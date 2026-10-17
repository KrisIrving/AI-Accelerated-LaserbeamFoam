"""Native ASCII tiny-mesh fixtures only; never OpenFOAM/physical validation."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m1_ic as ic
import compare_m1_ic as three
import export_smoke_feedback as exporter

SPEC = importlib.util.spec_from_file_location("ic_synthetic_meshes", ROOT / "tests/test_compare_m1_m3.py")
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)


class ControlledExperiment(unittest.TestCase):
    def setUp(self):
        self.helper = f.ComparisonFixture(methodName="test_native_mapping_ignores_reversed_fine_cell_order")
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.root, self.a, self.b = self.helper.root, self.helper.a, self.helper.b
        self.configs = {}
        for case, label in ((self.a, "M1"), (self.b, "M3")):
            m = json.loads((case / "manifest.json").read_text())
            m["config"].update(steps=1000, end_time="1e-5", solver_timeout_seconds=600,
                mesh_timeout_seconds=180, max_rss_kib=8388608, max_data_bytes=3221225472,
                resource_policy="MONITORED_ONLY")
            self.configs[label] = m["config"]
            (case / "manifest.json").write_text(json.dumps(m))
            for number in range(3, 11):
                shutil.copytree(case / "2e-6", case / (str(number) + "e-6"))
            for name in ("U", "p_rgh", "Laser_boundary"):
                content = f.fixtures.field(name, "uniform (0 0 0)" if name == "U" else "uniform 0")
                (case / "initial" / name).write_text(content)
                (case / "0" / name).write_text(content)
            (case / "system/controlDict").write_text(f.fixtures.fixtures.header("dictionary") +
                "application laserbeamFoam;\nendTime 1e-5;\nwriteInterval 100;\ndeltaT 1e-8;\n")
            dummy = f.fixtures.MChecks(methodName="test_all_times_native_fields_and_observations")
            dummy.config, dummy.case = m["config"], case
            dummy.write_log()
            f.fixtures.record_inputs(case)
        self.config = dict(self.configs["M1"], schema="m1-ic-exploration-v1", status="CONTROLLED_EXPLORATION_AUTHORIZED",
            id="M1-IC", steps=300, end_time="3e-6", initialization=ic.METHOD, decision="DEC-007")
        self.case = self.root / "runs/M1-IC"
        self.build = self.root / "validation/build"
        self.build.mkdir(parents=True)
        self.commit = "c" * 40
        self.summary = {"WM_OPTIONS": "synthetic", "project_commit": self.commit, "openfoam_version": "v2512"}
        for target, name, value in ((ic, "REPO", self.root), (ic.prep, "REPO", self.root),
                                    (exporter, "REPO", self.root)):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(ic, "config_for", return_value=self.config)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(ic.prep, "config_for", side_effect=lambda label: self.configs[label])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sources_before = {label: ic.hash_inventory(case, ("0", "constant", "system", "initial"))
                               for label, case in (("M1", self.a), ("M3", self.b))}

    def prepare(self):
        with patch.object(ic.prep, "build_record", return_value=(self.build, self.summary, self.commit)), \
             patch.object(ic.prep.base, "git", return_value=b""), redirect_stdout(io.StringIO()):
            ic.prepare(self.case, self.build, self.a, self.b)

    def initialize(self):
        self.prepare()
        (self.case / ".mesh-started").mkdir()
        centres = f.mesh(self.case, [2, 2, 2], reverse=True)
        shutil.copytree(self.case / "initial", self.case / "0")
        self.helper.write_field(self.case, "0", "alpha.metal", [int(y > 100.1e-6) for _, y, _ in centres])
        for stage in ("blockMesh", "checkMesh", "setFields"):
            (self.case / ("exit." + stage + ".txt")).write_text("0\n")
            (self.case / ("log." + stage)).write_text(("Mesh OK.\n" if stage == "checkMesh" else "") + "End\n")
        with redirect_stdout(io.StringIO()):
            ic.initialize(self.case)
        (self.case / "exit.restrictAlpha.txt").write_text("0\n")
        (self.case / "time.restrictAlpha.txt").write_text(
            "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\nMaximum resident set size (kbytes): 1200\n")
        f.fixtures.record_inputs(self.case)

    def validate(self):
        record = ic.manifest(self.case)
        geometry, volumes, centres, summary = ic.checks.mesh_metrics(self.case, self.config)
        parsed, alpha, _ = ic.checks.field_check(self.case / "0/alpha.metal", geometry, initial=True)
        return ic.validate_initial(self.case, record, geometry, volumes, centres, summary, alpha)

    def complete(self):
        self.initialize()
        (self.case / ".mesh-complete").touch()
        (self.case / ".solve-started").mkdir()
        for number in range(1, 4):
            out = self.case / (str(number) + "e-6")
            shutil.copytree(self.a / (str(number) + "e-6"), out)
            (out / "uniform").mkdir()
            (out / "uniform/cumulativeContErr").write_text(
                "FoamFile {format ascii; class uniformDimensionedScalarField; object cumulativeContErr;}\n"
                "dimensions [0 0 0 0 0 0 0]; value 0;\n")
            for name in ("phi", "p_rgh"):
                (out / name).write_text(f.fixtures.field(name, "uniform 0"))
        dummy = f.fixtures.MChecks(methodName="test_all_times_native_fields_and_observations")
        dummy.case, dummy.config = self.case, self.config
        dummy.write_log()
        (self.case / "solver.exit.txt").write_text("0\n")
        (self.case / "execution.txt").write_text("mpi_ranks=1\nthreads=1\n")
        timing = "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\nMaximum resident set size (kbytes): 1200\n"
        for stage in ("blockMesh", "checkMesh", "setFields", "restrictAlpha", "laserbeamFoam"):
            (self.case / ("time." + stage + ".txt")).write_text(timing)
            (self.case / ("exit." + stage + ".txt")).write_text("0\n")
        (self.case / "log.restrictAlpha").write_text("IC_INITIALIZATION_PASSED\n")
        for name in ("solver.time.txt", "time.workflow.mesh.txt", "time.workflow.solve.txt"):
            (self.case / name).write_text(timing)
        (self.build / "summary.txt").write_text("\n".join(k + "=" + v for k, v in self.summary.items()))
        return self.check()

    def check(self, mesh_only=False):
        return ic.checks.check(self.case, mesh_only, manifest_reader=ic.manifest, initial_validator=ic.validate_initial)

    def test_restriction_native_reversed_addressing_and_volume(self):
        self.initialize()
        report = self.validate()
        self.assertEqual(report["method"], ic.METHOD)
        self.assertEqual(report["box_centre_selection"], "NOT_APPLICABLE")
        values = [layer["alpha_volume_mean"] for layer in report["layers"]]
        self.assertAlmostEqual(values[0], 0.5)
        self.assertAlmostEqual(values[1], 1)
        self.assertAlmostEqual(report["metal_volume_m3"], 8.1e-11)
        self.assertFalse(report["surface"]["planar_binary_step"])
        for label, case in (("M1", self.a), ("M3", self.b)):
            self.assertEqual(self.sources_before[label], ic.hash_inventory(case, ("0", "constant", "system", "initial")))

    def test_only_alpha_changes_and_boundary_values_follow_owners(self):
        self.initialize()
        proof = json.loads((self.case / "ic-initialization.json").read_text())
        changed = [p for p in proof["before_sha256"] if proof["before_sha256"][p] != proof["after_sha256"][p]]
        self.assertEqual(changed, ["0/alpha.metal"])
        self.assertEqual(self.validate()["status"], "PASS")
        p = self.case / "0/alpha.metal"
        p.write_text(p.read_text().replace("type zeroGradient;", "type fixedValue;"))
        f.fixtures.record_inputs(self.case)
        with self.assertRaises(ic.N.ComparisonFailure):
            self.validate()

    def test_source_change_detected(self):
        self.initialize()
        (self.b / "0/alpha.metal").write_text("changed")
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "M3/0/alpha.metal"):
            self.validate()

    def test_reference_tamper_detected(self):
        self.initialize()
        with (self.case / ic.REFERENCE).open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "checksum"):
            self.validate()

    def test_other_initial_field_change_detected_even_with_new_input_hashes(self):
        self.initialize()
        p = self.case / "0/T"
        p.write_text(p.read_text().replace("uniform 300", "uniform 301"))
        f.fixtures.record_inputs(self.case)
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "snapshot changed"):
            self.validate()

    def test_alpha_nonfinite_or_unbounded_rejected(self):
        for alpha in ([float("nan")], [-1e-16], [1.00000001], []):
            with self.subTest(alpha=alpha), self.assertRaises(ic.N.ComparisonFailure):
                ic.bounded_alpha(alpha)

    def test_negative_volume_and_bad_mapping_rejected(self):
        a, b = ic.cross.load_case(self.a, "M1"), ic.cross.load_case(self.b, "M3")
        b["grid"]["volumes"][0] = -1
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.volume_restriction(a["grid"], b["grid"], b["initial"]["alpha.metal"])

    def test_original_checker_still_rejects_ic_identity(self):
        self.initialize()
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "manifest"):
            ic.checks.manifest(self.case)
        self.assertEqual(self.check(mesh_only=True)["status"], "MESH_INITIALIZATION_CHECKS_PASSED")

    def test_initialize_never_repeats_or_overwrites_source(self):
        self.initialize()
        before = ic.cross.digest(self.case / "0/alpha.metal")
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.initialize(self.case)
        self.assertEqual(before, ic.cross.digest(self.case / "0/alpha.metal"))

    def test_single_attempt_guard_is_checkout_wide_atomic(self):
        self.initialize()
        (self.case / ".mesh-complete").touch()
        with redirect_stdout(io.StringIO()):
            ic.attempt(self.case)
        with self.assertRaises(FileExistsError):
            ic.attempt(self.case)
        self.assertTrue((self.root / "runs/.m1-ic-solve-attempt/attempt.json").is_file())

    def test_existing_run_preparation_refused(self):
        self.prepare()
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "exists"):
            self.prepare()

    def test_complete_semantic_check_and_three_way_report(self):
        report = self.complete()
        self.assertEqual(report["status"], ic.checks.PASSED, report["issues"])
        self.assertEqual(report["steps"], 300)
        self.assertEqual(len(report["fields"]), 3)
        (self.case / "m.json").write_text(json.dumps(report))
        comparison = {"status": "COMPARISON_COMPLETED", "issues": []}
        three.compare(self.a, self.b, self.case, comparison)
        self.assertEqual(len(comparison["metrics"]), 9)
        self.assertEqual(len(comparison["times_s"]), 3)
        self.assertTrue(comparison["consumed_sources_unchanged_during_comparison"])
        self.assertLess(comparison["initial_alpha_IC_vs_restricted_M3"]["Linf"], 1e-12)
        self.assertIn("M1_to_IC", comparison["mapped_differences"]["0.000001"])

    def test_missing_output_cannot_pass(self):
        self.complete()
        (self.case / "2e-6/T").unlink()
        self.assertEqual(self.check()["status"], "FAIL")

    def test_bad_field_numerics_cannot_pass(self):
        self.complete()
        (self.case / "3e-6/T").write_text(f.fixtures.field("T", "uniform nan"))
        self.assertEqual(self.check()["status"], "FAIL")

    def test_changed_material_source_stops_preparation(self):
        (self.b / "constant/extra").write_text("different")
        f.fixtures.record_inputs(self.b)
        with self.assertRaisesRegex(ic.N.ComparisonFailure, "only"):
            self.prepare()

    def test_ic_feedback_whitelist_never_exports_full_reference(self):
        report = self.complete()
        (self.case / "m.json").write_text(json.dumps(report))
        for name in ("m.txt", "observations.csv", "execution_times.csv", "mesh-summary.json"):
            (self.case / name).write_text("synthetic\n")
        result = exporter.export_feedback(self.case, check_exit_code=0, profile="m1-ic")
        self.assertEqual(result["collection_status"], "COMPLETE", result)
        with tarfile.open(result["archive_path"], "r:gz") as bundle:
            self.assertIn("ic-initialization.json", bundle.getnames())
            self.assertNotIn(ic.REFERENCE, bundle.getnames())
            self.assertNotIn("manifest.json", bundle.getnames())

    def test_overlap_spatial_separation_and_power(self):
        self.assertEqual(three.overlap([1, 0], [0, 1], [2, 2])["overlap_over_smaller_positive_power"], 0)
        self.assertEqual(three.overlap([1, 0], [2, 0], [2, 2])["overlap_over_smaller_positive_power"], 1)
        self.assertIsNone(three.overlap([0], [1], [1])["overlap_over_smaller_positive_power"])

    def test_inlet_law_retained_and_unknown_bc_rejected(self):
        self.initialize()
        geometry, volumes, centres, summary = ic.checks.mesh_metrics(self.case, self.config)
        alpha = [0.5] * geometry["cells"]
        bc = {"wall": {"type": ["inletOutlet"], "inletValue": ["uniform", "0"], "value": ["uniform", "0"]}}
        self.assertEqual(ic.boundary_for_alpha(self.case, bc, alpha, geometry), bc)
        equivalent = copy.deepcopy(bc)
        equivalent["wall"]["value"] = ic.scalar_entry([0] * geometry["patches"]["wall"])
        equivalent["wall"]["inletValue"] = ["uniform", "0.0"]
        self.assertEqual(ic.boundary_for_alpha(self.case, equivalent, alpha, geometry), bc)
        bc["wall"]["inletValue"] = ["uniform", "0.1"]
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.boundary_for_alpha(self.case, bc, alpha, geometry)
        with self.assertRaises(ic.N.ReviewRequired):
            ic.boundary_for_alpha(self.case, {"wall": {"type": ["fixedValue"]}}, alpha, geometry)

    def test_wrong_boundary_count_and_nonfinite_values_rejected(self):
        self.initialize()
        geometry, *_ = ic.checks.mesh_metrics(self.case, self.config)
        path = self.case / "0/alpha.metal"
        path.write_text(f.fixtures.field("alpha.metal", "uniform 0.5", boundary="wall {type fixedValue; value uniform nan;}"))
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.checks.field_check(path, geometry, initial=True)
        path.write_text(f.fixtures.field("alpha.metal", "uniform 0.5", boundary="wall {type fixedValue; value nonuniform List<scalar> 1(0);}"))
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.checks.field_check(path, geometry, initial=True)

    def test_wrong_coordinate_and_nonpositive_reference_volume_rejected(self):
        self.initialize()
        record = ic.manifest(self.case)
        ref = ic.reference(self.case, record)
        geometry, volumes, centres, summary = ic.checks.mesh_metrics(self.case, self.config)
        bad = copy.deepcopy(centres)
        bad[0][0] += 1e-6
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.expected_alpha(ref, bad, volumes, summary)
        ref["volumes"][0] = 0
        with self.assertRaises(ic.N.ComparisonFailure):
            ic.expected_alpha(ref, centres, volumes, summary)

    def test_missing_initialization_exit_is_not_pass(self):
        self.initialize()
        (self.case / "exit.restrictAlpha.txt").unlink()
        self.assertNotEqual(self.check(mesh_only=True)["status"], "MESH_INITIALIZATION_CHECKS_PASSED")

    def test_cli_writes_controlled_mesh_evidence_and_offline_report(self):
        self.initialize()
        with redirect_stdout(io.StringIO()):
            code = ic.main(["check", "--case-dir", str(self.case), "--mesh-only"])
        self.assertEqual(code, 0)
        result = json.loads((self.case / "mesh-summary.json").read_text())
        self.assertEqual(result["controlled_initialization"]["status"], "PASS")

    def test_three_way_feedback_and_material_guard(self):
        report = self.complete()
        (self.case / "m.json").write_text(json.dumps(report))
        out = self.root / "validation/three-way"
        with patch.object(three.subprocess, "check_output", return_value=self.commit), redirect_stdout(io.StringIO()):
            code = three.main(["--m1-case-dir", str(self.a), "--m3-case-dir", str(self.b),
                "--ic-case-dir", str(self.case), "--report-dir", str(out)])
        self.assertEqual(code, 0)
        with tarfile.open(out / "m1-ic-comparison-feedback.tar.gz", "r:gz") as archive:
            self.assertEqual(len(archive.getmembers()), 9)
            self.assertTrue(all(m.isfile() for m in archive.getmembers()))
        # An unrelated control change cannot hide in the shortened controlDict.
        p = self.case / "system/controlDict"
        p.write_text(p.read_text().replace("deltaT 1e-8", "deltaT 2e-8"))
        f.fixtures.record_inputs(self.case)
        with self.assertRaises(ic.N.ComparisonFailure):
            three.compare(self.a, self.b, self.case, {"status": "COMPARISON_COMPLETED", "issues": []})

    def test_pre_intervention_alpha_must_match_native_m1(self):
        original = ic.initialize
        def corrupted(case):
            (case / "0/alpha.metal").write_text(f.fixtures.field("alpha.metal", "uniform 0"))
            return original(case)
        with patch.object(ic, "initialize", side_effect=corrupted), self.assertRaisesRegex(ic.N.ComparisonFailure, "pre-intervention"):
            self.initialize()
        self.assertFalse((self.case / "ic-initialization.json").exists())


class AuthorizedConfig(unittest.TestCase):
    def test_exact_owner_profile(self):
        config = ic.config_for()
        self.assertEqual(config["cells"], [40, 20, 40])
        self.assertEqual(config["steps"], 300)
        self.assertEqual(config["solver_timeout_seconds"], 600)
        self.assertEqual(config["formal_benchmark"], "PROPOSED")


if __name__ == "__main__":
    unittest.main()
