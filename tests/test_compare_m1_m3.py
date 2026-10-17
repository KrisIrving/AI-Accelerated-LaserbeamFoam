"""Tiny real Cartesian addressing fixtures; no CFD, physical validation or AI."""
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compare_m1_m3 as c

SPEC = importlib.util.spec_from_file_location("cross_grid_fixtures", ROOT / "tests/test_m_checks.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


def mesh(case, shape, reverse=False):
    bounds = ((-3e-4, 3e-4), (0, 3e-4), (-1e-4, 5e-4))
    axes = [[lo + i * (hi - lo) / n for i in range(n + 1)] for (lo, hi), n in zip(bounds, shape)]
    points = [(x, y, z) for x in axes[0] for y in axes[1] for z in axes[2]]
    point_labels = {p: i for i, p in enumerate(points)}
    keys = list(c.itertools.product(*(range(n) for n in shape)))
    if reverse:
        keys.reverse()
    faces = {}
    centres = []
    for cell, key in enumerate(keys):
        edges = [(axes[a][key[a]], axes[a][key[a] + 1]) for a in range(3)]
        vertices = list(c.itertools.product(*edges))
        centres.append([sum(pair) / 2 for pair in edges])
        for axis in range(3):
            for side in edges[axis]:
                labels = tuple(sorted(point_labels[p] for p in vertices if p[axis] == side))
                faces.setdefault(labels, []).append(cell)
    ordered = sorted(faces.items(), key=lambda item: -len(item[1]))
    internal = sum(len(cells) == 2 for _, cells in ordered)
    directory = case / "constant/polyMesh"
    directory.mkdir(parents=True)
    header = fixtures.fixtures.header
    (directory / "points").write_text(header("vectorField") + str(len(points)) + "(\n" +
        "\n".join("(" + " ".join(map(str, p)) + ")" for p in points) + "\n)\n")
    (directory / "faces").write_text(header("faceList") + str(len(ordered)) + "(\n" +
        "\n".join("4(" + " ".join(map(str, labels)) + ")" for labels, _ in ordered) + "\n)\n")
    for name, values in (("owner", [v[0] for _, v in ordered]),
                         ("neighbour", [v[1] for _, v in ordered if len(v) == 2])):
        (directory / name).write_text(header("labelList") + str(len(values)) + "(" + " ".join(map(str, values)) + ")\n")
    (directory / "boundary").write_text(header("polyBoundaryMesh") +
        "1(wall {type wall; nFaces " + str(len(ordered) - internal) + "; startFace " + str(internal) + ";})\n")
    return centres


class ComparisonFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a, self.b = self.root / "runs/M1", self.root / "runs/M3"
        self.make_case(self.a, "M1", [2, 2, 2])
        self.make_case(self.b, "M3", [4, 4, 4], reverse=True)

    def make_case(self, path, label, shape, reverse=False):
        path.mkdir(parents=True)
        centres = mesh(path, shape, reverse)
        self.centres = getattr(self, "centres", {})
        self.centres[label] = centres
        for folder in ("initial", "system", "0", "1e-6", "2e-6"):
            (path / folder).mkdir()
        config = {"schema": "threeD-exploration-v1", "status": "EXPLORATION_AUTHORIZED",
            "formal_benchmark": "PROPOSED", "id": label, "cells": shape, "steps": 200,
            "write_interval": 100, "delta_t": "1e-8", "end_time": "2e-6"}
        commit = "a" * 40 if label == "M1" else "b" * 40
        (path / "manifest.json").write_text(json.dumps({"experiment_id": label, "solver": "laserbeamFoam",
            "mpi_ranks": 1, "project_commit": commit, "build_commit": commit, "config": config}))
        (path / "m.json").write_text(json.dumps({"status": c.checks.PASSED, "project_commit": commit,
                                               "build_commit": commit, "offline_check_wall_seconds": 0.1}))
        header = fixtures.fixtures.header
        (path / "system/controlDict").write_text("application laserbeamFoam;\n")
        (path / "system/blockMeshDict").write_text("synthetic shape " + str(shape))
        (path / "system/setFieldsDict").write_text(header("dictionary") +
            "defaultFieldValues (volScalarFieldValue alpha.metal 0);\nregions (boxToCell {\n"
            "box (-400e-6 100.1e-6 -0.5)(400e-6 500.1e-6 0.5);\n"
            "fieldValues (volScalarFieldValue alpha.metal 1);});\n")
        (path / "constant/LaserProperties").write_text(header("dictionary") +
            'lasers (laser0 {V_incident (0 1 0); laserRadius 55e-6;\n'
            'timeVsLaserPosition {file "$FOAM_CASE/constant/timeVsLaserPosition0"; outOfBounds clamp;} });\n')
        (path / "constant/timeVsLaserPosition0").write_text("((0 (-200e-6 10e-6 0))(1 (-200e-6 10e-6 0.06)))\n")
        for folder in ("0", "1e-6", "2e-6"):
            for name in (("T", "alpha.metal") if folder == "0" else c.FIELDS):
                values = [(1 if y > 100.1e-6 else 0) if name == "alpha.metal" else
                          300 if name == "T" and folder == "0" else
                          1000 if name == "T" else 0.5 if name == "epsilon1" else 2
                          for _, y, _ in centres]
                self.write_field(path, folder, name, values)
        for name in ("T", "alpha.metal"):
            # Prepared templates are identical; evolved initialized fields are not.
            (path / "initial" / name).write_text(fixtures.field(name, "uniform 300" if name == "T" else "uniform 0"))
        fixtures.record_inputs(path)
        dummy = fixtures.MChecks(methodName="test_all_times_native_fields_and_observations")
        dummy.config, dummy.case = config, path
        dummy.write_log()
        (path / "solver.exit.txt").write_text("0\n")
        for name in ("solver.time.txt", "time.workflow.mesh.txt", "time.workflow.solve.txt"):
            (path / name).write_text("Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\nMaximum resident set size (kbytes): 1200\n")
        (path / "preparation.time.txt").write_text("preparation_wall_seconds=0.1\n")

    def write_field(self, path, folder, name, values):
        if name == "U":
            content = "nonuniform List<vector> " + str(len(values)) + "(" + " ".join("(1 0 0)" for _ in values) + ")"
        else:
            content = "nonuniform List<scalar> " + str(len(values)) + "(" + " ".join(map(str, values)) + ")"
        (path / folder / name).write_text(fixtures.field(name, content))

    def compare(self, times=None):
        report = {"status": "COMPARISON_COMPLETED", "issues": []}
        with redirect_stdout(io.StringIO()):
            c.compare_cases(self.a, self.b, report, times)
        return report

    def run_cli(self, report_dir=None):
        out = report_dir or self.root / "validation/comparison"
        with patch.object(c, "REPO", self.root), patch.object(c.subprocess, "check_output", return_value="c" * 40 + "\n"), redirect_stdout(io.StringIO()):
            code = c.main(["--m1-case-dir", str(self.a), "--m3-case-dir", str(self.b), "--report-dir", str(out)])
        return code, out

    def test_native_mapping_ignores_reversed_fine_cell_order(self):
        report = self.compare()
        self.assertEqual(report["status"], "COMPARISON_COMPLETED", report["issues"])
        self.assertEqual(report["mapping"]["fine_children_per_coarse_cell"], 8)
        self.assertEqual(len(report["times_s"]), 2)
        self.assertAlmostEqual(report["mapped_differences"]["0.000001"]["T"]["Linf"], 0, delta=1e-10)
        self.assertAlmostEqual(report["mapped_differences"]["0.000001"]["U"]["Linf"], 0, delta=1e-12)
        self.assertTrue(report["consumed_sources_unchanged_during_comparison"])

    def test_actual_initial_alpha_difference_is_preserved(self):
        report = self.compare()
        self.assertAlmostEqual(report["initial"]["M1"]["effective_surface_y_m"], 150e-6)
        self.assertAlmostEqual(report["initial"]["M3"]["effective_surface_y_m"], 75e-6)
        self.assertAlmostEqual(report["initial"]["mapped_alpha_difference"]["L1"], 0.25)
        self.assertAlmostEqual(report["initial"]["metal_volume_relative_difference_M3_vs_M1"], 0.5)
        self.assertTrue(report["initial"]["M1"]["box_selection_audit"]["raw_alpha_matches_centre_selection"])
        self.assertTrue(report["initial"]["M3"]["box_selection_audit"]["raw_alpha_matches_centre_selection"])
        self.assertEqual(len(report["profiles"]), 18)

    def test_laser_plane_geometry_and_profile_sampling_offsets(self):
        report = self.compare(["1e-6"])
        rows = [r for r in report["laser_geometry"] if r["time_s"] == 0]
        self.assertAlmostEqual(rows[0]["forward_distance_to_initial_plane_m"], 140e-6)
        self.assertAlmostEqual(rows[1]["forward_distance_to_initial_plane_m"], 65e-6)
        self.assertTrue(report["laser_profiles"])
        self.assertIn("sample_offset_x_m", rows[0])

    def test_spatially_different_temperature_is_not_false_equivalence(self):
        self.write_field(self.b, "1e-6", "T", [1100] * 64)
        report = self.compare(["1e-6"])
        self.assertEqual(report["status"], "COMPARISON_COMPLETED")
        self.assertAlmostEqual(report["mapped_differences"]["0.000001"]["T"]["L2"], 100)

    def test_deposition_integral_and_peak_are_separate(self):
        report = self.compare()
        rows = report["metrics"][:2]
        self.assertAlmostEqual(rows[0]["deposition_signed_integral_W"], 2 * 1.08e-10)
        self.assertAlmostEqual(rows[0]["deposition_signed_integral_W"], rows[1]["deposition_signed_integral_W"])
        self.assertEqual(rows[0]["deposition_peak_W_m3"], 2)
        self.assertAlmostEqual(rows[1]["deposition_positive_effective_volume_m3"], 1.08e-10)

    def test_nan_native_field_fails_with_path(self):
        self.write_field(self.b, "1e-6", "T", [float("nan")] * 64)
        with self.assertRaisesRegex(c.native.ComparisonFailure, "M3/1e-6/T"):
            self.compare()

    def test_wrong_dimensions_and_missing_field_fail(self):
        path = self.b / "1e-6/T"
        path.write_text(path.read_text().replace("dimensions [0 0 0 1 0 0 0]", "dimensions [0 0 0 0 0 0 0]"))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "dimensions"):
            self.compare()
        path.unlink()
        with self.assertRaisesRegex(c.native.ComparisonFailure, "M3/1e-6/T"):
            self.compare()

    def test_initial_hash_change_cannot_be_silently_corrected(self):
        (self.b / "0/alpha.metal").write_text(fixtures.field("alpha.metal", "uniform 1"))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "input path/hash mismatch"):
            self.compare()

    def test_missing_output_or_duplicate_numeric_time_fails(self):
        (self.b / "2e-6").rename(self.b / "3e-6")
        with self.assertRaisesRegex(c.native.ComparisonFailure, "output times"):
            self.compare()
        (self.b / "3e-6").rename(self.b / "1e-06")
        with self.assertRaisesRegex(c.native.ComparisonFailure, "duplicate"):
            self.compare()

    def test_report_provenance_and_full_check_are_required(self):
        report = json.loads((self.b / "m.json").read_text())
        report["project_commit"] = "c" * 40
        (self.b / "m.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "provenance"):
            self.compare()
        report.update(project_commit="b" * 40, status="REVIEW_REQUIRED")
        (self.b / "m.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "not PASS"):
            self.compare()

    def test_unexpected_physics_input_change_is_reported_not_normalized(self):
        path = self.b / "constant/LaserProperties"
        path.write_text(path.read_text().replace("55e-6", "65e-6"))
        fixtures.record_inputs(self.b)
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertIn("constant/LaserProperties", str(report["issues"]))
        self.assertEqual(len(report["metrics"]), 4)

    def test_source_changed_during_comparison_fails(self):
        source = c.Source(self.a, "M1")
        source.file("0/T")
        (self.a / "0/T").write_text("changed")
        with self.assertRaisesRegex(c.native.ComparisonFailure, "changed during"):
            source.unchanged()

    def test_native_invalid_cell_volume_is_rejected(self):
        source = c.load_case(self.a, "M1")
        bad = list(source["grid"]["volumes"])
        bad[0] *= 0.5
        with self.assertRaisesRegex(c.native.ComparisonFailure, "volume"):
            c.lattice(source["grid"]["centres"], bad, source["mesh"], [2, 2, 2])

    def test_duplicate_cell_centres_are_rejected(self):
        source = c.load_case(self.a, "M1")
        bad = list(source["grid"]["centres"])
        bad[0] = bad[1]
        with self.assertRaisesRegex(c.native.ComparisonFailure, "duplicate"):
            c.lattice(bad, source["grid"]["volumes"], source["mesh"], [2, 2, 2])

    def test_child_volumes_and_centroids_must_match_parent(self):
        coarse, fine = c.load_case(self.a, "M1"), c.load_case(self.b, "M3")
        fine["grid"]["volumes"][0] *= 1.1
        with self.assertRaisesRegex(c.native.ComparisonFailure, "child volumes"):
            c.build_mapping(coarse["grid"], fine["grid"])
        fine["grid"]["volumes"][0] /= 1.1
        fine["grid"]["centres"][0][0] += 1e-6
        with self.assertRaisesRegex(c.native.ComparisonFailure, "centroid"):
            c.build_mapping(coarse["grid"], fine["grid"])

    def test_boundary_nonfinite_value_fails(self):
        path = self.b / "1e-6/T"
        path.write_text(path.read_text().replace("type zeroGradient;", "type fixedValue; value uniform nan;"))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "non-finite"):
            self.compare()

    def test_oscillating_laser_not_silently_treated_as_linear(self):
        path = self.b / "constant/LaserProperties"
        path.write_text(path.read_text().replace("laserRadius 55e-6;", "laserRadius 55e-6; HS_oscAmpX 1e-6;"))
        fixtures.record_inputs(self.b)
        with self.assertRaisesRegex(c.native.ReviewRequired, "oscillating"):
            self.compare()

    def test_requested_time_must_exist(self):
        with self.assertRaisesRegex(c.native.ComparisonFailure, "requested times"):
            self.compare(["1.5e-6"])

    def test_nonzero_solver_exit_and_abnormal_end_fail(self):
        (self.b / "solver.exit.txt").write_text("1\n")
        with self.assertRaisesRegex(c.native.ComparisonFailure, "solver exit"):
            self.compare()
        (self.b / "solver.exit.txt").write_text("0\n")
        path = self.b / "log.laserbeamFoam"
        path.write_text(path.read_text().removesuffix("End\n"))
        with self.assertRaisesRegex(c.native.ComparisonFailure, "normal End"):
            self.compare()

    def test_unsupported_selected_field_is_not_byte_fallback(self):
        path = self.b / "1e-6/T"
        path.write_text(path.read_text().replace("class volScalarField", "class futureField"))
        code, out = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads((out / "comparison.json").read_text())["status"], "REVIEW_REQUIRED")

    def test_binary_native_field_requires_review(self):
        path = self.b / "1e-6/T"
        path.write_text(path.read_text().replace("format ascii", "format binary"))
        with self.assertRaisesRegex(c.native.ReviewRequired, "format ascii"):
            self.compare()

    def test_source_only_schema_is_not_numerical_equivalence(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        report = json.loads((out / "comparison.json").read_text())
        self.assertEqual(report["status"], "COMPARISON_COMPLETED")
        self.assertEqual(report["interpretation"]["physical_accuracy"], "UNVERIFIED")
        self.assertEqual(report["interpretation"]["grid_convergence"], "NOT_ESTABLISHED")
        self.assertTrue(report["interpretation"]["initial_interface_discretization_differs"])

    def test_feedback_size_limit_is_not_silent_truncation(self):
        out = self.root / "oversized"
        out.mkdir()
        report = {"status": "REVIEW_REQUIRED", "issues": [], "extra": "x" * (4 * 1024 * 1024)}
        with self.assertRaisesRegex(ValueError, "small-feedback limit"):
            c.publish(out, report)
        self.assertFalse((out / "m1-m3-comparison-feedback.tar.gz").exists())

    def test_complete_small_archive_and_no_source_writes(self):
        before = {p: c.digest(p) for case in (self.a, self.b) for p in case.rglob("*") if p.is_file()}
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(before, {p: c.digest(p) for case in (self.a, self.b) for p in case.rglob("*") if p.is_file()})
        archive = out / "m1-m3-comparison-feedback.tar.gz"
        checksum = (out / (archive.name + ".sha256")).read_text().split()[0]
        self.assertEqual(checksum, c.digest(archive))
        with tarfile.open(archive, "r:gz") as tar:
            data = {member.name: tar.extractfile(member).read() for member in tar.getmembers()}
            self.assertEqual(set(data), set(data["FILES.txt"].decode().splitlines()))
            for line in data["SHA256SUMS"].decode().splitlines():
                expected, name = line.split("  ", 1)
                self.assertEqual(expected, hashlib.sha256(data[name]).hexdigest())
            self.assertNotIn(str(self.root).encode(), data["comparison.json"])

    def test_existing_report_directory_is_never_overwritten(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        code, _ = self.run_cli(out)
        self.assertEqual(code, 2)

    def test_output_cannot_be_inside_source_case(self):
        with patch.object(c, "REPO", self.root):
            code, _ = self.run_cli(self.a / "comparison")
        self.assertEqual(code, 2)

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlinks unavailable")
    def test_symlink_input_is_rejected(self):
        path = self.b / "1e-6/T"
        target = self.root / "outside"
        target.write_text(path.read_text())
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest("host does not permit symlink creation")
        with self.assertRaisesRegex(c.native.ComparisonFailure, "symlink"):
            self.compare()


class MappingMath(unittest.TestCase):
    def test_restrict_product_not_product_of_restrictions(self):
        groups = [list(range(8))]
        alpha = [0, 0, 0, 0, 1, 1, 1, 1]
        epsilon = [1, 1, 1, 1, 0, 0, 0, 0]
        product = c.restrict([a * e for a, e in zip(alpha, epsilon)], groups, [1] * 8, [8])
        self.assertEqual(product, [0])
        self.assertEqual(c.restrict(alpha, groups, [1] * 8, [8])[0] * c.restrict(epsilon, groups, [1] * 8, [8])[0], 0.25)

    def test_volume_weighted_norms_and_empty_metal_mask(self):
        result = c.norms([1, 1], [2, 3], [1, 3])
        self.assertEqual(result["L1"], 1.75)
        self.assertAlmostEqual(result["L2"], math.sqrt(13 / 4))
        self.assertEqual(result["Linf"], 2)
        self.assertIsNone(c.norms([1], [2], [1], selected=[])["L1"])
        self.assertIsNone(c.norms([0], [2], [1])["relative_L1"])

    def test_wrong_refinement_or_shifted_bounds_rejected(self):
        coarse = {"shape": [2, 2, 2], "tolerance": 1e-16, "bounds": [[0, 1]] * 3}
        fine = {"shape": [4, 4, 5], "tolerance": 1e-16, "bounds": [[0, 1]] * 3}
        with self.assertRaises(c.native.ReviewRequired):
            c.build_mapping(coarse, fine)
        fine.update(shape=[4, 4, 4], bounds=[[0, 2], [0, 1], [0, 1]])
        with self.assertRaises(c.native.ComparisonFailure):
            c.build_mapping(coarse, fine)


if __name__ == "__main__":
    unittest.main()
