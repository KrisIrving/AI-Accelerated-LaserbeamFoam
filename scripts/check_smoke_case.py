#!/usr/bin/env python3
"""Offline sanity checks only: no physical accuracy or reference equivalence claim."""
import argparse
import hashlib
import json
import math
import re
import sys
import tarfile
from pathlib import Path

import compare_plate2d_ab as native


def gnu_time_record(path):
    """Report missing/non-GNU timing honestly; it never changes numerical gates."""
    record = {"status": "UNVERIFIED", "wall_seconds": None, "max_rss_kib": None}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "Elapsed (wall clock) time" in line:
                parts = line.rsplit(": ", 1)[1].strip().split(":")
                if not 1 <= len(parts) <= 3:
                    raise ValueError("unsupported wall-time format")
                seconds = 0.0
                for part in parts:
                    seconds = 60 * seconds + float(part)
                if not math.isfinite(seconds) or seconds < 0:
                    raise ValueError("invalid wall time")
                record["wall_seconds"] = seconds
            elif "Maximum resident set size (kbytes):" in line:
                rss = int(line.rsplit(":", 1)[1].strip())
                if rss < 0:
                    raise ValueError("negative RSS")
                record["max_rss_kib"] = rss
        if all(record[k] is not None for k in ("wall_seconds", "max_rss_kib")):
            record["status"] = "RECORDED"
    except (OSError, ValueError, IndexError) as exc:
        record["note"] = str(exc)
    return record


