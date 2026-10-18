"""Bounded M feedback export fixtures; no OpenFOAM, subprocesses or uploads."""
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
import export_smoke_feedback as feedback


class MFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case = self.root / "runs" / "m-001"
        self.build = self.root / "validation" / "build-original"
        self.case.mkdir(parents=True)
        self.build.mkdir(parents=True)
        self.repo_patch = patch.object(feedback, "REPO", self.root)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.addCleanup(self.tmp.cleanup)
        self.manifest = {"solver": "laserbeamFoam", "project_commit": "a" * 40,
                         "build_commit": "a" * 40, "build_dir": str(self.build), "mpi_ranks": 1,
                         "config": {"schema": "m-exploration-v1", "status": "PROPOSED", "id": "M-explore-001",
                                    "formal_benchmark": False, "solver": "laserbeamFoam", "write_interval": 20,
                                    "resource_policy": "OBSERVATION_ONLY", "max_rss_kib": 8388608,
                                    "max_data_bytes": 2147483648,
                                    "source_commit": "b" * 40, "cells": [40, 20, 40], "steps": 100,
                                    "delta_t": "1e-8", "end_time": "1e-6"}}
        (self.case / "manifest.json").write_text(json.dumps(self.manifest))
        (self.build / "summary.txt").write_text(
            "project_commit=" + "a" * 40 + "\nopenfoam_version=v2512\nWM_OPTIONS=linux64GccDPInt32Opt\n")
        self.report = {"status": "EXPLORATION_CHECKS_PASSED", "cells": 32000, "steps": 100,
                       "final_time": "1e-6", "diagnostic_events": 1730,
                       "resources": {"solver": {"wall_seconds": 1.25}},
                       "physical_observations": {"melting": "NOT_OBSERVED"}}
        self.write_report()
        (self.case / "m.txt").write_text("EXPLORATION_CHECKS_PASSED\n")
        (self.case / "observations.csv").write_text("time,Tmax\n1e-6,330\n")
        (self.case / "execution_times.csv").write_text("step,seconds\n100,1.25\n")
        (self.case / "mesh-summary.json").write_text('{"cells":32000,"status":"Mesh OK"}\n')
        for stage in ("blockMesh", "checkMesh", "setFields", "laserbeamFoam"):
            (self.case / ("log." + stage)).write_text("stage completed\n")
            (self.case / ("exit." + stage + ".txt")).write_text("0\n")
            (self.case / ("time." + stage + ".txt")).write_text(self.timing())
        (self.case / "solver.exit.txt").write_text("0\n")
        (self.case / "solver.time.txt").write_text(self.timing())
        (self.case / "preparation.time.txt").write_text("preparation_wall_seconds=0.01\n")
        for stage in ("mesh", "solve"):
            (self.case / ("time.workflow." + stage + ".txt")).write_text(self.timing())

    @staticmethod
    def timing():
        return ("Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\n"
                "Maximum resident set size (kbytes): 200\n")

    def write_report(self):
        (self.case / "m.json").write_text(json.dumps(self.report))

    def contents(self, result):
        with tarfile.open(result["archive_path"]) as archive:
            self.assertTrue(all(entry.isfile() and "/" not in entry.name for entry in archive))
            return {entry.name: archive.extractfile(entry).read() for entry in archive}

    def export(self, **kwargs):
        return feedback.export_feedback(self.case, profile="m", **kwargs)

    def test_complete_m_export_uses_fixed_reports_and_prefix(self):
        result = self.export(check_exit_code=0)
        content = self.contents(result)
        self.assertEqual(result["collection_status"], "COMPLETE")
        self.assertEqual(result["timing_status"], "RECORDED_SCOPE")
        self.assertEqual(result["check_exit_code"], 0)
        self.assertEqual(result["solver_exit_code"], 0)
        self.assertEqual(result["missing_required"], [])
        self.assertTrue(Path(result["archive_path"]).name.startswith("threeD-exploration-feedback."))
        self.assertTrue(set(feedback.M_REPORTS).issubset(content))
        self.assertNotIn("smoke.json", content)
        self.assertNotIn("log.aiLaserbeamFoam", result["missing_required"])

    def test_s_default_whitelist_and_prefix_remain_distinct(self):
        result = feedback.export_feedback(self.case)
        content = self.contents(result)
        self.assertTrue(Path(result["archive_path"]).name.startswith("threeD-smoke-feedback."))
        self.assertNotIn("m.json", content)
        self.assertNotIn("observations.csv", content)
        self.assertIn("smoke.json", result["missing_required"])
        self.assertNotIn("profile", json.loads(content["bundle.json"]))

    def test_saved_status_exit_inference_pass_fail_review_and_unknown(self):
        for status, code in (("EXPLORATION_CHECKS_PASSED", 0), ("FAIL", 1),
                             ("REVIEW_REQUIRED", 2), ("SMOKE_CHECKS_PASSED", None)):
            self.report["status"] = status
            self.write_report()
            result = self.export()
            self.assertEqual(result["check_status"], status)
            self.assertEqual(result["check_exit_code"], code)
            self.assertEqual(result["exit_code_source"], "INFERRED_FROM_SAVED_REPORT")

    def test_current_exit_code_must_agree_with_saved_m_status(self):
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.export(check_exit_code=1)
        self.assertFalse((self.case / "feedback").exists())

    def test_mesh_only_diagnostics_remain_available_without_saved_report(self):
        (self.case / "m.json").unlink()
        (self.case / "m.txt").unlink()
        (self.case / "solver.exit.txt").unlink()
        result = self.export()
        self.assertEqual(result["archive_status"], "EXPORTED")
        self.assertEqual(result["collection_status"], "PARTIAL")
        self.assertEqual(result["check_status"], "UNVERIFIED")
        self.assertIsNone(result["check_exit_code"])
        self.assertIn("m.json", result["missing_required"])
        self.assertIn("log.checkMesh", self.contents(result))

    def test_original_run_build_and_canonical_config_provenance(self):
        first = json.loads(self.contents(self.export())["provenance.json"])
        self.assertEqual(first["source_commit"], "a" * 40)
        self.assertEqual(first["build_commit"], "a" * 40)
        self.assertEqual(first["manifest_build_commit"], "a" * 40)
        self.assertEqual(first["provenance_status"], "RECORDS_MATCH")
        self.assertEqual(first["archive_tool_source_sha256"], hashlib.sha256(
            (ROOT / "scripts/export_smoke_feedback.py").read_bytes()).hexdigest())
        self.assertEqual(first["observed"]["steps"], 100)
        for key in ("id", "formal_benchmark", "solver", "write_interval", "resource_policy",
                    "max_rss_kib", "max_data_bytes"):
            self.assertEqual(first["config"][key], self.manifest["config"][key])
        expected = hashlib.sha256(json.dumps(self.manifest["config"], sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(first["config_canonical_sha256"], expected)
        (self.build / "summary.txt").write_text("project_commit=" + "c" * 40 + "\n")
        second = json.loads(self.contents(self.export())["provenance.json"])
        self.assertEqual(second["build_commit"], "c" * 40)
        self.assertEqual(second["provenance_status"], "PROVENANCE_PENDING")
        self.assertEqual(first["config_canonical_sha256"], second["config_canonical_sha256"])

    def test_hashes_inventory_and_external_export_timing(self):
        result = self.export()
        content = self.contents(result)
        self.assertEqual(set(content["FILES.txt"].decode().splitlines()), set(content))
        for line in content["SHA256SUMS"].decode().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256(content[name]).hexdigest(), digest)
        bundle = json.loads(content["bundle.json"])
        self.assertGreaterEqual(bundle["preparation_wall_seconds_before_archive"], 0)
        self.assertGreaterEqual(bundle["archive_payload_compression_wall_seconds"], 0)
        self.assertIn("excludes metadata entries", bundle["archive_payload_compression_timing_scope"])
        self.assertNotIn("feedback_export_wall_seconds", bundle)
        self.assertGreaterEqual(result["feedback_export_wall_seconds"], result["archive_creation_wall_seconds"])
        self.assertGreaterEqual(result["archive_creation_wall_seconds"], bundle["archive_payload_compression_wall_seconds"])
        self.assertGreaterEqual(result["archive_creation_wall_seconds"], 0)
        summary_path = Path(result["archive_path"].removesuffix(".tar.gz") + ".export.json")
        summary = json.loads(summary_path.read_text())
        self.assertEqual(summary["archive_sha256"], hashlib.sha256(Path(result["archive_path"]).read_bytes()).hexdigest())
        self.assertEqual(summary["feedback_export_wall_seconds"], result["feedback_export_wall_seconds"])
        self.assertEqual(summary["archive_payload_compression_wall_seconds"], bundle["archive_payload_compression_wall_seconds"])
        self.assertNotIn(str(self.case), summary_path.read_text())

    def test_no_fields_mesh_vtk_manifest_or_unknown_files(self):
        (self.case / "1e-6").mkdir()
        (self.case / "1e-6/T").write_text("secret field")
        (self.case / "output.vtk").write_text("secret vtk")
        (self.case / "private.log").write_text("secret extra")
        original = "User: alice\nHost: privatehost\nCase: /home/alice/private\n192.168.1.5\n"
        (self.case / "log.checkMesh").write_text(original)
        result = self.export()
        content = self.contents(result)
        for name in ("manifest.json", "output.vtk", "private.log", "1e-6/T"):
            self.assertNotIn(name, content)
        exported = content["log.checkMesh"].decode()
        for private in ("alice", "privatehost", "/home/", "192.168.1.5"):
            self.assertNotIn(private, exported)
        self.assertEqual((self.case / "log.checkMesh").read_text(), original)

    def test_m_larger_log_limit_does_not_change_s_limit(self):
        (self.case / "log.blockMesh").write_text("x" * (feedback.MAX_FILE_BYTES + 1))
        m_result = self.export()
        self.assertIn("log.blockMesh", self.contents(m_result))
        self.assertEqual(m_result["collection_status"], "COMPLETE")
        s_result = feedback.export_feedback(self.case)
        self.assertIn("size limit", s_result["omitted"]["log.blockMesh"])

    def test_m_oversized_file_is_omitted_not_silently_truncated(self):
        (self.case / "log.blockMesh").write_text("x" * 3001)
        with patch.object(feedback, "M_MAX_FILE_BYTES", 3000):
            result = self.export()
        self.assertIn("size limit", result["omitted"]["log.blockMesh"])
        self.assertIn("log.blockMesh", result["missing_required"])
        self.assertNotIn("log.blockMesh", self.contents(result))
        self.assertEqual(result["collection_status"], "PARTIAL")

    def test_m_payload_and_compressed_caps_fail_before_publication(self):
        for limit, message in (("M_MAX_TOTAL_BYTES", "total size limit"),
                               ("M_MAX_ARCHIVE_BYTES", "archive exceeds")):
            with patch.object(feedback, limit, 1), self.assertRaisesRegex(ValueError, message):
                self.export()
            self.assertFalse((self.case / "feedback").exists())

    def test_invalid_profile_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported feedback profile"):
            feedback.export_feedback(self.case, profile="powder")

    def test_cli_m_diagnostics_never_execute_subprocesses(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("no commands")), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("no commands")), \
                patch.object(sys, "argv", ["export_smoke_feedback.py", "--case-dir", str(self.case),
                                           "--diagnostics-only", "--profile", "m"]), \
                contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(feedback.main(), 0)
        self.assertIn("Feedback export wall time:", output.getvalue())
        self.assertEqual(len(list((self.case / "feedback").glob("threeD-exploration-feedback.*.tar.gz"))), 1)

    def test_repeated_exports_and_original_reports_are_preserved(self):
        report = (self.case / "m.json").read_bytes()
        first = self.export()
        first_bytes = Path(first["archive_path"]).read_bytes()
        second = self.export()
        self.assertNotEqual(first["archive_path"], second["archive_path"])
        self.assertEqual(Path(first["archive_path"]).read_bytes(), first_bytes)
        self.assertEqual((self.case / "m.json").read_bytes(), report)

    def test_missing_observations_is_partial_not_a_false_complete_bundle(self):
        (self.case / "observations.csv").unlink()
        result = self.export()
        self.assertEqual(result["check_status"], "EXPLORATION_CHECKS_PASSED")
        self.assertEqual(result["collection_status"], "PARTIAL")
        self.assertIn("observations.csv", result["missing_required"])

    def test_binary_m_report_is_omitted_and_status_unverified(self):
        (self.case / "m.json").write_bytes(b"\x00\xff")
        result = self.export()
        self.assertEqual(result["check_status"], "UNVERIFIED")
        self.assertEqual(result["collection_status"], "PARTIAL")
        self.assertIn("m.json", result["omitted"])
        self.assertNotIn("m.json", self.contents(result))

    def test_symlinked_m_report_cannot_escape_whitelist(self):
        target = self.root / "private.json"
        target.write_text('{"status":"EXPLORATION_CHECKS_PASSED","secret":"retain"}')
        (self.case / "m.json").unlink()
        try:
            (self.case / "m.json").symlink_to(target)
        except OSError:
            self.skipTest("symlink creation not available")
        result = self.export()
        self.assertIn("symlink", result["omitted"]["m.json"])
        self.assertNotIn("m.json", self.contents(result))
        self.assertIn("retain", target.read_text())


if __name__ == "__main__":
    unittest.main()
