"""Offline fixtures only; no OpenFOAM or DEM execution."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_smoke_case as prep
import check_smoke_case as smoke

SPEC = importlib.util.spec_from_file_location("serial_fixtures", ROOT / "tests/test_compare_plate2d_ab.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        (ROOT / "validation").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="smoke-test-")
        self.build_tmp = tempfile.TemporaryDirectory(dir=ROOT / "validation", prefix="smoke-build-test-")
        self.build = Path(self.build_tmp.name)
        self.out = Path(self.tmp.name) / "new"
        self.commit = prep.git("rev-parse", "HEAD").decode().strip()
        self.summary = ("project_commit=" + self.commit + "\nstatus=BUILD_ARTIFACT_CHECKS_PASSED;\n"
                        "WM_OPTIONS=mockOptions\nopenfoam_version=v2512\n")
        (self.build / "summary.txt").write_text(self.summary)

    def tearDown(self):
        self.tmp.cleanup()
        self.build_tmp.cleanup()

    def test_native_three_dimensional_copy_and_control(self):
        out = prep.prepare(self.out, self.build, "laserbeamFoam", 250, 90)
        self.assertFalse((out / "0").exists())
        self.assertFalse((out / "constant/polyMesh").exists())
        self.assertFalse((out / "DEM_small").exists())
        text = (out / "system/blockMeshDict").read_text()
        self.assertIn("(16 8 16)", text)
        self.assertNotIn("type empty", text)
        self.assertIn("application     laserbeamFoam;", (out / "system/controlDict").read_text())
        self.assertEqual((out / "constant/LaserProperties").read_bytes(), prep.git(
            "show", "3c93f2657e089e22e9a8298648292969e85a4bad:tutorials/laserbeamFoam/fiveLasersOnSubstrate/constant/LaserProperties"))
        self.assertEqual(json.loads((out / "manifest.json").read_text())["config"]["solver_timeout_seconds"], 90)
        self.assertIn("PROPOSED", (out / "manifest.json").read_text())
        self.assertTrue((out / "metadata.sha256").is_file())

    def test_existing_directory_rejected(self):
        self.out.mkdir()
        (self.out / "evidence").write_text("retain")
        with self.assertRaisesRegex(ValueError, "exists"):
            prep.prepare(self.out, self.build, "laserbeamFoam")
        self.assertEqual((self.out / "evidence").read_text(), "retain")

    def test_outside_runs_rejected(self):
        with self.assertRaisesRegex(ValueError, "below"):
            prep.prepare(self.build / "case", self.build, "laserbeamFoam")

    def test_stale_build_rejected(self):
        (self.build / "summary.txt").write_text(self.summary.replace(self.commit, "0" * 40))
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            prep.prepare(self.out, self.build, "laserbeamFoam")

    def test_failed_build_rejected(self):
        (self.build / "summary.txt").write_text(self.summary.replace("BUILD_ARTIFACT_CHECKS_PASSED", "FAILED"))
        with self.assertRaisesRegex(ValueError, "artifact checks"):
            prep.prepare(self.out, self.build, "laserbeamFoam")

    def test_invalid_timeout_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            prep.prepare(self.out, self.build, "laserbeamFoam", solver_timeout=-1)

    def test_ai_executable_choice(self):
        prep.prepare(self.out, self.build, "aiLaserbeamFoam")
        self.assertIn("aiLaserbeamFoam", (self.out / "system/controlDict").read_text())

    def test_proposal_requires_explicit_opt_in(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_smoke_case.py"),
                                 "--run-dir", str(self.out), "--build-dir", str(self.build)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("PROPOSED", result.stderr)
        self.assertFalse(self.out.exists())


class SmokeChecks(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ComparatorTests()
        self.fixture.setUp()
        self.case = self.fixture.root / "A"
        (self.case / "manifest.json").write_text(json.dumps({"solver": "laserbeamFoam",
            "config": {"cells": [1, 1, 2], "steps": 10, "end_time": "1e-7"}}))
        (self.case / "1e-7/T").write_text(fixtures.field(value="uniform 300"))
        (self.case / "1e-7/Deposition").write_text(fixtures.field(value="uniform 2"))

    def tearDown(self):
        self.fixture.tearDown()

    def test_valid_smoke_is_not_reference_validation(self):
        report = smoke.check(self.case)
        self.assertEqual(report["status"], "SMOKE_CHECKS_PASSED")
        self.assertEqual(report["accuracy"], "UNVERIFIED")
        self.assertEqual(report["reference"], "NOT_ESTABLISHED")

    def test_missing_field_fails(self):
        (self.case / "1e-7/T").unlink()
        self.assertEqual(smoke.check(self.case)["status"], "FAIL")

    def test_nonfinite_fails(self):
        (self.case / "1e-7/T").write_text(fixtures.field(value="uniform nan"))
        self.assertEqual(smoke.check(self.case)["status"], "FAIL")

    def test_bounds_fail(self):
        (self.case / "1e-7/alpha.metal").write_text(fixtures.field(value="uniform 1.1"))
        self.assertEqual(smoke.check(self.case)["status"], "FAIL")

    def test_unknown_output_needs_review(self):
        (self.case / "1e-7/unknown").write_bytes(b"\x00\xff")
        self.assertEqual(smoke.check(self.case)["status"], "REVIEW_REQUIRED")

    def test_nonzero_exit_fails(self):
        (self.case / "solver.exit.txt").write_text("1")
        self.assertEqual(smoke.check(self.case)["status"], "FAIL")

    def test_no_deposition_needs_review(self):
        (self.case / "1e-7/Deposition").write_text(fixtures.field(value="uniform 0"))
        self.assertEqual(smoke.check(self.case)["status"], "REVIEW_REQUIRED")

    def test_input_inventory_detects_extra_missing_changed(self):
        (self.case / "0").mkdir()
        def record():
            paths = [p for d in ("initial", "constant", "system", "0")
                     for p in (self.case / d).rglob("*") if p.is_file()]
            (self.case / "initialized.sha256").write_text("".join(
                hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(self.case).as_posix() + "\n"
                for p in paths))
        record()
        smoke.check_inputs(self.case)
        extra = self.case / "system/unexpected"
        extra.write_text("extra")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            smoke.check_inputs(self.case)
        extra.unlink()
        target = self.case / "initial/T"
        target.write_text("changed")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            smoke.check_inputs(self.case)
        target.unlink()
        with self.assertRaisesRegex(ValueError, "mismatch"):
            smoke.check_inputs(self.case)

    def test_uniform_symlink_fails(self):
        directory = self.case / "1e-7/uniform"
        directory.mkdir()
        try:
            (directory / "escape").symlink_to(self.case / "solver.exit.txt")
        except OSError:
            self.skipTest("symlink creation not available")
        self.assertEqual(smoke.check(self.case)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
