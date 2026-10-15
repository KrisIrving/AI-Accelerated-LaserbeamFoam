"""Synthetic parser/comparator checks; these fixtures are not CFD runs."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "compare_plate2d_ab", Path(__file__).resolve().parents[1] / "scripts" / "compare_plate2d_ab.py")
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)


def header(field_class, obj="field", fmt="ascii"):
    return "FoamFile\n{ format %s; class %s; object %s; }\n" % (fmt, field_class, obj)


def field(field_class="volScalarField", value="uniform 0", boundary=None, fmt="ascii"):
    if boundary is None:
        boundary = "wall { type zeroGradient; }"
    return (header(field_class, fmt=fmt) + "dimensions [0 0 0 0 0 0 0];\n"
            "internalField " + value + ";\nboundaryField { " + boundary + " }\n")


def write_manifest(case, name, paths):
    text = "".join(hashlib.sha256((case / p).read_bytes()).hexdigest() + "  " + p + "\n" for p in sorted(paths))
    (case / name).write_text(text, encoding="ascii")


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name, app in (("A", "laserbeamFoam"), ("B", "aiLaserbeamFoam")):
            case = self.root / name
            for directory in ("initial", "constant/polyMesh", "system", "1e-7"):
                (case / directory).mkdir(parents=True, exist_ok=True)
            (case / "initial/T").write_text("synthetic seed\n")
            (case / "constant/properties").write_text("synthetic constant\n")
            (case / "system/controlDict").write_text("application " + app + ";\nendTime 1e-7;\n")
            (case / "constant/polyMesh/owner").write_text(header("labelList") + "3(0 0 1)\n")
            (case / "constant/polyMesh/neighbour").write_text(header("labelList") + "1(1)\n")
            (case / "constant/polyMesh/boundary").write_text(header("polyBoundaryMesh") + "1(wall {type wall; nFaces 2; startFace 1;})\n")
            write_manifest(case, "inputs.sha256", ["initial/T", "constant/properties", "system/controlDict"])
            write_manifest(case, "mesh.sha256", ["constant/polyMesh/" + p for p in ("owner", "neighbour", "boundary")])
            for required in COMPARE.REQUIRED_FIELDS:
                if required in ("U", "H", "B", "J", "JcrossB"):
                    text = field("volVectorField", "uniform (0 0 0)")
                elif required == "phi":
                    text = field("surfaceScalarField", "uniform 0")
                else:
                    text = field(value="uniform 0.5" if required == "alpha.metal" else "uniform 0")
                (case / "1e-7" / required).write_text(text)
            lines = []
            for step in range(1, 11):
                lines.extend([
                    "Time = {:.12g}".format(step * 1e-8),
                    "Courant Number mean: 0 max: 0",
                    "Phase-1 volume fraction = 0.5 Min(alpha.metal) = 0 Max(alpha.metal) = 1",
                    "Total Q deposited: 10",
                    "smoothSolver: Solving for T, Initial residual = 1e-5, Final residual = 1e-10, No Iterations 2",
                    "Correcting epsilon1, mean residual = 1e-5, max residual = 1e-4",
                    "time step continuity errors : sum local = 1e-12, global = 0, cumulative = 0",
                    "ExecutionTime = 1 s ClockTime = 1 s",
                ])
            (case / ("log." + app)).write_text("\n".join(lines) + "\nEnd\n")
            (case / "solver.exit.txt").write_text("0\n")
            (case / "solver.time.txt").write_text("1.0\n")

    def tearDown(self):
        self.temp.cleanup()

    def compare(self):
        return COMPARE.compare_runs(self.root)

    def test_synthetic_equal(self):
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["geometry"]["cells"], 2)
        self.assertTrue(report["logs"]["exact_equal"])
        self.assertTrue(report["fields"]["1e-07"]["T"]["internal"]["exact_equal"])
        self.assertEqual(report["fields"]["1e-07"]["alpha.metal"]["alpha_bounds"]["A"], [0.5, 0.5])

    def test_small_difference(self):
        (self.root / "B/1e-7/T").write_text(field(value="nonuniform List<scalar> 2(1e-13 0)"))
        report = self.compare()
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["fields"]["1e-07"]["T"]["internal"]["exact_equal"])

    def test_exceeds_tolerance(self):
        (self.root / "B/1e-7/T").write_text(field(value="uniform 1e-3"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_missing_field(self):
        (self.root / "B/1e-7/T").unlink()
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_both_missing_required_field(self):
        for name in ("A", "B"):
            (self.root / name / "1e-7/T").unlink()
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_extra_field_not_silently_intersected(self):
        (self.root / "A/1e-7/extra").write_text(field())
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_nonfinite(self):
        (self.root / "B/1e-7/T").write_text(field(value="uniform nan"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_wrong_nonuniform_count(self):
        (self.root / "B/1e-7/T").write_text(field(value="nonuniform List<scalar> 1(0)"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_wrong_vector_shape(self):
        (self.root / "B/1e-7/U").write_text(field("volVectorField", "uniform (0 0)"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_binary_rejected(self):
        (self.root / "B/1e-7/T").write_text(field(fmt="binary"))
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_substitution_rejected(self):
        (self.root / "B/1e-7/T").write_text(field(value="$otherField"))
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_boundary_uniform_expansion(self):
        (self.root / "A/1e-7/T").write_text(field(boundary="wall {type fixedValue; value uniform 2;}"))
        (self.root / "B/1e-7/T").write_text(field(boundary="wall {type fixedValue; value nonuniform List<scalar> 2(2 2);}"))
        self.assertEqual(self.compare()["status"], "PASS")

    def test_boundary_difference(self):
        (self.root / "A/1e-7/T").write_text(field(boundary="wall {type fixedValue; value uniform 2;}"))
        (self.root / "B/1e-7/T").write_text(field(boundary="wall {type fixedValue; value uniform 3;}"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_changed_input_is_not_accepted_by_old_manifest(self):
        (self.root / "B/constant/properties").write_text("changed")
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_added_input_is_rejected(self):
        (self.root / "B/initial/extra").write_text("extra input")
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_added_nested_polymesh_input_is_not_hidden(self):
        directory = self.root / "B/initial/polyMesh"
        directory.mkdir()
        (directory / "extra").write_text("not a generated constant mesh")
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_compressed_field_rejected(self):
        for case in ("A", "B"):
            (self.root / case / "1e-7/extra.gz").write_bytes(b"not native ASCII")
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_surface_nonuniform_count_uses_internal_faces(self):
        for case in ("A", "B"):
            (self.root / case / "1e-7/phi").write_text(field("surfaceScalarField", "nonuniform List<scalar> 1(0)"))
        self.assertEqual(self.compare()["status"], "PASS")

    def test_dimension_change_is_rejected(self):
        path = self.root / "B/1e-7/T"
        path.write_text(path.read_text().replace("[0 0 0 0 0 0 0]", "[0 0 0 1 0 0 0]"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_log_nonfinite_is_rejected(self):
        path = self.root / "B/log.aiLaserbeamFoam"
        path.write_text(path.read_text().replace("Final residual = 1e-10", "Final residual = nan", 1))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_unknown_field_class_requires_review(self):
        for case in ("A", "B"):
            (self.root / case / "1e-7/extra").write_text(field("unsupportedField"))
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_different_matching_meshes_require_review(self):
        case = self.root / "B"
        path = case / "constant/polyMesh/owner"
        path.write_text(header("labelList") + "3(1 0 1)\n")
        write_manifest(case, "mesh.sha256", ["constant/polyMesh/" + p for p in ("owner", "neighbour", "boundary")])
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_uniform_time_dictionary_is_compared(self):
        for case in ("A", "B"):
            directory = self.root / case / "1e-7/uniform"
            directory.mkdir()
            (directory / "time").write_text(header("dictionary") + "value 1e-7; index 10; deltaT 1e-8;\n")
        report = self.compare()
        self.assertEqual(report["status"], "PASS")
        self.assertIn("time", report["uniform"]["1e-07"]["files"])
        path = self.root / "B/1e-7/uniform/time"
        path.write_text(path.read_text().replace("index 10", "index 9"))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_uniform_extra_file_is_not_silently_ignored(self):
        directory = self.root / "A/1e-7/uniform"
        directory.mkdir()
        (directory / "time").write_text(header("dictionary") + "value 1e-7;\n")
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_uniform_unsupported_list_requires_review(self):
        for case in ("A", "B"):
            directory = self.root / case / "1e-7/uniform"
            directory.mkdir()
            (directory / "other").write_text(header("labelList") + "1(0)\n")
        self.assertEqual(self.compare()["status"], "REVIEW_REQUIRED")

    def test_control_dictionary_only_normalizes_application(self):
        case = self.root / "B"
        (case / "system/controlDict").write_text("application aiLaserbeamFoam;\nendTime 2e-7;\n")
        write_manifest(case, "inputs.sha256", ["initial/T", "constant/properties", "system/controlDict"])
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_missing_log_event(self):
        log = self.root / "B/log.aiLaserbeamFoam"
        log.write_text(log.read_text().replace("Correcting epsilon1, mean residual = 1e-5, max residual = 1e-4\n", "", 1))
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_output_reports(self):
        self.assertEqual(COMPARE.main(["--run-dir", str(self.root)]), 0)
        self.assertTrue((self.root / "comparison.json").is_file())
        self.assertTrue((self.root / "comparison.txt").is_file())


if __name__ == "__main__":
    unittest.main()
