"""Synthetic OpenFOAM surface orientation checks; these are not CFD runs."""
import unittest

import test_compare_plate2d_ab as fixtures


COMPARE = fixtures.COMPARE


class SurfaceOrientationTests(unittest.TestCase):
    def setUp(self):
        # Composition reuses the valid A/B fixture without re-running its tests.
        self.fixture = fixtures.ComparatorTests(methodName="runTest")
        self.fixture.setUp()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.tearDown()

    def compare(self):
        return COMPARE.compare_runs(self.root)

    def write_surface(self, entry="oriented oriented;", variant=None,
                      name="phi", value="uniform 0", boundary=None,
                      dimensions=None):
        text = fixtures.field("surfaceScalarField", value, boundary) + entry + "\n"
        if dimensions is not None:
            text = text.replace("[0 0 0 0 0 0 0]", dimensions)
        for case in ((variant,) if variant else ("A", "B")):
            (self.root / case / "1e-7" / name).write_text(text, encoding="ascii")

    def field_result(self, report, name="phi"):
        return report["fields"]["1e-07"][name]

    def assert_problem(self, report, status, text, name="phi"):
        self.assertEqual(report["status"], status, report["issues"])
        self.assertEqual(self.field_result(report, name)["status"], status)
        self.assertTrue(any(issue.get("path") == "1e-07/" + name and text in issue["message"]
                            for issue in report["issues"]), report["issues"])
        self.assertFalse(report["fields_complete"])

    def test_all_legal_explicit_enum_values_are_semantically_compared(self):
        for value in ("unknown", "oriented", "unoriented"):
            with self.subTest(value=value):
                self.write_surface("oriented " + value + ";")
                report = self.compare()
                self.assertEqual(report["status"], "PASS", report["issues"])
                result = self.field_result(report)
                self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
                self.assertIn("internal", result)
                self.assertIn("wall", result["patches"])
                self.assertEqual(result["orientation"], {
                    "A": {"present": True, "value": value},
                    "B": {"present": True, "value": value}})

    def test_distinct_explicit_orientation_values_fail(self):
        self.write_surface("oriented oriented;", variant="A")
        self.write_surface("oriented unoriented;", variant="B")
        self.assert_problem(self.compare(), "FAIL", "oriented differs")

    def test_invalid_orientation_enum_or_token_shape_fails(self):
        for entry in ("oriented invalid;", "oriented true;", "oriented 1;",
                      'oriented "oriented";', "oriented;", "oriented ();",
                      "oriented (oriented);", "oriented oriented unoriented;",
                      "oriented { value oriented; }"):
            with self.subTest(entry=entry):
                self.write_surface(entry)
                self.assert_problem(self.compare(), "FAIL", "invalid oriented entry")

    def test_unknown_top_level_names_are_listed_for_review(self):
        self.write_surface("oriented oriented; unsupportedFlag 1; otherState 2;")
        report = self.compare()
        self.assert_problem(report, "REVIEW_REQUIRED", "unsupported extra top-level field entries")
        problem = self.field_result(report)["reason"]
        self.assertIn("unsupportedFlag", problem)
        self.assertIn("otherState", problem)

    def test_both_absent_orientation_records_no_inferred_value(self):
        self.write_surface("")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(self.field_result(report)["orientation"], {
            "A": {"present": False, "value": None},
            "B": {"present": False, "value": None}})

    def test_absent_versus_explicit_is_review_including_unknown(self):
        for missing_variant in ("A", "B"):
            for explicit in ("unknown", "oriented", "unoriented"):
                with self.subTest(missing_variant=missing_variant, explicit=explicit):
                    self.write_surface("oriented " + explicit + ";")
                    self.write_surface("", variant=missing_variant)
                    self.assert_problem(self.compare(), "REVIEW_REQUIRED", "oriented presence differs")

    def test_matching_orientation_does_not_hide_internal_difference(self):
        self.write_surface()
        self.write_surface(variant="B", value="uniform 1e-3")
        report = self.compare()
        self.assert_problem(report, "FAIL", "field exceeds tolerance")
        self.assertEqual(self.field_result(report)["internal"]["max_abs"], 1e-3)

    def test_matching_orientation_does_not_hide_boundary_difference(self):
        self.write_surface(boundary="wall { type fixedValue; value uniform 0; }")
        self.write_surface(variant="B", boundary="wall { type fixedValue; value uniform 1e-3; }")
        report = self.compare()
        self.assert_problem(report, "FAIL", "field exceeds tolerance")
        self.assertEqual(self.field_result(report)["patches"]["wall"]["values"]["value"]["max_abs"], 1e-3)

    def test_matching_orientation_does_not_hide_dimensions_difference(self):
        self.write_surface()
        self.write_surface(variant="B", dimensions="[0 1 0 0 0 0 0]")
        self.assert_problem(self.compare(), "FAIL", "field dimensions differs")

    def test_internal_surface_uses_internal_face_count_not_cells(self):
        # The fixture has 2 cells, 1 internal face and 2 boundary faces.
        self.write_surface(value="nonuniform List<scalar> 1(0)")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(self.field_result(report)["internal"]["count"], 1)
        self.write_surface(value="nonuniform List<scalar> 2(0 0)")
        self.assert_problem(self.compare(), "FAIL", "nonuniform field entity count mismatch")

    def test_boundary_surface_uses_boundary_face_count(self):
        self.write_surface(boundary="wall { type fixedValue; value nonuniform List<scalar> 2(0 0); }")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(self.field_result(report)["patches"]["wall"]["values"]["value"]["count"], 2)
        self.write_surface(boundary="wall { type fixedValue; value nonuniform List<scalar> 1(0); }")
        self.assert_problem(self.compare(), "FAIL", "nonuniform field entity count mismatch")

    def test_nonfinite_surface_internal_or_boundary_never_passes(self):
        for value, boundary in (("uniform nan", None),
                                ("uniform inf", None),
                                ("uniform 0", "wall { type fixedValue; value uniform nan; }")):
            with self.subTest(value=value, boundary=boundary):
                self.write_surface(value=value, boundary=boundary)
                self.assert_problem(self.compare(), "FAIL", "non-finite numeric value")

    def test_volume_scalar_and_vector_remain_semantically_checked(self):
        self.write_surface()
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        for name, field_class, count in (("T", "volScalarField", 2),
                                         ("U", "volVectorField", 6)):
            result = self.field_result(report, name)
            self.assertEqual(result["class"], field_class)
            self.assertEqual(result["internal"]["count"], count)
            self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
            self.assertIn("wall", result["patches"])

    def test_orientation_is_not_silently_allowed_for_other_field_classes(self):
        for name, field_class, value in (("T", "volScalarField", "uniform 0"),
                                         ("U", "volVectorField", "uniform (0 0 0)"),
                                         ("surfaceVector", "surfaceVectorField", "uniform (0 0 0)")):
            with self.subTest(field_class=field_class):
                originals = {}
                for case in ("A", "B"):
                    path = self.root / case / "1e-7" / name
                    originals[case] = path.read_text() if path.exists() else None
                    path.write_text(fixtures.field(field_class, value) + "oriented oriented;\n")
                self.assert_problem(self.compare(), "REVIEW_REQUIRED", "oriented", name)
                for case in ("A", "B"):
                    path = self.root / case / "1e-7" / name
                    original = originals[case]
                    if original is None:
                        path.unlink()
                    else:
                        path.write_text(original)

    def test_synthetic_thirty_fields_include_three_surface_fields_and_all_compare(self):
        # This proves fixture coverage, not the contents of the user's files.
        for name in ("phi", "phiH", "alphaPhi0.metal"):
            self.write_surface(name=name)
        total = len(list((self.root / "A/1e-7").iterdir()))
        for index in range(30 - total):
            for case in ("A", "B"):
                path = self.root / case / "1e-7" / ("extraScalar%02d" % index)
                path.write_text(fixtures.field(value="uniform 0"))
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertTrue(report["fields_complete"])
        self.assertEqual(report["summary"]["physical_field_files"], 30)
        self.assertEqual(report["summary"]["physical_field_files_compared"], 30)
        self.assertEqual(report["summary"]["physical_fields_status"], "PASS")
        for result in report["fields"]["1e-07"].values():
            self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
            self.assertTrue(result["internal"]["exact_equal"])
            self.assertIn("wall", result["patches"])


if __name__ == "__main__":
    unittest.main()
