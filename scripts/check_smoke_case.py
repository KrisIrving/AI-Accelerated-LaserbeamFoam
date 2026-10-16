#!/usr/bin/env python3
"""Offline sanity checks only: no physical accuracy or reference equivalence claim."""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import compare_plate2d_ab as native


def check_inputs(case):
    """Validate the complete initialized inventory, including extra-file checks."""
    expected = {}
    for name in ("inputs.sha256", "initialized.sha256"):
        for line in (case / name).read_text().splitlines():
            digest, relative = line.split("  ", 1)
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or path.parts[0] not in ("initial", "constant", "system", "0"):
                raise ValueError("unsafe input manifest path")
            if relative in expected and expected[relative] != digest:
                raise ValueError("conflicting input hash: " + relative)
            expected[relative] = digest
    actual = {}
    for root in ("initial", "constant", "system", "0"):
        base = case / root
        if base.is_symlink() or not base.is_dir():
            raise ValueError("missing/symlinked input root: " + root)
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError("symlinked input: " + path.relative_to(case).as_posix())
            if path.is_file():
                actual[path.relative_to(case).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif not path.is_dir():
                raise ValueError("non-regular input")
    if actual != expected:
        changed = sorted(p for p in set(actual) | set(expected) if actual.get(p) != expected.get(p))
        raise ValueError("initialized input path/hash mismatch: " + ", ".join(changed[:5]))


def check(case):
    case = Path(case)
    manifest = json.loads((case / "manifest.json").read_text())
    config = manifest["config"]
    report = {"status": "REVIEW_REQUIRED", "accuracy": "UNVERIFIED",
              "reference": "NOT_ESTABLISHED", "fields": {}, "issues": []}
    try:
        log = native.parse_log(case, manifest["solver"])
        expected = math.prod(config["cells"])
        geometry = native.mesh_geometry(case)
        if geometry["cells"] != expected:
            raise native.ComparisonFailure("unexpected mesh cell count")
        if len(log["times"]) != config["steps"] or not math.isclose(
                log["times"][-1], float(config["end_time"]), rel_tol=1e-12, abs_tol=0):
            raise native.ComparisonFailure("wrong simulation steps/final time")
        times = list(native.result_times(case).values())
        if len(times) != 1 or float(times[0].name) != float(config["end_time"]):
            raise native.ComparisonFailure("missing or unexpected output times")
        directory = times[0]
        required = {"T", "U", "p_rgh", "alpha.metal", "epsilon1", "Deposition", "phi"}
        files = {p.name for p in directory.iterdir() if p.name != "uniform"}
        if not required <= files:
            raise native.ComparisonFailure("missing fields: " + ", ".join(sorted(required - files)))
        for name in sorted(files):
            path = directory / name
            if path.is_symlink() or not path.is_file():
                raise native.ReviewRequired("non-file output: " + name)
            # Self-comparison exercises the established parser, sizes, finite
            # values and explicit boundary data; it is not reference validation.
            result = native.compare_fields(path, path, geometry, 1e-12, 1e-10)
            if name == "alpha.metal":
                bounds = result["alpha_bounds"]["A"]
                if bounds[0] < -1e-12 or bounds[1] > 1 + 1e-12:
                    raise native.ComparisonFailure("alpha.metal outside [0,1] tolerance")
                report["alpha_bounds"] = bounds
            if name in ("T", "Deposition"):
                parsed = native.parse_field(path)
                values = native.expand_field(parsed["internal"], geometry["cells"], 1, "scalar")
                report[name + "_range"] = [min(values), max(values)]
                if name == "T" and min(values) <= 0:
                    raise native.ComparisonFailure("non-positive absolute temperature")
            report["fields"][name] = {"status": "PARSED_FINITE_SIZE_CHECKED", "class": result["class"]}
        report["uniform"] = native.compare_uniform_directory(
            directory / "uniform", directory / "uniform", 1e-12, 1e-10, geometry)
        if report["uniform"]["status"] == "FAIL":
            raise native.ComparisonFailure("uniform: " + str(report["uniform"]["issues"]))
        if report["uniform"]["status"] != "PASS":
            raise native.ReviewRequired("uniform: " + str(report["uniform"]["issues"]))
        if not any(event["kind"] == "deposition" for event in log["events"]):
            raise native.ReviewRequired("no recognized laser deposition diagnostics")
        if report["Deposition_range"][1] <= 0:
            raise native.ReviewRequired("no positive laser deposition; target heat path not established")
        report["execution_time_samples"] = re.findall(
            r"ExecutionTime\s*=\s*([0-9.eE+-]+)\s+s\s+ClockTime\s*=\s*([0-9.eE+-]+)\s+s",
            (case / ("log." + manifest["solver"])).read_text())
        report.update(status="SMOKE_CHECKS_PASSED", cells=geometry["cells"],
                      steps=len(log["times"]), final_time=log["times"][-1],
                      diagnostic_events=len(log["events"]))
    except native.ComparisonFailure as exc:
        report.update(status="FAIL", issues=[str(exc)])
    except (native.ReviewRequired, OSError, ValueError, KeyError) as exc:
        report.update(status="REVIEW_REQUIRED", issues=[str(exc)])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--inputs-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.inputs_only:
            check_inputs(args.case_dir)
            print("PASS [initialized-inputs] complete path/hash inventory")
            return 0
        report = check(args.case_dir)
        (args.case_dir / "smoke.json").write_text(json.dumps(report, indent=2) + "\n")
        text = "Status: {}\nAccuracy: UNVERIFIED; reference: NOT_ESTABLISHED\nFields checked: {}\n".format(
            report["status"], len(report["fields"]))
        text += "\n".join(report["issues"]) + "\n"
        (args.case_dir / "smoke.txt").write_text(text)
        print(text, end="")
        return {"SMOKE_CHECKS_PASSED": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}[report["status"]]
    except (OSError, ValueError, KeyError) as exc:
        print("ERROR [smoke-check] " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
