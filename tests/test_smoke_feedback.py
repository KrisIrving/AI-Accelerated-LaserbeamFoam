"""Synthetic offline feedback fixtures; no OpenFOAM execution or uploads."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_smoke_case as smoke
import export_smoke_feedback as feedback
import test_smoke_tools as smoke_fixtures


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.fixture = smoke_fixtures.SmokeChecks()
        self.fixture.setUp()
        self.case = self.fixture.case

    def tearDown(self):
        self.fixture.tearDown()

    def run_check(self):
        with patch.object(sys, "argv", ["check_smoke_case.py", "--case-dir", str(self.case), "--feedback-bundle"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return smoke.main()

    def contents(self, result=None):
        if result is None:
            path = next((self.case / "feedback").glob("*.tar.gz"))
        else:
            path = Path(result["archive_path"])
        with tarfile.open(path) as archive:
            self.assertTrue(all(x.isfile() and "/" not in x.name for x in archive))
            return {name: archive.extractfile(name).read() for name in archive.getnames()}

    def test_pass_auto_bundle(self):
        self.assertEqual(self.run_check(), 0)
        content = self.contents()
        self.assertEqual(json.loads(content["bundle.json"])["check_status"], "SMOKE_CHECKS_PASSED")
        self.assertEqual(json.loads(content["smoke.json"])["reference"], "NOT_ESTABLISHED")

    def test_fail_auto_bundle(self):
        (self.case / "1e-7/T").unlink()
        self.assertEqual(self.run_check(), 1)
        self.assertEqual(json.loads(self.contents()["bundle.json"])["check_exit_code"], 1)

    def test_review_auto_bundle(self):
        (self.case / "1e-7/unknown").write_bytes(b"\x00\xff")
        self.assertEqual(self.run_check(), 2)
        self.assertEqual(json.loads(self.contents()["bundle.json"])["check_status"], "REVIEW_REQUIRED")

    def test_nonzero_solver_exit(self):
        (self.case / "solver.exit.txt").write_text("137\n")
        self.assertEqual(self.run_check(), 1)
        self.assertEqual(self.contents()["solver.exit.txt"].decode().splitlines(), ["137"])

    def test_mesh_only_export_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "log.checkMesh").write_text("Mesh OK\n")
            result = feedback.export_feedback(case)
            self.assertEqual(result["check_status"], "UNVERIFIED")
            self.assertIsNone(result["check_exit_code"])
            self.assertEqual(result["collection_status"], "PARTIAL")
            self.assertIn("smoke.json", result["missing_required"])
            self.assertEqual(self.contents(result)["log.checkMesh"].decode().splitlines(), ["Mesh OK"])

    def test_missing_manifest_check_reports_review_and_exports(self):
        (self.case / "manifest.json").unlink()
        self.assertEqual(self.run_check(), 2)
        self.assertEqual(json.loads(self.contents()["smoke.json"])["status"], "REVIEW_REQUIRED")

    def test_missing_or_incomplete_wrapper_timing(self):
        result = feedback.export_feedback(self.case)
        self.assertEqual(result["timing_status"], "INCOMPLETE_TIMING")
        for name in ("mesh", "solve"):
            (self.case / ("time.workflow." + name + ".txt")).write_text("Command being timed: ...\n")
        self.assertEqual(feedback.export_feedback(self.case)["timing_status"], "INCOMPLETE_TIMING")

    def test_complete_timing(self):
        for name in ("mesh", "solve"):
            (self.case / ("time.workflow." + name + ".txt")).write_text(
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.00\nMaximum resident set size (kbytes): 3\n")
        (self.case / "preparation.time.txt").write_text("preparation_wall_seconds=0.1\n")
        self.assertEqual(feedback.export_feedback(self.case)["timing_status"], "RECORDED_SCOPE")

    def test_complete_collection(self):
        build_parent = ROOT / "validation"
        build_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build_parent) as tmp:
            (Path(tmp) / "summary.txt").write_text("project_commit=" + "a" * 40 + "\nopenfoam_version=v2512\n")
            manifest = json.loads((self.case / "manifest.json").read_text())
            manifest.update(project_commit="a" * 40, build_commit="a" * 40, build_dir=tmp)
            (self.case / "manifest.json").write_text(json.dumps(manifest))
            self.assertEqual(self.run_check(), 0)
            for stage in ("blockMesh", "checkMesh", "setFields", "laserbeamFoam"):
                for prefix in ("exit.", "time."):
                    path = self.case / (prefix + stage + ".txt")
                    if not path.exists():
                        path.write_text("0\n")
                if not (self.case / ("log." + stage)).exists():
                    (self.case / ("log." + stage)).write_text("stage completed\n")
            (self.case / "solver.time.txt").write_text("GNU time\n")
            for name in ("mesh", "solve"):
                (self.case / ("time.workflow." + name + ".txt")).write_text(
                    "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.00\nMaximum resident set size (kbytes): 3\n")
            (self.case / "preparation.time.txt").write_text("preparation_wall_seconds=0.1\n")
            result = feedback.export_feedback(self.case)
            self.assertEqual(result["collection_status"], "COMPLETE")
            self.assertEqual(result["solver_exit_code"], 0)

    def test_repeated_export_never_overwrites(self):
        first = feedback.export_feedback(self.case)
        original = Path(first["archive_path"]).read_bytes()
        second = feedback.export_feedback(self.case)
        self.assertNotEqual(first["archive_path"], second["archive_path"])
        self.assertEqual(Path(first["archive_path"]).read_bytes(), original)

    def test_sha256_and_inventory(self):
        result = feedback.export_feedback(self.case)
        content = self.contents(result)
        for line in content["SHA256SUMS"].decode().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256(content[name]).hexdigest(), digest)
        self.assertEqual(set(content["FILES.txt"].decode().splitlines()), set(content))
        path = Path(result["archive_path"])
        digest = path.with_suffix("").with_suffix(".sha256").read_text().split()[0]
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_raw_fields_vtk_mesh_and_binary_excluded(self):
        (self.case / "dump.vtk").write_text("private vtk")
        (self.case / "processor0").mkdir()
        (self.case / "processor0/secret").write_text("private field")
        (self.case / "log.blockMesh").write_bytes(b"\x00\xff")
        result = feedback.export_feedback(self.case)
        content = self.contents(result)
        self.assertIn("log.blockMesh", result["omitted"])
        self.assertNotIn("manifest.json", content)
        self.assertFalse(any("vtk" in name or "processor" in name or "polyMesh" in name for name in content))
        self.assertNotIn(b"internalField", b"".join(content.values()))

    def test_size_limits_omit_with_warning(self):
        (self.case / "log.blockMesh").write_text("x" * 101)
        with patch.object(feedback, "MAX_FILE_BYTES", 100):
            result = feedback.export_feedback(self.case)
        self.assertIn("size limit", result["omitted"]["log.blockMesh"])

    def test_archive_limit_fails_without_publishing(self):
        with patch.object(feedback, "MAX_ARCHIVE_BYTES", 1), self.assertRaisesRegex(ValueError, "archive exceeds"):
            feedback.export_feedback(self.case)
        self.assertFalse((self.case / "feedback").exists())

    def test_total_limit_fails_without_publishing(self):
        with patch.object(feedback, "MAX_TOTAL_BYTES", 10), self.assertRaisesRegex(ValueError, "total size limit"):
            feedback.export_feedback(self.case)
        self.assertFalse((self.case / "feedback").exists())

    def test_private_paths_and_identities_redacted_original_retained(self):
        original = 'User: alice\nHost: secretstation\nCase: /media/alice/disk/case\nC:\\Users\\alice\\private\nalice@secretstation 192.168.1.5\n'
        (self.case / "log.blockMesh").write_text(original)
        result = feedback.export_feedback(self.case)
        archived = self.contents(result)["log.blockMesh"].decode()
        for private in ("alice", "secretstation", "/media/", "C:\\Users", "192.168.1.5"):
            self.assertNotIn(private, archived)
        self.assertEqual((self.case / "log.blockMesh").read_text(), original)

    def test_provenance_does_not_substitute_current_head(self):
        result = feedback.export_feedback(self.case)
        provenance = json.loads(self.contents(result)["provenance.json"])
        self.assertEqual(provenance["source_commit"], "UNVERIFIED")
        self.assertEqual(provenance["build_commit"], "UNVERIFIED")
        self.assertEqual(provenance["provenance_status"], "PROVENANCE_PENDING")

    def test_config_hash_is_independent_of_key_order(self):
        first = json.loads(self.contents(feedback.export_feedback(self.case))["provenance.json"])
        manifest = json.loads((self.case / "manifest.json").read_text())
        manifest["config"] = dict(reversed(list(manifest["config"].items())))
        (self.case / "manifest.json").write_text(json.dumps(manifest))
        second = json.loads(self.contents(feedback.export_feedback(self.case))["provenance.json"])
        self.assertEqual(first["config_canonical_sha256"], second["config_canonical_sha256"])

    def test_original_build_records_are_cross_checked(self):
        (ROOT / "validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "validation") as tmp:
            build = Path(tmp)
            (build / "summary.txt").write_text("project_commit=" + "a" * 40 + "\nopenfoam_version=v2512\n")
            manifest = json.loads((self.case / "manifest.json").read_text())
            manifest.update(project_commit="a" * 40, build_commit="b" * 40, build_dir=str(build))
            (self.case / "manifest.json").write_text(json.dumps(manifest))
            result = feedback.export_feedback(self.case)
            provenance = json.loads(self.contents(result)["provenance.json"])
            self.assertEqual(provenance["build_commit"], "a" * 40)
            self.assertEqual(provenance["provenance_status"], "PROVENANCE_PENDING")
            manifest["build_commit"] = "a" * 40
            (self.case / "manifest.json").write_text(json.dumps(manifest))
            provenance = json.loads(self.contents(feedback.export_feedback(self.case))["provenance.json"])
            self.assertEqual(provenance["provenance_status"], "RECORDS_MATCH")

    def test_no_command_execution(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("must not run CFD")), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("must not run CFD")):
            feedback.export_feedback(self.case)

    def test_pack_failure_preserves_pass_fail_and_review(self):
        for code, status in ((0, "SMOKE_CHECKS_PASSED"), (1, "FAIL"), (2, "REVIEW_REQUIRED")):
            report = {"status": status, "fields": {}, "issues": [], "resources": {}}
            with patch.object(smoke, "check", return_value=report), \
                    patch.object(feedback, "export_feedback", side_effect=ValueError("export failed")):
                self.assertEqual(self.run_check(), code)

    def test_diagnostics_cli_does_not_recheck(self):
        (self.case / "smoke.json").write_text('{"status": "FAIL"}')
        with patch.object(smoke, "check", side_effect=AssertionError("must not recheck")), \
                patch.object(sys, "argv", ["export_smoke_feedback.py", "--case-dir", str(self.case), "--diagnostics-only"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(feedback.main(), 0)
        self.assertEqual(json.loads(self.contents()["bundle.json"])["check_status"], "FAIL")

    def test_invalid_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "traversal"):
            feedback.export_feedback(self.case / ".." / "A")

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError:
            self.skipTest("symlink creation not available")

    def test_symlink_file_is_omitted(self):
        self.symlink(self.case / "log.blockMesh", self.case / "1e-7/T")
        result = feedback.export_feedback(self.case)
        self.assertIn("symlink", result["omitted"]["log.blockMesh"])
        self.assertNotIn("log.blockMesh", self.contents(result))

    def test_symlink_feedback_directory_rejected(self):
        self.symlink(self.case / "feedback", self.fixture.fixture.root, True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            feedback.export_feedback(self.case)

    def test_symlink_case_rejected(self):
        link = self.case.parent / "linked-case"
        self.symlink(link, self.case, True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            feedback.export_feedback(link)

    def test_symlink_report_not_overwritten(self):
        outside = self.case.parent / "private-report"
        outside.write_text("retain original")
        self.symlink(self.case / "smoke.json", outside)
        self.assertEqual(self.run_check(), 2)
        self.assertEqual(outside.read_text(), "retain original")


if __name__ == "__main__":
    unittest.main()
