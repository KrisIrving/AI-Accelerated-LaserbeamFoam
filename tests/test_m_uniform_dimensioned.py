"""Source-derived v2512 ASCII fixtures, not files from the Ubuntu M1 run.

Official OpenFOAM-v2512 sources:
https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/OpenFOAM/fields/UniformDimensionedFields/UniformDimensionedField.C
https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/finiteVolume/cfdTools/general/include/initContinuityErrs.H
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_m_case as m

SPEC = importlib.util.spec_from_file_location("uniform_m_fixtures", ROOT / "tests/test_m_checks.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


def scalar_state(value="-1.25e-12", dimensions="[0 0 0 0 0 0 0]",
                 object_name="cumulativeContErr", field_class="uniformDimensionedScalarField"):
    return ("FoamFile\n{\nversion 2.0;\nformat ascii;\nclass " + field_class +
            ";\nlocation \"1e-05/uniform\";\nobject " + object_name + ";\n}\n" +
            "dimensions " + dimensions + ";\nvalue " + value + ";\n")


class UniformScalarParser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "cumulativeContErr"

    def parse(self, content):
        self.path.write_text(content, encoding="ascii")
        return m.parse_uniform_dimensioned_scalar(self.path)

    def test_canonical_scalar_is_semantically_parsed(self):
        result = self.parse(scalar_state())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["class"], "uniformDimensionedScalarField")
        self.assertEqual(result["object"], "cumulativeContErr")
        self.assertEqual(result["dimensions"], [0] * 7)
        self.assertEqual(result["value"], -1.25e-12)
        self.assertTrue(result["finite"])
        self.assertEqual(result["method"], "NUMERICAL_SEMANTIC_UNIFORM_DIMENSIONED_SCALAR")

    def test_wrong_class_fails(self):
        for field_class in ("dictionary", "uniformDimensionedVectorField", "volScalarField"):
            with self.subTest(field_class=field_class), self.assertRaises(m.native.ComparisonFailure):
                self.parse(scalar_state(field_class=field_class))

    def test_wrong_or_missing_object_fails(self):
        for content in (scalar_state(object_name="anotherObject"),
                        scalar_state().replace("object cumulativeContErr;", "")):
            with self.subTest(content=content), self.assertRaises(m.native.ComparisonFailure):
                self.parse(content)

    def test_nonfinite_or_overflow_scalar_fails(self):
        for value in ("nan", "NaN", "+Inf", "-infinity", "1e999"):
            with self.subTest(value=value), self.assertRaises(m.native.ComparisonFailure):
                self.parse(scalar_state(value=value))

    def test_value_requires_exactly_one_scalar(self):
        for value in ("", "uniform 0", "(0)", "(0 1 2)", "0 1"):
            with self.subTest(value=value), self.assertRaises(m.native.ComparisonFailure):
                self.parse(scalar_state(value=value))

    def test_illegal_dimension_shapes_require_review(self):
        for dimensions in ("[0 0 0 0 0 0]", "[0 0 0 0 0 0 0 0]", "[kg]", "()",
                           "(0 0 0 0 0 0 0)", "[0 0 0 0 0 0 word]"):
            with self.subTest(dimensions=dimensions), self.assertRaises(m.native.ReviewRequired):
                self.parse(scalar_state(dimensions=dimensions))

    def test_nonfinite_dimension_exponent_fails(self):
        with self.assertRaises(m.native.ComparisonFailure):
            self.parse(scalar_state(dimensions="[0 0 0 0 0 0 nan]"))

    def test_cumulative_continuity_state_must_be_dimensionless(self):
        with self.assertRaisesRegex(m.native.ComparisonFailure, "dimensionless"):
            self.parse(scalar_state(dimensions="[0 0 -1 0 0 0 0]"))

    def test_other_uniform_scalar_can_have_finite_fractional_dimensions(self):
        self.path = self.path.with_name("otherScalar")
        result = self.parse(scalar_state(object_name="otherScalar", dimensions="[0.5 1 -2 0 0 0 0]"))
        self.assertEqual(result["dimensions"], [0.5, 1, -2, 0, 0, 0, 0])

    def test_missing_required_entries_fail(self):
        for removed in ("dimensions [0 0 0 0 0 0 0];", "value -1.25e-12;"):
            with self.subTest(removed=removed), self.assertRaises(m.native.ComparisonFailure):
                self.parse(scalar_state().replace(removed, ""))

    def test_truncated_entries_and_header_require_review(self):
        for content in (scalar_state().rstrip()[:-1], scalar_state().split("value")[0] + "value",
                        "FoamFile { class uniformDimensionedScalarField;",
                        scalar_state().replace("[0 0 0 0 0 0 0]", "[0 0 0 0 0 0 0")):
            with self.subTest(content=content), self.assertRaises(m.native.ReviewRequired):
                self.parse(content)

    def test_unknown_and_duplicate_entries_require_review(self):
        for extra in ("futureProperty 1;", "value 2;"):
            with self.subTest(extra=extra), self.assertRaises(m.native.ReviewRequired):
                self.parse(scalar_state() + extra)

    def test_unknown_entry_cannot_hide_nonfinite_scalar(self):
        with self.assertRaises(m.native.ComparisonFailure):
            self.parse(scalar_state(value="nan") + "futureProperty 1;")

    def test_binary_or_substitution_is_not_silently_accepted(self):
        for content in (scalar_state().replace("format ascii", "format binary"),
                        scalar_state(value="$otherValue")):
            with self.subTest(content=content), self.assertRaises(m.native.ReviewRequired):
                self.parse(content)


class UniformScalarIntegration(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.MChecks(methodName="test_all_times_native_fields_and_observations")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.case = self.fixture.case
        for directory in ("2e-8", "4e-8"):
            (self.case / directory / "uniform/cumulativeContErr").write_text(scalar_state())

    def test_all_output_times_require_actual_scalar_parsing(self):
        report = m.check(self.case)
        self.assertEqual(report["status"], m.PASSED, report["issues"])
        for directory in ("2e-8", "4e-8"):
            parsed = report["uniform"][directory]["files"]["cumulativeContErr"]
            self.assertEqual(parsed["method"], "NUMERICAL_SEMANTIC_UNIFORM_DIMENSIONED_SCALAR")
            self.assertEqual(parsed["value"], -1.25e-12)
            self.assertNotIn("unsupported uniform class", str(parsed))

    def test_ten_output_times_are_all_parsed(self):
        self.fixture.config.update(steps=20, end_time="2e-7")
        self.fixture.write_manifest()
        self.fixture.write_log()
        for number in range(3, 11):
            shutil.copytree(self.case / "2e-8", self.case / (str(number * 2) + "e-8"))
        report = m.check(self.case)
        self.assertEqual(report["status"], m.PASSED, report["issues"])
        self.assertEqual(len(report["uniform"]), 10)
        for uniform in report["uniform"].values():
            self.assertEqual(uniform["files"]["cumulativeContErr"]["method"],
                             "NUMERICAL_SEMANTIC_UNIFORM_DIMENSIONED_SCALAR")

    def test_nonfinite_scalar_is_fail_with_time_and_path_and_later_fields_checked(self):
        (self.case / "2e-8/uniform/cumulativeContErr").write_text(scalar_state(value="nan"))
        report = m.check(self.case)
        self.assertEqual(report["status"], "FAIL", report["issues"])
        self.assertIn("2e-8/uniform", str(report["issues"]))
        self.assertIn("cumulativeContErr", str(report["issues"]))
        self.assertIn("4e-8", report["fields"])

    def test_cumulative_state_wrong_class_cannot_masquerade_as_dictionary(self):
        (self.case / "2e-8/uniform/cumulativeContErr").write_text(scalar_state(field_class="dictionary"))
        report = m.check(self.case)
        self.assertEqual(report["status"], "FAIL", report["issues"])

    def test_missing_cumulative_state_is_fail_with_path(self):
        (self.case / "2e-8/uniform/cumulativeContErr").unlink()
        report = m.check(self.case)
        self.assertEqual(report["status"], "FAIL", report["issues"])
        self.assertIn("uniform/cumulativeContErr", str(report["issues"]))

    def test_unknown_state_class_still_requires_review(self):
        (self.case / "2e-8/uniform/unknownState").write_text(
            scalar_state(object_name="unknownState", field_class="uniformDimensionedVectorField"))
        report = m.check(self.case)
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report["issues"])

    def test_other_uniform_scalar_is_parsed_without_class_byte_fallback(self):
        (self.case / "2e-8/uniform/otherScalar").write_text(scalar_state(object_name="otherScalar"))
        report = m.check(self.case)
        self.assertEqual(report["status"], m.PASSED, report["issues"])
        self.assertEqual(report["uniform"]["2e-8"]["files"]["otherScalar"]["value"], -1.25e-12)

    def test_existing_mixed_count_retained_with_strict_interval_observation(self):
        alpha = [0, 1e-16, 0.01, 0.010001, 0.5, 0.989999, 0.99, 1 - 1e-16, 1]
        count = len(alpha)
        fields = {"Deposition": {"dimensions": m.DEPOSITION_DIMENSIONS},
            "T": {"dimensions": [0, 0, 0, 1, 0, 0, 0]}, "U": {"dimensions": [0, 1, -1, 0, 0, 0, 0]},
            "alpha.metal": {"dimensions": [0] * 7}, "epsilon1": {"dimensions": [0] * 7}}
        values = {"alpha.metal": alpha, "epsilon1": [0] * count, "T": [300] * count,
            "U": [0] * (3 * count), "Deposition": [1] * count}
        row = m.observations(self.case / "2e-8", fields, values, [1] * count,
            [[i, 0, 0] for i in range(count)], sum(alpha), 2e-8, alpha)
        self.assertEqual(row["mixed_cells_count"], 7)
        self.assertEqual(row["mixed_cells_strict_001_099_count"], 3)
        self.assertEqual(row["significant_interface_motion"], "NOT_ESTABLISHED")
        self.assertIn("not acceptance thresholds", row["mixed_cells_note"])


if __name__ == "__main__":
    unittest.main()
