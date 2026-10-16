"""Synthetic multi-output M fixtures; no OpenFOAM, simulation or CFD reference."""
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_m_case as m

SPEC = importlib.util.spec_from_file_location("m_field_fixtures", ROOT / "tests/test_compare_plate2d_ab.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


def field(name, values, boundary="wall {type zeroGradient;}", dimensions=None, field_class=None):
    vectors = name in ("U", "B")
    field_class = field_class or ("volVectorField" if vectors else "surfaceScalarField" if name == "phi" else "volScalarField")
    dims = dimensions if dimensions is not None else {
        "T": [0, 0, 0, 1, 0, 0, 0], "U": [0, 1, -1, 0, 0, 0, 0],
        "p_rgh": [1, -1, -2, 0, 0, 0, 0], "Deposition": m.DEPOSITION_DIMENSIONS}.get(name, [0] * 7)
    return fixtures.field(field_class, values, boundary).replace("dimensions [0 0 0 0 0 0 0]",
            "dimensions [" + " ".join(map(str, dims)) + "]")


def write_cartesian_mesh(case):
    """Two real closed hexahedra sharing one face, with native cell ordering."""
    directory = case / "constant/polyMesh"
    directory.mkdir(parents=True)
    points = [(x, y, z) for x in (-3e-4, 0, 3e-4) for y in (0, 3e-4) for z in (-1e-4, 5e-4)]
    faces = {}
    for cell in range(2):
        box = [i for i, (x, _, _) in enumerate(points) if -3e-4 + cell * 3e-4 <= x <= cell * 3e-4]
        for axis in range(3):
            for side in (min(points[i][axis] for i in box), max(points[i][axis] for i in box)):
                labels = tuple(i for i in box if points[i][axis] == side)
                if labels in faces:
                    faces[labels].append(cell)
                else:
                    faces[labels] = [cell]
    ordered = sorted(faces.items(), key=lambda item: -len(item[1]))
    owner = [cells[0] for _, cells in ordered]
    neighbour = [cells[1] for _, cells in ordered if len(cells) == 2]
    (directory / "points").write_text(fixtures.header("vectorField") + str(len(points)) + "(\n" +
        "\n".join("(" + " ".join(map(str, p)) + ")" for p in points) + "\n)\n")
    (directory / "faces").write_text(fixtures.header("faceList") + str(len(ordered)) + "(\n" +
        "\n".join("4(" + " ".join(map(str, labels)) + ")" for labels, _ in ordered) + "\n)\n")
    for name, values in (("owner", owner), ("neighbour", neighbour)):
        (directory / name).write_text(fixtures.header("labelList") + str(len(values)) + "(" + " ".join(map(str, values)) + ")\n")
    (directory / "boundary").write_text(fixtures.header("polyBoundaryMesh") +
        "1(wall {type wall; nFaces 10; startFace 1;})\n")


def record_inputs(case):
    prepared = [p for root in ("initial", "constant", "system") for p in (case / root).rglob("*")
                if p.is_file() and "polyMesh" not in p.parts]
    initialized = [p for root in ("0", "constant/polyMesh") for p in (case / root).rglob("*") if p.is_file()]
    for name, paths in (("inputs.sha256", prepared), ("initialized.sha256", initialized)):
        (case / name).write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(case).as_posix() + "\n"
                                      for p in sorted(paths)))


class MChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.case = Path(self.tmp.name) / "case"
        self.case.mkdir()
        for directory in ("initial", "system", "0"):
            (self.case / directory).mkdir()
        write_cartesian_mesh(self.case)
        self.config = {"schema": "threeD-exploration-v1", "status": "EXPLORATION_AUTHORIZED",
            "formal_benchmark": "PROPOSED", "id": "M1", "cells": [2, 1, 1], "steps": 4,
            "write_interval": 2, "delta_t": "1e-8", "end_time": "4e-8", "solver_timeout_seconds": 1800,
            "max_rss_kib": 8388608, "max_data_bytes": 3221225472}
        self.write_manifest()
        (self.case / "system/controlDict").write_text("application laserbeamFoam;\n")
        (self.case / "constant/material").write_text("synthetic constant\n")
        for name in m.INITIAL_REQUIRED:
            value = "uniform (0 0 0)" if name == "U" else "uniform 300" if name == "T" else (
                    "nonuniform List<scalar> 2(1 0)" if name == "alpha.metal" else "uniform 0")
            for directory in ("initial", "0"):
                (self.case / directory / name).write_text(field(name, value))
        for directory in ("2e-8", "4e-8"):
            output = self.case / directory
            (output / "uniform/functionObjects/nested").mkdir(parents=True)
            (output / "uniform/time").write_text(fixtures.header("dictionary") + "value " + directory + ";\n")
            # Source-derived v2512 initContinuityErrs.H AUTO_WRITE state.
            (output / "uniform/cumulativeContErr").write_text(
                "FoamFile {version 2.0; format ascii; class uniformDimensionedScalarField; "
                "object cumulativeContErr;}\ndimensions [0 0 0 0 0 0 0];\nvalue 0;\n")
            (output / "uniform/functionObjects/nested/state").write_text("reader { lastTime 0; }\n")
            for name in m.REQUIRED | {"B"}:
                value = {"T": "nonuniform List<scalar> 2(600 1000)",
                    "alpha.metal": "nonuniform List<scalar> 2(1 0)",
                    "epsilon1": "nonuniform List<scalar> 2(0 1)", "Deposition": "uniform 2",
                    "U": "nonuniform List<vector> 2((1 0 0)(0 0 0))", "B": "uniform (0 0 0)"}.get(name, "uniform 0")
                (output / name).write_text(field(name, value))
        (self.case / ".mesh-complete").touch()
        self.write_log()
        (self.case / "solver.exit.txt").write_text("0\n")
        (self.case / "execution.txt").write_text("mpi_ranks=1\nthreads=1\n")
        for stage in ("blockMesh", "checkMesh", "setFields"):
            (self.case / ("log." + stage)).write_text(("Mesh OK.\n" if stage == "checkMesh" else "") + "End\n")
            (self.case / ("exit." + stage + ".txt")).write_text("0\n")
        for stage in ("blockMesh", "checkMesh", "setFields", "laserbeamFoam"):
            (self.case / ("time." + stage + ".txt")).write_text(
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\nMaximum resident set size (kbytes): 1200\n")
        record_inputs(self.case)

    def tearDown(self):
        self.tmp.cleanup()

    def write_manifest(self):
        (self.case / "manifest.json").write_text(json.dumps({"experiment_id": "M1", "solver": "laserbeamFoam",
            "mpi_ranks": 1, "project_commit": "a" * 40, "build_commit": "a" * 40, "config": self.config}))

    def write_log(self):
        lines = [fixtures.TRAPFPE_BANNER, "Laser: laser0", "Total rays: 150, local particles: 150"]
        for step in range(1, self.config["steps"] + 1):
            lines.extend(["Time = {:.12g}".format(step * 1e-8), "Courant Number mean: 0 max: 0",
                "Phase-1 volume fraction = 0.5 Min(alpha.metal) = 0 Max(alpha.metal) = 1",
                "Total Q deposited: 2", "smoothSolver: Solving for T, Initial residual = 1e-5, Final residual = 1e-10, No Iterations 2",
                "GAMG: Solving for p_rgh, Initial residual = 1e-6, Final residual = 1e-9, No Iterations 3",
                "Correcting epsilon1, mean residual = 1e-5, max residual = 1e-4",
                "time step continuity errors : sum local = 1e-12, global = 0, cumulative = 0",
                "ExecutionTime = {:.4g} s ClockTime = {} s".format(step * 0.02, step // 3)])
        (self.case / "log.laserbeamFoam").write_text("\n".join(lines) + "\nEnd\n")

    def report(self):
        return m.check(self.case)

    def assert_status(self, expected):
        report = self.report()
        self.assertEqual(report["status"], expected, report["issues"])
        return report

    def test_all_times_native_fields_and_observations(self):
        report = self.assert_status(m.PASSED)
        self.assertEqual(len(report["fields"]), 2)
        self.assertEqual(sum(len(fields) for fields in report["fields"].values()), 16)
        self.assertEqual(report["steps"], 4)
        self.assertEqual(report["cells"], 2)
        self.assertEqual(report["accuracy"], "UNVERIFIED")
        self.assertAlmostEqual(report["mesh"]["total_volume_m3"], 1.08e-10)
        self.assertAlmostEqual(report["initial_metal_volume_m3"], 5.4e-11)
        row = report["observations"][0]
        self.assertEqual(row["metal_T_max_K"], 600)
        self.assertEqual(row["T_max_K"], 1000)
        self.assertEqual(row["metal_epsilon_max"], 0)
        self.assertFalse(row["nonzero_metal_liquid_fraction"])
        self.assertEqual(row["liquid_metal_volume_estimate_m3"], 0)
        self.assertAlmostEqual(row["deposition_power_W"], 2.16e-10)
        self.assertEqual(row["metal_U_max_m_per_s"], 1)
        self.assertEqual(row["metal_volume_relative_change"], 0)
        self.assertEqual(report["resources"]["solver_wall_seconds"], 1.25)
        self.assertEqual(report["resources"]["max_rss_kib"], 1200)
        self.assertEqual(report["linear_summaries"]["p_rgh"]["iterations_total"], 12)
        self.assertFalse(report["execution_times"][0]["clock_difference_resolved"])
        self.assertEqual(report["path_evidence"]["multiple_reflections"], "NOT_ESTABLISHED")

    def test_missing_output_time_fails(self):
        shutil.rmtree(self.case / "2e-8")
        self.assert_status("FAIL")

    def test_extra_output_time_fails(self):
        (self.case / "3e-8").mkdir()
        self.assert_status("FAIL")

    def test_duplicate_numeric_time_fails(self):
        (self.case / "0.00000002").mkdir()
        self.assert_status("FAIL")

    def test_missing_field_and_different_fieldset_fail(self):
        (self.case / "4e-8/T").unlink()
        report = self.assert_status("FAIL")
        self.assertIn("missing fields: T", str(report["issues"]))

    def test_unsupported_extra_field_needs_review(self):
        for time_dir in ("2e-8", "4e-8"):
            (self.case / time_dir / "unsupported").write_bytes(b"\x00\xff")
        self.assert_status("REVIEW_REQUIRED")

    def test_nonfinite_boundary_fails_with_path(self):
        (self.case / "2e-8/T").write_text(field("T", "uniform 600", "wall {type fixedValue; value uniform nan;}"))
        report = self.assert_status("FAIL")
        self.assertIn("2e-8/T", report["issues"][0]["message"])
        self.assertIn("4e-8", report["fields"])

    def test_wrong_internal_or_boundary_count_fails(self):
        for value, boundary in (("nonuniform List<scalar> 1(600)", "wall {type zeroGradient;}"),
                                ("uniform 600", "wall {type fixedValue; value nonuniform List<scalar> 1(600);}")):
            with self.subTest(value=value):
                (self.case / "2e-8/T").write_text(field("T", value, boundary))
                self.assert_status("FAIL")

    def test_alpha_boundary_out_of_bounds_fails(self):
        (self.case / "2e-8/alpha.metal").write_text(field("alpha.metal", "uniform 0.5", "wall {type fixedValue; value uniform 1.1;}"))
        self.assert_status("FAIL")

    def test_alpha_inlet_and_reference_values_are_bounded(self):
        for key in ("inletValue", "refValue"):
            with self.subTest(key=key):
                (self.case / "2e-8/alpha.metal").write_text(field("alpha.metal", "nonuniform List<scalar> 2(1 0)",
                    "wall {type mixed; value uniform 0.5; " + key + " uniform 1.1;}"))
                report = self.assert_status("FAIL")
                self.assertIn("internal/boundary outside", report["issues"][0]["message"])

    def test_alpha_gradient_is_not_misclassified_as_alpha_value(self):
        (self.case / "2e-8/alpha.metal").write_text(field("alpha.metal", "nonuniform List<scalar> 2(1 0)",
            "wall {type fixedGradient; gradient uniform 2; value uniform 0.5;}"))
        self.assert_status(m.PASSED)

    def test_deposition_dimensions_not_assumed(self):
        (self.case / "2e-8/Deposition").write_text(field("Deposition", "uniform 2", dimensions=[0] * 7))
        report = self.assert_status("FAIL")
        self.assertIn("dimensions", str(report["issues"]))

    def test_velocity_class_cannot_masquerade_as_scalar(self):
        (self.case / "2e-8/U").write_text(field("U", "uniform 0", field_class="volScalarField"))
        self.assert_status("FAIL")

    def test_true_positive_liquid_is_separate_from_region(self):
        (self.case / "2e-8/epsilon1").write_text(field("epsilon1", "nonuniform List<scalar> 2(0.1 1)"))
        row = self.assert_status(m.PASSED)["observations"][0]
        self.assertTrue(row["nonzero_metal_liquid_fraction"])
        self.assertEqual(row["threshold_liquid_region_cells"], 0)
        self.assertFalse(row["solidus_reached"])
        self.assertAlmostEqual(row["liquid_metal_volume_estimate_m3"], 5.4e-12)

    def test_missing_uniform_fails(self):
        shutil.rmtree(self.case / "2e-8/uniform")
        self.assert_status("FAIL")

    def test_opaque_uniform_self_identity_requires_review(self):
        path = self.case / "2e-8/uniform/functionObjects/nested/state"
        path.write_text("unparsed identical opaque state\n")
        report = self.assert_status("REVIEW_REQUIRED")
        self.assertTrue(any("Self-byte identity" in item["message"] for item in report["issues"]))

    def test_unknown_declared_uniform_class_is_not_headerless_dictionary(self):
        path = self.case / "2e-8/uniform/functionObjects/nested/state"
        path.write_text(fixtures.header("unrecognizedStateClass") + "value 0;\n")
        self.assert_status("REVIEW_REQUIRED")

    def test_changed_inputs_fail(self):
        (self.case / "0/T").write_text(field("T", "uniform 350"))
        self.assert_status("FAIL")

    def test_native_volume_geometry_cannot_be_guessed(self):
        path = self.case / "constant/polyMesh/points"
        path.write_text(path.read_text().replace("0.0003 0.0003", "0.00031 0.0003", 1))
        record_inputs(self.case)
        self.assertNotEqual(self.report()["status"], m.PASSED)

    def test_roundoff_plane_jitter_is_clustered_and_reported(self):
        path = self.case / "constant/polyMesh/points"
        path.write_text(path.read_text().replace("-0.0003 0 -0.0001", "-0.000299999999999999 0 -0.0001", 1))
        record_inputs(self.case)
        report = self.assert_status(m.PASSED)
        self.assertGreater(report["mesh"]["coordinate_roundoff_tolerance_m"], 1e-18)
        self.assertGreater(report["mesh"]["coordinate_values_collapsed_per_axis"][0], 0)

    def test_derived_velocity_overflow_cannot_false_pass(self):
        (self.case / "2e-8/U").write_text(field("U", "uniform (1.7e308 1.7e308 1.7e308)"))
        self.assert_status("FAIL")

    def test_symlink_output_or_uniform_fails(self):
        for path in (self.case / "4e-8/escape", self.case / "2e-8/uniform/escape"):
            try:
                path.symlink_to(self.case / "solver.exit.txt")
            except OSError:
                self.skipTest("symlink creation unavailable")
            try:
                self.assert_status("FAIL")
            finally:
                path.unlink()

    def test_nonzero_exit_or_real_fatal_fails(self):
        (self.case / "solver.exit.txt").write_text("124")
        self.assert_status("FAIL")
        (self.case / "solver.exit.txt").write_text("0")
        path = self.case / "log.laserbeamFoam"
        path.write_text(path.read_text().replace("End\n", "Floating point exception (core dumped)\nEnd\n"))
        self.assert_status("FAIL")

    def test_missing_end_wrong_steps_or_fixed_dt_fail(self):
        path = self.case / "log.laserbeamFoam"
        original = path.read_text()
        for text in (original.replace("End\n", ""), original.replace("Time = 4e-08", "Time = 5e-08"),
                     original.replace("Time = 2e-08\n", "")):
            with self.subTest(text=text[-30:]):
                path.write_text(text)
                self.assert_status("FAIL")

    def test_missing_solver_timer_needs_review(self):
        (self.case / "time.laserbeamFoam.txt").unlink()
        self.assert_status("REVIEW_REQUIRED")

    def test_nonconvergence_alert_requires_review_without_new_residual_threshold(self):
        path = self.case / "log.laserbeamFoam"
        path.write_text(path.read_text().replace("End\n", "PIMPLE: not converged within 10 iterations\nEnd\n"))
        report = self.assert_status("REVIEW_REQUIRED")
        self.assertIn("not converged", report["solver_alerts"][0]["message"])

    def test_residual_increase_is_reported_without_invented_acceptance_threshold(self):
        path = self.case / "log.laserbeamFoam"
        path.write_text(path.read_text().replace("Final residual = 1e-10", "Final residual = 1e-4"))
        report = self.assert_status(m.PASSED)
        self.assertEqual(report["linear_summaries"]["T"]["final_residual_greater_than_initial_count"], 4)

    def test_invalid_residuals_and_iteration_counts_cannot_false_pass(self):
        path = self.case / "log.laserbeamFoam"
        original = path.read_text()
        for old, new, expected in (("Final residual = 1e-10", "Final residual = -1e-10", "FAIL"),
                                   ("No Iterations 2", "No Iterations -2", "FAIL"),
                                   ("No Iterations 2", "No Iterations 2.5", "REVIEW_REQUIRED")):
            with self.subTest(new=new):
                path.write_text(original.replace(old, new))
                self.assert_status(expected)

    def test_resource_over_budget_is_reported_not_silent_enforced_claim(self):
        self.config["max_rss_kib"] = 1
        self.config["max_data_bytes"] = 1
        self.write_manifest()
        resources = self.assert_status(m.PASSED)["resources"]
        self.assertFalse(resources["rss_within_observation_budget"])
        self.assertFalse(resources["data_within_observation_budget"])
        self.assertEqual(resources["resource_policy"], "MONITORED_ONLY")

    def test_initialization_rss_budget_uses_max_stage_not_only_solver(self):
        (self.case / "time.setFields.txt").write_text(
            "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.25\nMaximum resident set size (kbytes): 8388609\n")
        resources = self.assert_status(m.PASSED)["resources"]
        self.assertEqual(resources["max_rss_kib"], 8388609)
        self.assertEqual(resources["solver_max_rss_kib"], 1200)
        self.assertFalse(resources["rss_within_observation_budget"])

    def test_missing_initialization_timer_does_not_claim_full_resource_evidence(self):
        (self.case / "time.setFields.txt").unlink()
        self.assert_status("REVIEW_REQUIRED")

    def test_completed_workflow_scope(self):
        (self.case / "preparation.time.txt").write_text("preparation_wall_seconds=0.5\n")
        for stage in ("mesh", "solve"):
            (self.case / ("time.workflow." + stage + ".txt")).write_text(
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:02.00\nMaximum resident set size (kbytes): 2000\n")
        report = self.assert_status(m.PASSED)
        self.assertEqual(report["resources"]["recorded_workflow_wall_seconds"], 4.5)

    def test_mesh_only_fresh_initialization_and_no_fake_solver_pass(self):
        for directory in ("2e-8", "4e-8"):
            shutil.rmtree(self.case / directory)
        (self.case / ".mesh-complete").unlink()
        report = m.check(self.case, mesh_only=True)
        self.assertEqual(report["status"], "MESH_INITIALIZATION_CHECKS_PASSED", report["issues"])
        self.assertEqual(m.main(["--case-dir", str(self.case), "--mesh-only"]), 0)
        self.assertFalse((self.case / "m.json").exists())
        self.assertTrue((self.case / "mesh-summary.json").exists())
        mesh_report = json.loads((self.case / "mesh-summary.json").read_text())
        self.assertEqual(mesh_report["check_status"], "MESH_INITIALIZATION_CHECKS_PASSED")
        initial = mesh_report["initialization"]
        self.assertEqual(initial["status"], "PASS")
        self.assertEqual(initial["fields_checked"], 5)
        self.assertEqual(set(initial["field_names"]), m.INITIAL_REQUIRED)
        self.assertEqual(initial["metal_cells"], 1)
        self.assertAlmostEqual(initial["metal_volume_m3"], 5.4e-11)
        self.assertEqual(initial["metal_T_max_K"], 300)
        self.assertIn("Initial fields checked: 5; initialization: PASS", (self.case / "mesh-check.txt").read_text())

    def test_failed_mesh_summary_cannot_retain_prior_success(self):
        (self.case / "mesh-summary.json").write_text('{"check_status":"MESH_INITIALIZATION_CHECKS_PASSED"}')
        (self.case / "exit.setFields.txt").write_text("1")
        self.assertEqual(m.main(["--case-dir", str(self.case), "--mesh-only"]), 1)
        result = json.loads((self.case / "mesh-summary.json").read_text())
        self.assertEqual(result["check_status"], "FAIL")
        self.assertEqual(result["initialization"]["status"], "NOT_ESTABLISHED")
        self.assertTrue(result["issues"])

    def test_mesh_only_rejects_existing_evolution(self):
        self.assertEqual(m.check(self.case, mesh_only=True)["status"], "FAIL")

    def test_full_check_without_mesh_completion_marker_fails(self):
        (self.case / ".mesh-complete").unlink()
        self.assert_status("FAIL")

    def test_cli_reports_all_times_and_feedback_failure_preserves_code(self):
        with patch("export_smoke_feedback.export_feedback", side_effect=ValueError("mock packing failure")):
            self.assertEqual(m.main(["--case-dir", str(self.case), "--feedback-bundle"]), 0)
        for name in ("m.json", "m.txt", "observations.csv", "execution_times.csv", "mesh-summary.json"):
            self.assertTrue((self.case / name).is_file(), name)
        self.assertEqual(len((self.case / "observations.csv").read_text().splitlines()), 3)
        self.assertEqual(len((self.case / "execution_times.csv").read_text().splitlines()), 5)
        self.assertEqual(json.loads((self.case / "m.json").read_text())["status"], m.PASSED)

    def test_cannot_return_success_if_report_write_fails(self):
        with patch.object(Path, "write_text", side_effect=OSError("mock disk full")):
            self.assertEqual(m.main(["--case-dir", str(self.case)]), 2)

    def test_hardlinked_report_is_not_overwritten(self):
        source = Path(self.tmp.name) / "external-report"
        source.write_text("retain external evidence")
        os.link(source, self.case / "m.json")
        self.assertEqual(m.main(["--case-dir", str(self.case)]), 2)
        self.assertEqual(source.read_text(), "retain external evidence")

    def test_nested_symlink_cli_returns_failure_not_fake_pass(self):
        try:
            (self.case / "4e-8/escape").symlink_to(self.case / "solver.exit.txt")
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.assertEqual(m.main(["--case-dir", str(self.case)]), 1)
        self.assertEqual(json.loads((self.case / "m.json").read_text())["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
