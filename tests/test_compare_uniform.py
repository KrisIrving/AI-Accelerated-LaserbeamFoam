"""Recursive uniform-output regression fixtures; no OpenFOAM run is needed."""
import contextlib
import io
import json
import shutil
import unittest

import test_compare_plate2d_ab as fixtures


COMPARE = fixtures.COMPARE


class RecursiveUniformTests(unittest.TestCase):
    def setUp(self):
        # Reuse the original valid A/B fixture without inheriting its tests.
        self.fixture = fixtures.ComparatorTests(methodName="runTest")
        self.fixture.setUp()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.tearDown()

    def compare(self):
        return COMPARE.compare_runs(self.root)

    def write_uniform(self, relative, content, variant=None, time="1e-7"):
        for name in ((variant,) if variant else ("A", "B")):
            path = self.root / name / time / "uniform" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="ascii")

    def dictionary(self, contents="value 1; index 10;"):
        return fixtures.header("dictionary") + contents + "\n"

    def uniform_result(self, report, time="1e-07"):
        return report["uniform"][time]

    def assert_issue_path(self, report, relative):
        descriptions = [item.get("path", "") + " " + item["message"]
                        for item in report["issues"]]
        self.assertTrue(any(relative in text for text in descriptions),
                        (relative, descriptions))

    def assert_all_fields_compared(self, report, time="1e-07"):
        self.assertEqual(set(report["fields"][time]), COMPARE.REQUIRED_FIELDS)
        for result in report["fields"][time].values():
            self.assertIn("internal", result)
            self.assertIn("patches", result)

    def test_nested_uniform_does_not_truncate_263_log_events(self):
        self.write_uniform("functionObjects/state", self.dictionary())
        # The baseline fixture has 70 recognized events. Make 263 while
        # retaining its ten time events and every required diagnostic kind.
        for case, app in (("A", "laserbeamFoam"), ("B", "aiLaserbeamFoam")):
            path = self.root / case / ("log." + app)
            extra = "Courant Number mean: 0 max: 0\n" * 193
            path.write_text(path.read_text().replace("End\n", extra + "End\n"), encoding="ascii")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["logs"]["compared_events"], 263)
        self.assertTrue(report["logs"]["exact_equal"])
        self.assert_all_fields_compared(report)

    def test_plain_dictionary_remains_semantically_compared(self):
        self.write_uniform("time", self.dictionary())
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        result = self.uniform_result(report)["files"]["time"]
        self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
        self.assertTrue(result["byte_identical"])
        self.assert_all_fields_compared(report)

    def test_empty_nested_directories_are_valid(self):
        for case in ("A", "B"):
            (self.root / case / "1e-7/uniform/functionObjects/cache").mkdir(parents=True)
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(self.uniform_result(report)["directories"],
                         ["functionObjects", "functionObjects/cache"])
        self.assertEqual(self.uniform_result(report)["files"], {})
        self.assert_all_fields_compared(report)

    def test_multilevel_dictionary_is_compared(self):
        relative = "functionObjects/sampler/state"
        self.write_uniform(relative, self.dictionary("sample { value (1 2 3); } count 10;"))
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        result = self.uniform_result(report)["files"][relative]
        self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
        self.assertTrue(result["byte_identical"])
        self.assert_all_fields_compared(report)

    def test_opaque_identical_nested_file_has_explicit_byte_method(self):
        relative = "functionObjects/cache/opaque"
        self.write_uniform(relative, b"\x00\xff\x01unsupported state\n")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        result = self.uniform_result(report)["files"][relative]
        self.assertEqual(result["method"], "BYTE_IDENTICAL")
        self.assertTrue(result["byte_identical"])
        self.assert_all_fields_compared(report)

    def test_unsupported_identical_openfoam_list_has_byte_method(self):
        relative = "functionObjects/listState"
        self.write_uniform(relative, fixtures.header("labelList") + "1(0)\n")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(self.uniform_result(report)["files"][relative]["method"], "BYTE_IDENTICAL")

    def test_nested_dictionary_different_bytes_semantically_equal(self):
        relative = "functionObjects/state"
        self.write_uniform(relative, self.dictionary("value 1; index 10;"), "A")
        self.write_uniform(relative, self.dictionary("index 10; /* formatting */ value 1.000;"), "B")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        result = self.uniform_result(report)["files"][relative]
        self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
        self.assertFalse(result["byte_identical"])

    def test_nested_dictionary_difference_within_tolerance(self):
        relative = "functionObjects/state"
        self.write_uniform(relative, self.dictionary("value 1;"), "A")
        self.write_uniform(relative, self.dictionary("value 1.00000000001;"), "B")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertFalse(self.uniform_result(report)["files"][relative]["byte_identical"])

    def test_unsupported_different_nested_bytes_require_review_and_fields_continue(self):
        relative = "functionObjects/opaque"
        self.write_uniform(relative, b"\x00\xffstate A", "A")
        self.write_uniform(relative, b"\x00\xffstate B", "B")
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report)
        self.assert_issue_path(report, relative)
        self.assert_all_fields_compared(report)
        self.assertEqual(report["summary"]["physical_fields_status"], "PASS")
        self.assertEqual(report["summary"]["physical_field_files_compared"], 13)
        self.assertEqual(report["summary"]["uniform_status"], "REVIEW_REQUIRED")

    def test_mixed_validation_methods_have_honest_summary_counts(self):
        self.write_uniform("functionObjects/state", self.dictionary())
        self.write_uniform("functionObjects/opaque", b"\x00\xffsame state")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        summary = report["summary"]
        self.assertEqual(summary["physical_fields_status"], "PASS")
        self.assertEqual(summary["uniform_status"], "PASS")
        self.assertEqual(summary["physical_field_files"], 13)
        self.assertEqual(summary["physical_field_files_compared"], 13)
        self.assertEqual(summary["semantic_pass_files"], 14)
        self.assertEqual(summary["byte_only_files"], 1)
        self.assertEqual(summary["byte_identical_files"], 15)
        self.assertEqual(summary["uniform_files"], 2)
        self.assertEqual(summary["uniform_directories"], 1)
        self.assertIsNone(summary["first_issue"])

    def test_cli_review_report_keeps_counts_and_first_issue_path(self):
        relative = "functionObjects/opaque"
        self.write_uniform(relative, b"\x00\xffstate A", "A")
        self.write_uniform(relative, b"\x00\xffstate B", "B")
        with contextlib.redirect_stdout(io.StringIO()):
            status = COMPARE.main(["--run-dir", str(self.root)])
        self.assertEqual(status, 2)
        text = (self.root / "comparison.txt").read_text(encoding="utf-8")
        report = json.loads((self.root / "comparison.json").read_text(encoding="utf-8"))
        self.assertIn("Status: REVIEW_REQUIRED", text)
        self.assertIn("Simulation steps: 10; compared log events: 70", text)
        self.assertIn("Physical fields: 13 / 13 compared; numerical status: PASS", text)
        self.assertIn("Uniform tree: REVIEW_REQUIRED", text)
        self.assertIn("First issue: REVIEW_REQUIRED: 1e-07/uniform/" + relative, text)
        self.assertEqual(report["summary"]["first_issue"]["path"], "1e-07/uniform/" + relative)

    def test_nested_file_missing_or_extra_fails(self):
        for side in ("A", "B"):
            with self.subTest(side=side):
                self.write_uniform("functionObjects/extra", self.dictionary(), side)
                # Both trees exist: isolate a file-set difference.
                other = "B" if side == "A" else "A"
                (self.root / other / "1e-7/uniform/functionObjects").mkdir(parents=True, exist_ok=True)
                report = self.compare()
                self.assertEqual(report["status"], "FAIL", report)
                self.assert_issue_path(report, "functionObjects/extra")
                for name in ("A", "B"):
                    shutil.rmtree(self.root / name / "1e-7/uniform")

    def test_extra_empty_directory_fails(self):
        self.write_uniform("time", self.dictionary())
        (self.root / "B/1e-7/uniform/functionObjects/extra").mkdir(parents=True)
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, "functionObjects")

    def test_file_directory_type_mismatch_fails(self):
        self.write_uniform("functionObjects/state", self.dictionary(), "A")
        (self.root / "B/1e-7/uniform/functionObjects/state").mkdir(parents=True)
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, "functionObjects/state")

    def test_nested_file_symlink_is_rejected(self):
        self.write_uniform("functionObjects/state", self.dictionary())
        target = self.root / "private-state"
        target.write_text(self.dictionary(), encoding="ascii")
        link = self.root / "B/1e-7/uniform/functionObjects/state"
        link.unlink()
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest("host cannot create symlinks: " + str(exc))
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, "functionObjects/state")

    def test_nested_directory_symlink_is_rejected(self):
        self.write_uniform("functionObjects/state", self.dictionary(), "A")
        target = self.root / "outside"
        target.mkdir()
        (target / "state").write_text(self.dictionary(), encoding="ascii")
        link = self.root / "B/1e-7/uniform/functionObjects"
        link.parent.mkdir()
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            self.skipTest("host cannot create symlinks: " + str(exc))
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, "functionObjects")

    def test_true_nested_numeric_difference_fails_with_path(self):
        relative = "functionObjects/state"
        self.write_uniform(relative, self.dictionary("value 1;"), "A")
        self.write_uniform(relative, self.dictionary("value 2;"), "B")
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, relative)
        self.assert_all_fields_compared(report)

    def test_equal_nonfinite_dictionary_is_failure_not_byte_pass(self):
        relative = "functionObjects/state"
        self.write_uniform(relative, self.dictionary("value nan;"))
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, relative)

    def test_equal_malformed_dictionary_never_gets_byte_fallback(self):
        relative = "functionObjects/state"
        self.write_uniform(relative, self.dictionary("value 1"))
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report["issues"])
        self.assert_issue_path(report, relative)
        self.assertNotEqual(self.uniform_result(report)["files"][relative].get("method"), "BYTE_IDENTICAL")

    def test_numeric_output_time_directory_symlink_is_rejected(self):
        target = self.root / "B/saved-output"
        source = self.root / "B/1e-7"
        source.rename(target)
        try:
            source.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            self.skipTest("host cannot create symlinks: " + str(exc))
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report["issues"])
        self.assertTrue(any("symlink output time directory" in issue["message"]
                            for issue in report["issues"]))
        self.assertNotEqual(report["summary"]["physical_fields_status"], "PASS")

    def test_case_directory_symlink_is_rejected(self):
        for variant in ("A", "B"):
            with self.subTest(variant=variant):
                source = self.root / variant
                target = self.root / (variant + "-saved")
                source.rename(target)
                try:
                    source.symlink_to(target, target_is_directory=True)
                except OSError as exc:
                    self.skipTest("host cannot create symlinks: " + str(exc))
                try:
                    report = self.compare()
                    self.assertEqual(report["status"], "FAIL", report["issues"])
                    self.assertTrue(any("case directory must not be a symlink" in issue["message"]
                                        for issue in report["issues"]))
                    self.assertEqual(report["summary"]["physical_fields_status"], "NOT_CHECKED")
                finally:
                    source.unlink()
                    target.rename(source)

    def test_known_nested_field_uses_field_and_boundary_semantics(self):
        relative = "functionObjects/savedField"
        self.write_uniform(relative, fixtures.field(value="uniform 1"), "A")
        self.write_uniform(relative, fixtures.field(value="uniform 1.00000000001"), "B")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        result = self.uniform_result(report)["files"][relative]
        self.assertEqual(result["method"], "NUMERICAL_SEMANTIC")
        self.assertFalse(result["byte_identical"])

    def test_equal_invalid_known_field_never_gets_byte_fallback(self):
        relative = "functionObjects/savedField"
        self.write_uniform(relative, fixtures.field().replace("boundaryField", "missingBoundaryField"))
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report)
        self.assert_issue_path(report, relative)
        result = self.uniform_result(report)["files"][relative]
        self.assertNotEqual(result.get("method"), "BYTE_IDENTICAL")
        self.assert_all_fields_compared(report)

    def test_equal_binary_known_field_never_gets_byte_fallback(self):
        relative = "functionObjects/savedField"
        self.write_uniform(relative, fixtures.field(fmt="binary"))
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report)
        self.assert_issue_path(report, relative)
        self.assertNotEqual(self.uniform_result(report)["files"][relative].get("method"), "BYTE_IDENTICAL")

    def test_unsupported_top_level_field_still_requires_review(self):
        for case in ("A", "B"):
            (self.root / case / "1e-7/unsupported").write_bytes(b"\xffunsupported identical bytes")
        report = self.compare()
        self.assertEqual(report["status"], "REVIEW_REQUIRED", report)
        self.assert_issue_path(report, "unsupported")

    def test_missing_required_field_is_not_hidden_by_valid_uniform(self):
        self.write_uniform("functionObjects/state", self.dictionary())
        for case in ("A", "B"):
            (self.root / case / "1e-7/JcrossB").unlink()
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assertTrue(any("JcrossB" in item["message"] for item in report["issues"]))

    def test_nested_field_boundary_difference_fails(self):
        relative = "functionObjects/savedField"
        self.write_uniform(relative, fixtures.field(boundary="wall { type fixedValue; value uniform 1; }"), "A")
        self.write_uniform(relative, fixtures.field(boundary="wall { type fixedValue; value uniform 2; }"), "B")
        report = self.compare()
        self.assertEqual(report["status"], "FAIL", report)
        self.assert_issue_path(report, relative)

    def test_all_output_times_and_auto_written_fields_are_compared(self):
        self.write_uniform("functionObjects/state", self.dictionary())
        for case in ("A", "B"):
            source = self.root / case / "1e-7"
            shutil.copytree(source, self.root / case / "5e-8")
            for time in ("1e-7", "5e-8"):
                (self.root / case / time / "extraAutoWrite").write_text(fixtures.field(), encoding="ascii")
        report = self.compare()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(set(report["fields"]), {"5e-08", "1e-07"})
        self.assertEqual(set(report["uniform"]), {"5e-08", "1e-07"})
        for fields in report["fields"].values():
            self.assertEqual(set(fields), COMPARE.REQUIRED_FIELDS | {"extraAutoWrite"})
        bad = self.root / "B/5e-8/extraAutoWrite"
        bad.write_text(fixtures.field(value="uniform 7"), encoding="ascii")
        self.assertEqual(self.compare()["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
