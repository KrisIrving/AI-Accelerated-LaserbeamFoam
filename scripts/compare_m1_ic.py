#!/usr/bin/env python3
"""Read-only M1 / M3 / M1-IC diagnostics at 1, 2, 3 us; never run CFD."""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import compare_m1_m3 as c
import m1_ic as ic


def overlap(a, b, volumes):
    pa = math.fsum(max(x, 0) * v for x, v in zip(a, volumes))
    pb = math.fsum(max(x, 0) * v for x, v in zip(b, volumes))
    common = math.fsum(min(max(x, 0), max(y, 0)) * v for x, y, v in zip(a, b, volumes))
    return {"positive_common_W": common, "positive_power_A_W": pa, "positive_power_B_W": pb,
        "overlap_over_smaller_positive_power": common / min(pa, pb) if min(pa, pb) > 0 else None,
        "definition": "Integral min(qA+,qB+) / min(integral qA+,integral qB+) on verified coarse cells; not native subcell overlap"}


def compare(m1, m3, controlled, report):
    cases = [c.load_case(m1, "M1"), c.load_case(m3, "M3"),
             c.load_case(controlled, "M1-IC", manifest_reader=ic.manifest)]
    a, b, experiment = cases
    for case in (a, b):
        if case["manifest"]["config"] != ic.prep.config_for(case["source"].label):
            raise c.native.ComparisonFailure("three-way comparison requires authorized source profiles")
    src = experiment["source"]
    src.file(ic.REFERENCE)
    src.file("ic-initialization.json")
    initial_check = ic.validate_initial(src.path, experiment["manifest"], experiment["geometry"],
        experiment["grid"]["volumes"], experiment["grid"]["centres"], experiment["mesh"], experiment["initial"]["alpha.metal"])
    ref = ic.reference(src.path, experiment["manifest"])
    for case in (a, b):
        if str(case["source"].path) != str(Path(experiment["manifest"]["source_cases"][case["source"].label]).resolve()):
            raise c.native.ComparisonFailure("comparison source case differs from IC preparation source")
    inputs = [ic.prepared_inputs(case) for case in cases]
    if {p for p in set(inputs[0]) | set(inputs[1]) if inputs[0].get(p) != inputs[1].get(p)} != {"system/blockMeshDict"}:
        raise c.native.ComparisonFailure("M1/M3 prepared input changes exceed grid")
    differences = {p for p in set(inputs[0]) | set(inputs[2]) if inputs[0].get(p) != inputs[2].get(p)}
    if differences != {"system/controlDict"}:
        raise c.native.ComparisonFailure("M1-IC prepared input changes exceed authorized duration/write schedule")
    # Compare control entries semantically, so an unrelated change in the same
    # file cannot hide behind the authorized time-window difference.
    controls = [c.dictionary(case["source"], "system/controlDict", case_paths=True) for case in (a, experiment)]
    for key in ("endTime", "writeInterval"):
        controls[0].pop(key, None)
        controls[1].pop(key, None)
    c.native.compare_tree(controls[0], controls[1], 1e-12, 1e-10, "controlDict unchanged entries")
    groups = c.build_mapping(a["grid"], b["grid"])
    g, fine = a["grid"], b["grid"]
    # New blockMesh numbering may differ. Reorder IC into original M1 cells.
    mapping = [None] * len(g["volumes"])
    ic.expected_alpha(ref, experiment["grid"]["centres"], experiment["grid"]["volumes"], experiment["mesh"])
    for key, cell in g["lookup"].items():
        mapping[cell] = experiment["grid"]["lookup"][key]
    reorder = lambda values, rank=1: [values[j * rank + k] for j in mapping for k in range(rank)]
    vc, vf = g["volumes"], fine["volumes"]
    times = sorted(experiment["times"])
    if times != [Decimal("1e-6"), Decimal("2e-6"), Decimal("3e-6")] or any(t not in ca["times"] for ca in cases for t in times):
        raise c.native.ComparisonFailure("missing authorized common 1/2/3 us outputs")
    report.update(times_s=[float(t) for t in times], selected_fields=list(c.FIELDS),
        mapping={"status": "NATIVE_COORDINATES_VOLUMES_VERIFIED", "fine_children_per_coarse_cell": 8,
                 "IC_reordered_by_native_coordinates": True},
        initial={case["source"].label: case["surface"] for case in cases},
        controlled_initialization=initial_check, metrics=[], profiles=[], laser_geometry=[], laser_profiles=[],
        mapped_differences={}, source_records={}, first_observed_melting_s={},
        initial_alpha_IC_vs_restricted_M3=c.norms(ref["alpha"], reorder(experiment["initial"]["alpha.metal"]), vc),
        initial_T_IC_vs_M1=c.norms(a["initial"]["T"], reorder(experiment["initial"]["T"]), vc))
    for case in cases:
        label = case["source"].label
        report["source_records"][label] = {"run_commit": case["manifest"]["project_commit"],
            "build_commit": case["manifest"]["build_commit"], "log": case["log"], "resources": case["resources"]}
        report["profiles"].extend(c.y_layers(case["grid"], case["initial"], label, 0))
        geometry, profiles = c.laser_profiles(case["grid"], case["lasers"], case["surface"], case["initial"], label, 0)
        report["laser_geometry"].extend(geometry)
        report["laser_profiles"].extend(profiles)
        report["first_observed_melting_s"][label] = {"alpha_gt_05": None, "alpha_gt_0": None}
    for t in times:
        values = []
        for case in cases:
            label = case["source"].label
            fields = {n: c.read_volume(case["source"], case["times"][t] + "/" + n, case["geometry"], n) for n in c.FIELDS}
            values.append(fields)
            metrics = c.field_metrics(case["grid"], fields, case["surface"]["metal_volume_m3"])
            occupied = [i for i, alpha in enumerate(fields["alpha.metal"]) if alpha > 0]
            metrics.update(T_max_alpha_gt_0_K=max((fields["T"][i] for i in occupied), default=None),
                epsilon_max_alpha_gt_0=max((fields["epsilon1"][i] for i in occupied), default=None))
            report["metrics"].append(dict(case=label, time_s=float(t), **metrics))
            for mask, peak in (("alpha_gt_05", metrics["metal_epsilon_max"]),
                               ("alpha_gt_0", metrics["epsilon_max_alpha_gt_0"])):
                if peak is not None and peak > 0 and report["first_observed_melting_s"][label][mask] is None:
                    report["first_observed_melting_s"][label][mask] = float(t)
            report["profiles"].extend(c.y_layers(case["grid"], fields, label, float(t)))
            geometry, profiles = c.laser_profiles(case["grid"], case["lasers"], case["surface"], fields, label, float(t))
            report["laser_geometry"].extend(geometry)
            report["laser_profiles"].extend(profiles)
        coarse = values[0]
        restricted = {n: c.restrict(values[1][n], groups, vf, vc, 3 if n == "U" else 1) for n in c.FIELDS}
        control = {n: reorder(values[2][n], 3 if n == "U" else 1) for n in c.FIELDS}
        pairs = {"M1_to_IC": (coarse, control), "IC_to_restricted_M3": (control, restricted),
                 "M1_to_restricted_M3": (coarse, restricted)}
        differences = {key: {n: c.norms(x[n], y[n], vc, 3 if n == "U" else 1) for n in c.FIELDS}
                       for key, (x, y) in pairs.items()}
        products = [[x * y for x, y in zip(f["alpha.metal"], f["epsilon1"])] for f in values]
        products = [products[0], c.restrict(products[1], groups, vf, vc), reorder(products[2])]
        for key, (i, j) in {"M1_to_IC": (0, 2), "IC_to_restricted_M3": (2, 1), "M1_to_restricted_M3": (0, 1)}.items():
            differences[key]["alpha_times_epsilon1"] = c.norms(products[i], products[j], vc)
            x, y = pairs[key]
            differences[key]["positive_deposition_overlap"] = overlap(x["Deposition"], y["Deposition"], vc)
        # Metal-weighted T restriction is a diagnostic, not enthalpy conservation.
        weighted = c.restrict([x * y for x, y in zip(values[1]["alpha.metal"], values[1]["T"])], groups, vf, vc)
        tmetal = [x / alpha if alpha > 0 else 0 for x, alpha in zip(weighted, restricted["alpha.metal"])]
        mask = [i for i in range(len(vc)) if control["alpha.metal"][i] > 0.5 and restricted["alpha.metal"][i] > 0.5]
        differences["IC_to_restricted_M3"]["T_common_metal_alpha_weighted"] = c.norms(control["T"], tmetal, vc, selected=mask)
        report["mapped_differences"][str(t)] = differences
    # Hash source files before and after this tool's read window, including the
    # source reference used to prepare IC. This says nothing about earlier history.
    ic.reference(src.path, experiment["manifest"])
    for case in cases:
        case["source"].unchanged()
    report["consumed_sources_sha256"] = {ca["source"].label + "/" + p: checksum
        for ca in cases for p, checksum in ca["source"].hashes.items()}
    report["consumed_sources_unchanged_during_comparison"] = True
    report["interpretation"] = {
        "same_grid_intervention": "M1 vs M1-IC changes initial alpha and its derived BC caches only, over the same first 300 steps",
        "remaining_confounders": "IC vs M3 retains grid/source allocation/phase discretization differences; not an isolated grid-convergence test",
        "interface": "Fractional alpha is volume information, not an independently checked 97.5 um PLIC plane",
        "temperature_weighting": "Volume and alpha-weighted diagnostics; neither proves thermal-energy conservation",
        "melting": "First nonzero epsilon at saved sample, not exact onset; alpha>0 includes numerical tails",
        "initial_deposition": "Only compare saved native Deposition; no t=0 field invented",
        "physical_accuracy": "UNVERIFIED", "causal_explanation_of_all_early_temperature_difference": "NOT_ESTABLISHED",
        "hotspot": "NOT_ESTABLISHED", "ai_speedup": "NOT_STUDIED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("m1-case-dir", "m3-case-dir", "ic-case-dir", "report-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    report = {"status": "COMPARISON_COMPLETED", "issues": [], "scope": "M1/M3/M1-IC controlled initial-alpha diagnostics"}
    started = time.perf_counter()
    try:
        out = ic.prep.below(args.report_dir, ic.REPO / "validation", "three-way report")
        if out.exists():
            raise ValueError("report directory exists; never overwrite previous evidence")
        out.mkdir(parents=True)
        report["tool_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ic.REPO, text=True).strip()
        report["tool_sources_sha256"] = {name: c.digest(Path(__file__).parent / name) for name in (
            "compare_m1_ic.py", "m1_ic.py", "compare_m1_m3.py", "check_m_case.py", "compare_plate2d_ab.py")}
        compare(args.m1_case_dir, args.m3_case_dir, args.ic_case_dir, report)
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError,
            c.native.ComparisonFailure, c.native.ReviewRequired, subprocess.CalledProcessError) as exc:
        status = "FAIL" if isinstance(exc, c.native.ComparisonFailure) else "REVIEW_REQUIRED"
        report.update(status=status, issues=[{"status": status, "message": str(exc)}])
    report["offline_wall_seconds"] = time.perf_counter() - started
    report["timing_scope"] = "Native selected-field/mesh/log/source-hash diagnostics; excludes report/archive publication, CFD and original full-check runtime"
    report["metric_definitions"] = {
        "norms": "Second named field minus first on native M1 cells; volume L1/L2, max Linf, vector Euclidean length",
        "relative_norms": "Matching first named field norm as denominator; null for nonzero error with zero reference",
        "liquid_volume": "sum(alpha*epsilon1*V); restrict product, not product of averages",
        "temperature_masks": "metal: alpha>0.5; alpha_gt_0 includes fractional cells and numerical tails",
        "selected_scope": "T, U, alpha.metal, epsilon1, Deposition; previous full-check PASS is separate, unread sources not recertified"}
    if "out" in locals() and out.is_dir() and not any(out.iterdir()):
        try:
            c.publish(out, report, archive_name="m1-ic-comparison-feedback.tar.gz")
        except (OSError, ValueError, tarfile.TarError) as exc:
            print("ERROR [three-way feedback] " + str(exc), file=sys.stderr)
            return 2
    else:
        print(json.dumps(report, indent=2), file=sys.stderr)
    return c.CODE[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