def resources(case, solver):
    stages = {name: gnu_time_record(case / ("time." + name + ".txt"))
              for name in ("blockMesh", "checkMesh", "setFields", solver)}
    measured = stages[solver]
    budget = None if measured["wall_seconds"] is None else measured["wall_seconds"] <= 120
    result = {"stages": stages, "solver_within_approx_120s_budget": budget,
            "budget_note": "120s is the approximate solver-time goal, separate from configurable timeout. "
                           "Complete preparation/preflight/checker workflow time is not inferred from solver time.",
            "whole_workflow_budget": "UNVERIFIED",
            "rss_note": "GNU time maximum RSS for each timed serial command; not a sum or whole-workstation memory."}
    wrappers = {name: gnu_time_record(case / ("time.workflow." + name + ".txt"))
                for name in ("mesh", "solve")}
    result["workflow_wrappers"] = wrappers
    # Optional user-side wrapper timing is complete only after Allrun returns.
    # Rechecking offline can then include it without rerunning any CFD.
    if all(r["status"] == "RECORDED" for r in wrappers.values()):
        try:
            preparation = float((case / "preparation.time.txt").read_text().strip().split("=", 1)[1])
            if not math.isfinite(preparation) or preparation < 0:
                raise ValueError("invalid preparation wall time")
            total = preparation + sum(r["wall_seconds"] for r in wrappers.values())
            result.update(recorded_workflow_wall_seconds=total,
                          whole_workflow_budget="RECORDED_SCOPE_WITHIN_TARGET" if total <= 120 else "RECORDED_SCOPE_OVER_TARGET",
                          workflow_scope="Recorded preparation body plus mesh/solve wrappers, including their preflights/checks; "
                                         "excludes build, Git, operator waiting, Python preparation startup and final offline report rerun.")
        except (OSError, ValueError, IndexError):
            pass
    return result


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
    report = {"status": "REVIEW_REQUIRED", "accuracy": "UNVERIFIED",
              "reference": "NOT_ESTABLISHED", "fields": {}, "issues": [], "resources": {}}
    try:
        manifest = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
        config = manifest["config"]
        report["solver"] = manifest["solver"]
        report["resources"] = resources(case, manifest["solver"])
        report["initialization"] = "RECORDED_COMPLETE" if (case / ".mesh-complete").is_file() else "UNVERIFIED"
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
        text = (case / ("log." + manifest["solver"])).read_text(encoding="utf-8")
        report["path_evidence"] = {
            "logged_lasers": sorted(set(re.findall(r"^\s*Laser:\s*(\S+)", text, re.M))),
            "seed_counts": [[int(a), int(b)] for a, b in re.findall(
                r"Total rays:\s*(\d+),\s*local particles:\s*(\d+)", text)],
            "vof_diagnostics": "vof" in log["categories"],
            "liquid_fraction_iteration_diagnostics": "epsilon" in log["categories"],
            "temperature_linear_solves": any(e["kind"] == "linear" and
                                             "Solving for T," in e["label"] for e in log["events"]),
            "pressure_linear_solves": any(e["kind"] == "linear" and
                                          "Solving for p_rgh," in e["label"] for e in log["events"]),
            "positive_deposition": True,
            "multiple_reflections": "NOT_ESTABLISHED",
            "steady_melt_pool": "NOT_ESTABLISHED",
            "note": "Log evidence confirms execution, not physical accuracy or all difficult regimes."}
        def scalar_values(name):
            field = native.parse_field(directory / name)
            return native.expand_field(field["internal"], geometry["cells"], 1, "scalar")
        alpha, temperature, liquid = map(scalar_values, ("alpha.metal", "T", "epsilon1"))
        metal = [i for i, a in enumerate(alpha) if a > 0.5]
        report["metal_observations"] = {"selection": "alpha.metal > 0.5", "cells": len(metal),
            "max_temperature_K": max((temperature[i] for i in metal), default=None),
            "liquid_fraction_range": [min(liquid[i] for i in metal), max(liquid[i] for i in metal)] if metal else None,
            "note": "Only final metal-dominated cells; gas liquid fraction is not used as proof of melting."}
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
    parser.add_argument("--feedback-bundle", action="store_true",
                        help="explicitly export redacted diagnostics after the outer solve timer finishes")
    args = parser.parse_args()
    if args.inputs_only and args.feedback_bundle:
        parser.error("--inputs-only cannot be combined with --feedback-bundle")
    from export_smoke_feedback import safe_directory, export_feedback, print_result

    def finish(code):
        if args.feedback_bundle:
            try:
                print_result(export_feedback(args.case_dir, check_exit_code=code))
            except (OSError, ValueError, TypeError, tarfile.TarError) as exc:
                print("ERROR [feedback] archive_status=FAILED; check exit unchanged: " + str(exc), file=sys.stderr)
        return code

    try:
        args.case_dir = safe_directory(args.case_dir)
        for name in ("smoke.txt", "smoke.json"):
            if (args.case_dir / name).is_symlink():
                raise ValueError("refusing to overwrite symlinked report: " + name)
        if args.inputs_only:
            check_inputs(args.case_dir)
            print("PASS [initialized-inputs] complete path/hash inventory")
            return 0
        report = check(args.case_dir)
        (args.case_dir / "smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        text = "Status: {}\nAccuracy: UNVERIFIED; reference: NOT_ESTABLISHED\nFields checked: {}\n".format(
            report["status"], len(report["fields"]))
        text += "\n".join(report["issues"]) + "\n"
        timed = report["resources"].get("stages", {}).get(report.get("solver"), {})
        text += "Solver wall seconds: {}; max RSS KiB: {}\nSolver within approximate 120s budget: {}\n".format(
            timed.get("wall_seconds"), timed.get("max_rss_kib"), report["resources"].get("solver_within_approx_120s_budget"))
        text += "Recorded workflow budget: {}; seconds: {}\n".format(
            report["resources"].get("whole_workflow_budget", "UNVERIFIED"), report["resources"].get("recorded_workflow_wall_seconds"))
        text += "Scope excludes build/operator waiting/final offline report; smoke is not physical validation or a steady melt-pool prediction.\n"
        text += "T range K: {}; alpha range: {}; Deposition range: {}\n".format(
            report.get("T_range"), report.get("alpha_bounds"), report.get("Deposition_range"))
        (args.case_dir / "smoke.txt").write_text(text, encoding="utf-8")
        print(text, end="")
        return finish({"SMOKE_CHECKS_PASSED": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}[report["status"]])
    except (OSError, ValueError, KeyError) as exc:
        print("ERROR [smoke-check] " + str(exc), file=sys.stderr)
        return finish(2)


if __name__ == "__main__":
    sys.exit(main())
