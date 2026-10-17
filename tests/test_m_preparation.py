"""Authorized M preparation and conditional gates; no OpenFOAM execution."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_m_case as prep


class MPreparationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        (ROOT / "validation").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="m-preparation-test-")
        self.build_tmp = tempfile.TemporaryDirectory(dir=ROOT / "validation", prefix="m-build-test-")
        self.build = Path(self.build_tmp.name)
        self.out = Path(self.tmp.name) / "new"
        self.commit = prep.base.git("rev-parse", "HEAD").decode().strip()
        self.summary = ("project_commit=" + self.commit + "\nstatus=BUILD_ARTIFACT_CHECKS_PASSED;\n"
                        "WM_OPTIONS=mockOptions\nopenfoam_version=v2512\n")
        (self.build / "summary.txt").write_text(self.summary)
        self.disk_patch = patch.object(prep.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(20 * 2**30, 0, 20 * 2**30))
        self.disk_patch.start()

    def tearDown(self):
        self.disk_patch.stop()
        self.tmp.cleanup()
        self.build_tmp.cleanup()

    def make_m1(self, **resources):
        m1 = Path(self.tmp.name) / "completed-M1"
        m1.mkdir(exist_ok=True)
        manifest = {"experiment_id": "M1", "project_commit": self.commit, "config": prep.config_for("M1")}
        (m1 / "manifest.json").write_text(json.dumps(manifest))
        data = {"solver_wall_seconds": 10., "max_rss_kib": 100000, "data_bytes": 1000000}
        data.update(resources)
        report = {"experiment_id": "M1", "status": "EXPLORATION_CHECKS_PASSED", "resources": data}
        (m1 / "m.json").write_text(json.dumps(report))
        return m1

    def test_three_authorized_profiles_and_ten_outputs(self):
        for name, cells, steps, _, interval, timeout in (
                (key, *value) for key, value in prep.PROFILES.items()):
            config = prep.config_for(name)
            self.assertEqual(config["cells"], cells)
            self.assertEqual(config["steps"], steps)
            self.assertEqual(config["steps"] // config["write_interval"], 10)
            self.assertEqual(config["solver_timeout_seconds"], timeout)
            self.assertEqual(config["write_interval"], interval)
            self.assertEqual(config["resource_policy"], "MONITORED_ONLY")
            self.assertEqual(config["formal_benchmark"], "PROPOSED")

    def test_m1_native_copy_controls_and_preserved_physics(self):
        out = prep.prepare(self.out, self.build, "M1")
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["project_commit"], self.commit)
        self.assertEqual(manifest["experiment_id"], "M1")
        self.assertFalse((out / "0").exists())
        self.assertFalse((out / "constant/polyMesh").exists())
        self.assertIn("(40 20 40)", (out / "system/blockMeshDict").read_text(encoding="utf-8"))
        control = (out / "system/controlDict").read_text(encoding="utf-8")
        for key, value in (("endTime", "1e-5"), ("deltaT", "1e-8"), ("writeInterval", "100"),
                           ("purgeWrite", "0"), ("adjustTimeStep", "no"), ("application", "laserbeamFoam")):
            self.assertRegex(control, r"\b" + key + r"\s+" + value + ";")
        self.assertEqual((out / "constant/LaserProperties").read_bytes(), prep.base.git(
            "show", prep.config_for("M1")["source_commit"] + ":" + prep.config_for("M1")["source"] + "/constant/LaserProperties"))
        for line in (out / "inputs.sha256").read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            self.assertEqual(digest, hashlib.sha256((out / relative).read_bytes()).hexdigest())
        self.assertIn("run_m_case.sh", (out / "Allrun").read_text(encoding="utf-8"))
        self.assertIn("no automatic cleanup", (out / "Allclean").read_text(encoding="utf-8"))

    def test_m2_and_m3_independent_case_and_output_controls(self):
        m1 = self.make_m1()
        with patch.object(prep, "refresh_m1"):
            for name, expected_mesh, interval in (("M2", "(40 20 40)", "300"), ("M3", "(80 40 80)", "100")):
                out = prep.prepare(self.out.parent / name, self.build, name, m1, "Observe later thermal evolution")
                self.assertIn(expected_mesh, (out / "system/blockMeshDict").read_text(encoding="utf-8"))
                self.assertRegex((out / "system/controlDict").read_text(encoding="utf-8"), r"writeInterval\s+" + interval + ";")
                self.assertFalse((out / "0").exists())
                self.assertEqual(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["conditional"]["forecast_status"],
                                 "SCALING_SCENARIO_NOT_GUARANTEE")

    def test_existing_directory_never_overwritten(self):
        self.out.mkdir()
        (self.out / "evidence").write_text("retain")
        with self.assertRaisesRegex(ValueError, "exists"):
            prep.prepare(self.out, self.build, "M1")
        self.assertEqual((self.out / "evidence").read_text(encoding="utf-8"), "retain")

    def test_stale_or_failed_or_wrong_openfoam_build_rejected(self):
        for old, new, message in ((self.commit, "0" * 40, "HEAD differs"),
                                  ("BUILD_ARTIFACT_CHECKS_PASSED", "FAILED", "artifact checks"),
                                  ("v2512", "v2412", "v2512")):
            (self.build / "summary.txt").write_text(self.summary.replace(old, new))
            with self.assertRaisesRegex(ValueError, message):
                prep.prepare(self.out, self.build, "M1")
            self.assertFalse(self.out.exists())

    def test_run_outside_checkout_runs_rejected(self):
        with self.assertRaisesRegex(ValueError, "below"):
            prep.prepare(self.build / "case", self.build, "M1")

    def test_config_override_refused(self):
        original = prep.json.loads
        def altered(text):
            data = original(text)
            data["delta_t"] = "1e-7"
            return data
        with patch.object(prep.json, "loads", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "explicitly authorized"):
                prep.config_for("M1")

    def test_conditional_requires_m1_and_scientific_reason(self):
        for name in ("M2", "M3"):
            with self.assertRaisesRegex(ValueError, "require"):
                prep.prepare(self.out, self.build, name)
            with self.assertRaisesRegex(ValueError, "require"):
                prep.conditional_evidence(prep.config_for(name), self.make_m1(), "longer")
        self.assertFalse(self.out.exists())

    def test_m1_failure_blocks_even_an_old_report(self):
        m1 = self.make_m1()
        with patch.object(prep, "refresh_m1", side_effect=ValueError("M1 current offline numerical check failed")):
            with self.assertRaisesRegex(ValueError, "current offline"):
                prep.conditional_evidence(prep.config_for("M2"), m1, "Observe later thermal evolution")

    def test_failed_status_and_missing_timing_block_conditional(self):
        m1 = self.make_m1(solver_wall_seconds=None)
        with self.assertRaisesRegex(ValueError, "measurement"):
            prep.conditional_evidence(prep.config_for("M2"), m1, "Observe later thermal evolution", refresh=False)
        report = json.loads((m1 / "m.json").read_text(encoding="utf-8"))
        report["status"] = "FAIL"
        (m1 / "m.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "not passed"):
            prep.conditional_evidence(prep.config_for("M2"), m1, "Observe later thermal evolution", refresh=False)

    def test_measured_and_forecast_budget_excess_blocks_conditional(self):
        for resources, expected in (({"max_rss_kib": 8388609}, "measured"),
                                    ({"solver_wall_seconds": 1000}, "scaling scenario"),
                                    ({"max_rss_kib": 2000000}, "scaling scenario"),
                                    ({"data_bytes": 500000000}, "scaling scenario")):
            m1 = self.make_m1(**resources)
            with self.assertRaisesRegex(ValueError, expected):
                prep.conditional_evidence(prep.config_for("M3"), m1, "Compare grid resolution sensitivity", refresh=False)

    def test_low_free_disk_blocks_before_creation(self):
        with patch.object(prep.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(100, 99, 1)):
            with self.assertRaisesRegex(ValueError, "filesystem space"):
                prep.prepare(self.out, self.build, "M1")
        self.assertFalse(self.out.exists())

    def test_zero_unresolved_measurement_does_not_predict_free_work(self):
        m1 = self.make_m1(solver_wall_seconds=0)
        with self.assertRaisesRegex(ValueError, "positive resolution"):
            prep.conditional_evidence(prep.config_for("M2"), m1, "Observe later thermal evolution", refresh=False)

    def test_nonascii_run_path_generates_utf8_native_scripts(self):
        out = prep.prepare(self.out.parent / "\u4e09\u7ef4\u63a2\u7d22", self.build, "M1")
        self.assertIn(str(out), (out / "Allrun").read_bytes().decode("utf-8"))
        self.assertNotIn(b"\r", (out / "Allrun").read_bytes())
        self.assertNotIn(b"\r", (out / "Allclean").read_bytes())
        for name in ("Allclean", "manifest.json", "preflight.json", "preparation.time.txt"):
            (out / name).read_bytes().decode("utf-8")

    def test_preflight_directory_output_rejected(self):
        target = Path(self.tmp.name) / "preflight.json"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "unsafe output"):
            prep.write_preflight(Path(self.tmp.name), {"status": "test"})

    def test_preflight_symlink_output_rejected_without_touching_target(self):
        destination = Path(self.tmp.name) / "preserve.txt"
        destination.write_text("preserve", encoding="utf-8")
        try:
            (Path(self.tmp.name) / "preflight.json").symlink_to(destination)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "unsafe output"):
            prep.write_preflight(Path(self.tmp.name), {"status": "test"})
        self.assertEqual(destination.read_text(encoding="utf-8"), "preserve")

    def test_preflight_hardlink_output_rejected_without_touching_target(self):
        destination = Path(self.tmp.name) / "preserve.txt"
        destination.write_text("preserve", encoding="utf-8")
        try:
            os.link(destination, Path(self.tmp.name) / "preflight.json")
        except OSError:
            self.skipTest("hardlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "unsafe output"):
            prep.write_preflight(Path(self.tmp.name), {"status": "test"})
        self.assertEqual(destination.read_text(encoding="utf-8"), "preserve")

    def test_preflight_checks_fresh_exact_build_and_manifest(self):
        prep.prepare(self.out, self.build, "M1")
        self.assertEqual(prep.preflight(self.out)["status"], "PREFLIGHT_PASSED")
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        manifest["config"]["steps"] = 100
        (self.out / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "authorized"):
            prep.preflight(self.out)

    def test_cli_has_no_arbitrary_timeout_physics_or_restart_override(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_m_case.py"), "--solver-timeout", "1"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
