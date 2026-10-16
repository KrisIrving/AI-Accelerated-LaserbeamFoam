#!/usr/bin/env python3
"""Offline native-field checks for authorized M explorations; never run CFD.

Self-parsing checks sizes, explicit boundaries and finite values. It is neither
an A/B comparison nor validation of discretization, physics or performance.
"""
import argparse
import csv
import io
import itertools
import json
import math
import os
import re
import stat
import sys
import tarfile
import time
from decimal import Decimal
from pathlib import Path

import compare_plate2d_ab as native
from check_smoke_case import check_inputs, gnu_time_record

REQUIRED = {"T", "U", "p_rgh", "alpha.metal", "epsilon1", "Deposition", "phi"}
INITIAL_REQUIRED = {"T", "U", "p_rgh", "alpha.metal", "Laser_boundary"}
DEPOSITION_DIMENSIONS = [1, -1, -3, 0, 0, 0, 0]
PASSED = "EXPLORATION_CHECKS_PASSED"
CODE = {PASSED: 0, "FAIL": 1, "REVIEW_REQUIRED": 2}


def issue(report, status, message):
    report["issues"].append({"status": status, "message": message})
    if status == "FAIL" or report["status"] != "FAIL":
        report["status"] = status


def safe_inventory(case):
    """Reject every link/special entry, including directories, before reading."""
    case = Path(case).absolute()
    for parent in (case, *case.parents):
        if parent.is_symlink():
            raise native.ComparisonFailure("symlinked case ancestor: " + str(parent))
    if not case.is_dir():
        raise native.ComparisonFailure("missing case directory")
    total = 0
    pending = [case]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                mode = entry.stat(follow_symlinks=False).st_mode
                relative = Path(entry.path).relative_to(case).as_posix()
                if stat.S_ISLNK(mode):
                    raise native.ComparisonFailure("symlink is not accepted: " + relative)
                if stat.S_ISDIR(mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(mode):
                    total += entry.stat(follow_symlinks=False).st_size
                else:
                    raise native.ComparisonFailure("non-regular entry: " + relative)
    return total


def manifest(case):
    data = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
    config = data["config"]
    if (config["schema"] != "threeD-exploration-v1"
            or config["status"] != "EXPLORATION_AUTHORIZED"
            or config["formal_benchmark"] != "PROPOSED"
            or data["solver"] != "laserbeamFoam" or data["mpi_ranks"] != 1
            or data["experiment_id"] != config["id"] or config["id"] not in ("M1", "M2", "M3")):
        raise native.ComparisonFailure("unexpected exploration manifest/serial solver contract")
    if (len(config["cells"]) != 3 or any(type(n) is not int or n < 1 for n in config["cells"])
            or type(config["steps"]) is not int or config["steps"] < 1
            or type(config["write_interval"]) is not int or config["write_interval"] < 1
            or config["steps"] % config["write_interval"]):
        raise native.ComparisonFailure("invalid mesh/step/output configuration")
    dt, end = Decimal(config["delta_t"]), Decimal(config["end_time"])
    if not dt.is_finite() or dt <= 0 or end != dt * config["steps"]:
        raise native.ComparisonFailure("delta_t/steps/end_time disagree")
    if data["project_commit"] != data["build_commit"]:
        raise native.ComparisonFailure("recorded run/build commits differ")
    return data


def scan_log(path, require_end=True):
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if native.TRAPFPE_STARTUP.fullmatch(line.strip()):
            continue
        for marker, pattern in native.FATAL_LOG_MARKERS:
            if pattern.search(line):
                raise native.ComparisonFailure("{}:{}: {}: {}".format(path.name, number, marker, line))
        if any(native.NONFINITE.fullmatch(m[0]) for m in native.LOG_NUMBER.finditer(line)):
            raise native.ComparisonFailure("{}:{}: non-finite log token".format(path.name, number))
    nonempty = [line.strip() for line in lines if line.strip()]
    if require_end and (not nonempty or nonempty[-1] != "End"):
        raise native.ComparisonFailure(path.name + ": missing normal End")
    return lines


def parse_log(case, config):
    """Use the baseline fatal/event semantics without its ten-step contract."""
    if (case / "solver.exit.txt").read_text().strip() != "0":
        raise native.ComparisonFailure("solver.exit.txt: missing/nonzero solver exit")
    lines = scan_log(case / "log.laserbeamFoam")
    patterns = (
        ("linear", r"Solving for .+Initial residual.+Final residual.+No Iterations"),
        ("epsilon", r"Correcting epsilon1, mean residual"),
        ("continuity", r"continuity errors\s*:"),
        ("vof", r"Phase-1 volume fraction\s*="),
        ("courant", r"Courant Number mean:"),
        ("deltaT", r"^\s*deltaT\s*="),
        ("deposition", r"Total Q deposited:"),
    )
    times, events, execution, linear, alerts = [], [], [], {}, []
    previous_cpu = previous_clock = 0.0
    for line_number, line in enumerate(lines, 1):
        if re.search(r"\bDivergence detected\b|\bnot converged\b|\b(?:maximum|max)\b.*\biterations\b.*\b(?:reached|exceeded)\b", line, re.I):
            alerts.append({"line_number": line_number, "message": line})
        match = re.fullmatch(r"\s*Time\s*=\s*(\S+)\s*", line)
        if match:
            value = native.finite_number(match[1])
            times.append(value)
            events.append({"kind": "time", "values": [value]})
        for kind, pattern in patterns:
            if re.search(pattern, line):
                values = [native.finite_number(m[0]) for m in native.LOG_NUMBER.finditer(line)]
                if not values:
                    raise native.ReviewRequired("recognized diagnostic has no numerical data: " + line)
                events.append({"kind": kind, "values": values})
                break
        solve = re.search(r"Solving for ([^,]+), Initial residual = (\S+), Final residual = (\S+), No Iterations (\S+)", line)
        if solve:
            initial, final = map(native.finite_number, solve.group(2, 3))
            if initial < 0 or final < 0 or solve[4].startswith("-"):
                raise native.ComparisonFailure("invalid negative residual/iteration count: " + line)
            if not re.fullmatch(r"\d+", solve[4]):
                raise native.ReviewRequired("non-integer linear iteration count: " + line)
            iterations = int(solve[4])
            record = linear.setdefault(solve[1], {"solves": 0, "iterations_total": 0,
                "iterations_max": 0, "initial_residual_max": 0, "final_residual_max": 0,
                "final_residual_greater_than_initial_count": 0})
            record["solves"] += 1
            record["iterations_total"] += iterations
            record["iterations_max"] = max(record["iterations_max"], iterations)
            record["initial_residual_max"] = max(record["initial_residual_max"], initial)
            record["final_residual_max"] = max(record["final_residual_max"], final)
            record["final_residual_greater_than_initial_count"] += int(final > initial)
        elif "Solving for " in line:
            raise native.ReviewRequired("unrecognized linear diagnostic at line {}: {}".format(line_number, line))
        timing = re.fullmatch(r"\s*ExecutionTime\s*=\s*([0-9.eE+-]+)\s+s\s+ClockTime\s*=\s*([0-9.eE+-]+)\s+s\s*", line)
        if timing:
            cpu, clock = map(native.finite_number, timing.group(1, 2))
            if cpu < previous_cpu or clock < previous_clock or not times:
                raise native.ComparisonFailure("ExecutionTime/ClockTime decreased or preceded a Time event")
            execution.append({"step": len(times), "time_s": times[-1], "execution_cpu_s": cpu,
                "clock_s": clock, "delta_execution_cpu_s": cpu - previous_cpu,
                "delta_clock_s": clock - previous_clock,
                "clock_difference_resolved": clock > previous_clock})
            previous_cpu, previous_clock = cpu, clock
    if len(times) != config["steps"]:
        raise native.ComparisonFailure("expected {} Time events; found {}".format(config["steps"], len(times)))
    dt = float(config["delta_t"])
    if any(not math.isclose(t, i * dt, rel_tol=1e-10, abs_tol=dt * 1e-8)
           for i, t in enumerate(times, 1)):
        raise native.ComparisonFailure("Time events do not follow the configured fixed delta_t")
    categories = {e["kind"] for e in events}
    needed = {"linear", "epsilon", "continuity", "vof", "courant", "deposition"}
    if not needed <= categories:
        raise native.ReviewRequired("missing diagnostic categories: " + ", ".join(sorted(needed - categories)))
    if len(execution) != len(times) or [e["step"] for e in execution] != list(range(1, len(times) + 1)):
        raise native.ReviewRequired("ExecutionTime/ClockTime samples do not cover every physical step exactly once")
    text = "\n".join(lines)
    return {"times": times, "events": events, "categories": sorted(categories),
        "linear_summaries": linear, "execution": execution, "solver_alerts": alerts,
        "diagnostic_ranges": {kind: {"events": sum(e["kind"] == kind for e in events),
            "minimum_reported_number": min(v for e in events if e["kind"] == kind for v in e["values"]),
            "maximum_reported_number": max(v for e in events if e["kind"] == kind for v in e["values"])}
            for kind in ("courant", "continuity", "epsilon")},
        "path_evidence": {"logged_lasers": sorted(set(re.findall(r"^\s*Laser:\s*(\S+)", text, re.M))),
            "seed_counts": [[int(a), int(b)] for a, b in re.findall(r"Total rays:\s*(\d+),\s*local particles:\s*(\d+)", text)],
            "vof_diagnostics": "vof" in categories, "phase_change_iteration_diagnostics": "epsilon" in categories,
            "temperature_linear_solves": "T" in linear, "pressure_linear_solves": "p_rgh" in linear,
            "multiple_reflections": "NOT_ESTABLISHED", "significant_interface_motion": "NOT_ESTABLISHED",
            "note": "Calls and diagnostics do not establish melting, difficult coupling, or module cost shares."}}


def mesh_metrics(case, config):
    """Derive real cell volumes/centres only for verified Cartesian hexahedra.

    No requested grid spacing or bounding-box volume is silently assigned to
    cells. Native face addressing and every rectangular cell are checked first.
    Other meshes require a separate volume extractor, not guessed integrals.
    """
    geometry = native.mesh_geometry(case)
    if geometry["cells"] != math.prod(config["cells"]):
        raise native.ComparisonFailure("native mesh cell count differs from configured grid")
    mesh = case / "constant/polyMesh"
    parser = native.Parser(native.read_ascii(mesh / "points"))
    if parser.header()["class"] != ["vectorField"]:
        raise native.ReviewRequired("unsupported mesh points class")
    count = native.integer(parser.pop())
    raw = parser.item()
    parser.done()
    if not isinstance(raw, list) or len(raw) != count:
        raise native.ComparisonFailure("mesh points count mismatch")
    points = [native.component_value(value, 3) for value in raw]
    del raw
    scale = max(abs(value) for point in points for value in point)
    # blockMesh interpolation and ASCII roundtrips can put nominally coplanar
    # points a few ulps apart. Cluster roundoff only, far below grid spacing.
    coordinate_tolerance = 128 * math.ulp(scale)
    axes, indices, collapsed = [], [], []
    for axis in range(3):
        distinct = sorted({p[axis] for p in points})
        groups = []
        for value in distinct:
            if not groups or value - groups[-1][0] > coordinate_tolerance:
                groups.append([value])
            else:
                groups[-1].append(value)
        axes.append([math.fsum(group) / len(group) for group in groups])
        indices.append({value: index for index, group in enumerate(groups) for value in group})
        collapsed.append(len(distinct) - len(groups))
    if [len(values) - 1 for values in axes] != config["cells"]:
        raise native.ReviewRequired("native point coordinates do not form the configured Cartesian grid")
    for values in axes:
        spacings = [b - a for a, b in zip(values, values[1:])]
        if max(spacings) - min(spacings) > 4 * coordinate_tolerance:
            raise native.ReviewRequired("native mesh is not uniform Cartesian simpleGrading(1 1 1)")
    expected_bounds = ((-3e-4, 3e-4), (0, 3e-4), (-1e-4, 5e-4))
    if any(abs(found - expected) > 4 * coordinate_tolerance
           for axis, pair in enumerate(expected_bounds) for found, expected in zip((axes[axis][0], axes[axis][-1]), pair)):
        raise native.ComparisonFailure("native mesh bounds differ from pinned 600x300x600 micrometre geometry")
    indexed = [tuple(indices[a][p[a]] for a in range(3)) for p in points]
    if len(set(indexed)) != math.prod(len(values) for values in axes):
        raise native.ComparisonFailure("duplicate or incomplete Cartesian point lattice")
    owner, neighbour = native.label_list(mesh / "owner"), native.label_list(mesh / "neighbour")
    parser = native.Parser(native.read_ascii(mesh / "faces"))
    if parser.header()["class"] != ["faceList"]:
        raise native.ReviewRequired("unsupported native face class")
    faces = native.integer(parser.pop())
    parser.expect("(")
    if faces != len(owner):
        raise native.ComparisonFailure("face/owner count mismatch")
    cell_faces = [[] for _ in range(geometry["cells"])]
    for face in range(faces):
        length = native.integer(parser.pop())
        vertices = parser.item()
        if length != 4 or not isinstance(vertices, list) or len(vertices) != 4:
            raise native.ReviewRequired("only quadrilateral Cartesian faces are supported")
        labels = [native.integer(value) for value in vertices]
        if len(set(labels)) != 4 or any(value >= len(points) for value in labels):
            raise native.ComparisonFailure("invalid face vertex addressing")
        positions = [indexed[value] for value in labels]
        low = tuple(min(p[a] for p in positions) for a in range(3))
        high = tuple(max(p[a] for p in positions) for a in range(3))
        extents = tuple(h - l for h, l in zip(high, low))
        if sorted(extents) != [0, 1, 1] or set(positions) != set(itertools.product(*[
                (lo,) if lo == hi else (lo, hi) for lo, hi in zip(low, high)])):
            raise native.ReviewRequired("non-Cartesian face at native index " + str(face))
        axis = extents.index(0)
        if owner[face] >= geometry["cells"] or (face < len(neighbour) and neighbour[face] == owner[face]):
            raise native.ComparisonFailure("invalid cell face addressing")
        cell_faces[owner[face]].append((axis, low, high))
        if face < len(neighbour):
            if neighbour[face] >= geometry["cells"]:
                raise native.ComparisonFailure("invalid neighbour addressing")
            cell_faces[neighbour[face]].append((axis, low, high))
    parser.expect(")")
    parser.done()
    volumes, centres, seen = [], [], set()
    for cell, addressing in enumerate(cell_faces):
        low = tuple(min(face[1][a] for face in addressing) for a in range(3)) if addressing else ()
        high = tuple(max(face[2][a] for face in addressing) for a in range(3)) if addressing else ()
        if len(addressing) != 6 or tuple(h - l for h, l in zip(high, low)) != (1, 1, 1) or low in seen:
            raise native.ComparisonFailure("invalid Cartesian hexahedron at cell " + str(cell))
        planes = {(axis, lo[axis]) for axis, lo, _ in addressing}
        if planes != {(a, value) for a in range(3) for value in (low[a], high[a])}:
            raise native.ComparisonFailure("cell face planes do not enclose a hexahedron: " + str(cell))
        seen.add(low)
        volumes.append(math.prod(axes[a][high[a]] - axes[a][low[a]] for a in range(3)))
        centres.append([(axes[a][high[a]] + axes[a][low[a]]) / 2 for a in range(3)])
    if any(not math.isfinite(v) or v <= 0 for v in volumes):
        raise native.ComparisonFailure("non-positive/nonfinite derived volume")
    summary = dict(geometry, geometry_status="VERIFIED_CARTESIAN_HEXAHEDRA", geometric_directions=3,
        bounds_m=[[values[0], values[-1]] for values in axes],
        spacing_m=[[min(b - a for a, b in zip(values, values[1:])),
                    max(b - a for a, b in zip(values, values[1:]))] for values in axes],
        cell_volume_range_m3=[min(volumes), max(volumes)], total_volume_m3=math.fsum(volumes),
        coordinate_roundoff_tolerance_m=coordinate_tolerance,
        coordinate_values_collapsed_per_axis=collapsed,
        volume_source="Native points, faces, owner and neighbour; each Cartesian hexahedron verified")
    return geometry, volumes, centres, summary


def field_check(path, geometry, initial=False):
    parsed = native.parse_field(path)
    if initial:
        # Upstream initial templates can retain an unused empty default patch.
        unused = set(parsed["boundary"]) - set(geometry["patches"])
        if unused and not (unused == {"defaultFaces"} and
                parsed["boundary"]["defaultFaces"] == {"type": ["empty"]}):
            raise native.ReviewRequired("unexpected initial boundary entries: " + ", ".join(sorted(unused)))
        # Reuse baseline checks on a parsed copy without touching initial files.
        checked_geometry = dict(geometry, patches=dict(geometry["patches"], **{name: 0 for name in unused}))
    else:
        checked_geometry = geometry
    result = native.compare_fields(path, path, checked_geometry, 1e-12, 1e-10)
    count = geometry["cells" if parsed["location"] == "vol" else "internal_faces"]
    rank = parsed["class"][len(parsed["location"]):-5]
    values = native.expand_field(parsed["internal"], count, parsed["components"], rank[0].lower() + rank[1:])
    if path.name in ("T", "U", "alpha.metal", "epsilon1", "Deposition"):
        expected = "volVectorField" if path.name == "U" else "volScalarField"
        if parsed["class"] != expected:
            raise native.ComparisonFailure(path.name + ": unexpected field class " + parsed["class"])
    if path.name == "T" and min(values) <= 0:
        raise native.ComparisonFailure("non-positive absolute temperature")
    if path.name == "alpha.metal":
        alpha_values = list(values)
        for patch, size in geometry["patches"].items():
            # These entries prescribe alpha itself. Gradients and mixed-BC
            # weights have other meanings and are not alpha-value bounds.
            for key in ("value", "inletValue", "refValue"):
                entry = parsed["boundary"][patch].get(key)
                if entry is not None:
                    alpha_values.extend(native.expand_field(entry, size, 1, "scalar"))
        if min(alpha_values) < -1e-12 or max(alpha_values) > 1 + 1e-12:
            raise native.ComparisonFailure("alpha.metal internal/boundary outside existing [0,1] tolerance")
    return parsed, values, {"status": "PARSED_FINITE_INTERNAL_BOUNDARY_SIZE_CHECKED", "class": result["class"]}


def observations(directory, fields, values, volumes, centres, initial_volume, time_s, initial_alpha):
    if fields["Deposition"]["dimensions"] != DEPOSITION_DIMENSIONS:
        raise native.ComparisonFailure("Deposition dimensions {} cannot support volume-integrated power in W".format(
            fields["Deposition"]["dimensions"]))
    for name, expected in (("T", [0, 0, 0, 1, 0, 0, 0]), ("U", [0, 1, -1, 0, 0, 0, 0]),
                           ("alpha.metal", [0] * 7), ("epsilon1", [0] * 7)):
        if fields[name]["dimensions"] != expected:
            raise native.ComparisonFailure(name + ": dimensions do not match reported observation units")
    alpha, epsilon, temperature, velocity = (values[name] for name in ("alpha.metal", "epsilon1", "T", "U"))
    metal = [i for i, value in enumerate(alpha) if value > 0.5]
    if not metal:
        raise native.ComparisonFailure("no metal-dominated cells (alpha.metal > 0.5)")
    if any(epsilon[i] < -1e-12 or epsilon[i] > 1 + 1e-12 for i in metal):
        raise native.ComparisonFailure("metal-dominated epsilon1 outside [0,1] tolerance")
    metal_volume = math.fsum(a * v for a, v in zip(alpha, volumes))
    liquid_volume = math.fsum(a * e * v for a, e, v in zip(alpha, epsilon, volumes))
    speeds = [math.hypot(*velocity[3 * i:3 * i + 3]) for i in metal]
    region = [i for i in metal if epsilon[i] > 0.5]
    bounds = [[min(centres[i][a] for i in region), max(centres[i][a] for i in region)]
              for a in range(3)] if region else None
    result = {"time_s": time_s, "directory": directory.name, "T_min_K": min(temperature), "T_max_K": max(temperature),
        "metal_cells": len(metal), "metal_T_min_K": min(temperature[i] for i in metal),
        "metal_T_max_K": max(temperature[i] for i in metal), "metal_epsilon_min": min(epsilon[i] for i in metal),
        "metal_epsilon_max": max(epsilon[i] for i in metal), "metal_volume_m3": metal_volume,
        "initial_metal_volume_m3": initial_volume, "metal_volume_relative_change": (metal_volume - initial_volume) / initial_volume,
        "liquid_metal_volume_estimate_m3": liquid_volume,
        "metal_U_min_m_per_s": min(speeds), "metal_U_max_m_per_s": max(speeds),
        "deposition_min_W_per_m3": min(values["Deposition"]), "deposition_max_W_per_m3": max(values["Deposition"]),
        "deposition_power_W": math.fsum(q * v for q, v in zip(values["Deposition"], volumes)),
        "alpha_min": min(alpha), "alpha_max": max(alpha),
        "mixed_cells_count": sum(0 < a < 1 for a in alpha),
        "alpha_change_from_initial_max_abs": max(abs(a - a0) for a, a0 in zip(alpha, initial_alpha)),
        "alpha_change_from_initial_L1_volume_m3": math.fsum(abs(a - a0) * v for a, a0, v in zip(alpha, initial_alpha, volumes)),
        "solidus_reached": max(temperature[i] for i in metal) >= 1928.15,
        "nonzero_metal_liquid_fraction": max(epsilon[i] for i in metal) > 0,
        "threshold_liquid_region_cells": len(region), "threshold_liquid_region_cell_centre_bounds_m": bounds,
        "threshold_liquid_region_note": "alpha>0.5 and epsilon1>0.5 cell-centre bounds; resolution-limited, not validated melt-pool dimensions",
        "significant_interface_motion": "NOT_ESTABLISHED", "multiple_reflections": "NOT_ESTABLISHED"}
    if any(isinstance(value, float) and not math.isfinite(value) for value in result.values()):
        raise native.ComparisonFailure("derived observation overflow/nonfinite result")
    return result


def resource_records(case, config, data_bytes):
    stages = {name: gnu_time_record(case / ("time." + name + ".txt"))
              for name in ("blockMesh", "checkMesh", "setFields", "laserbeamFoam")}
    wrappers = {name: gnu_time_record(case / ("time.workflow." + name + ".txt")) for name in ("mesh", "solve")}
    solver = stages["laserbeamFoam"]
    recorded_rss = [record["max_rss_kib"] for record in stages.values() if record["max_rss_kib"] is not None]
    stage_max_rss = max(recorded_rss) if recorded_rss else None
    result = {"stages": stages, "workflow_wrappers": wrappers,
        "solver_wall_seconds": solver["wall_seconds"], "solver_max_rss_kib": solver["max_rss_kib"],
        "max_rss_kib": stage_max_rss,
        "data_bytes": data_bytes, "resource_policy": "MONITORED_ONLY",
        "data_scope": "All regular files in this case before this check's new reports/archive; existing reports/feedback included. Conservative total footprint, not exact incremental CFD data.",
        "rss_scope": "Maximum of recorded GNU time command RSS across blockMesh/checkMesh/setFields/solver; solver_max_rss_kib separate. Not a sum, whole-workstation/process-tree claim, or offline checker/export RSS.",
        "recorded_workflow_wall_seconds": None, "workflow_timing_status": "INCOMPLETE_TIMING",
        "scope": "Preparation body + completed mesh/solve wrappers; excludes build, Git, operator wait, final offline check/archive. Solver includes native output I/O."}
    if solver["status"] == "RECORDED":
        result["solver_within_timeout"] = solver["wall_seconds"] <= config["solver_timeout_seconds"]
    result["stage_timing_status"] = "RECORDED" if all(record["status"] == "RECORDED" for record in stages.values()) else "INCOMPLETE_TIMING"
    result["rss_within_observation_budget"] = None if stage_max_rss is None else stage_max_rss <= config["max_rss_kib"]
    result["data_within_observation_budget"] = data_bytes <= config["max_data_bytes"]
    if all(record["status"] == "RECORDED" for record in wrappers.values()):
        try:
            value = float((case / "preparation.time.txt").read_text().strip().split("=", 1)[1])
            if not math.isfinite(value) or value < 0:
                raise ValueError("invalid preparation timer")
            result["recorded_workflow_wall_seconds"] = value + sum(r["wall_seconds"] for r in wrappers.values())
            result["workflow_timing_status"] = "RECORDED_SCOPE"
        except (OSError, ValueError, IndexError):
            pass
    return result


def check(case, mesh_only=False):
    started = time.perf_counter()
    case = Path(case).absolute()
    report = {"status": PASSED, "accuracy": "UNVERIFIED", "reference": "NOT_ESTABLISHED",
        "formal_benchmark": "PROPOSED", "mode": "mesh-only" if mesh_only else "all-output-times",
        "issues": [], "fields": {}, "uniform": {}, "observations": [], "resources": {}, "execution_times": []}
    try:
        data_bytes = safe_inventory(case)
        record = manifest(case)
        config = record["config"]
        report.update(experiment_id=record["experiment_id"], solver=record["solver"],
            project_commit=record["project_commit"], build_commit=record["build_commit"], config=config)
        report["resources"] = resource_records(case, config, data_bytes)
        try:
            check_inputs(case)
        except ValueError as exc:
            raise native.ComparisonFailure(str(exc)) from exc
        if not mesh_only and not (case / ".mesh-complete").is_file():
            raise native.ComparisonFailure("missing .mesh-complete initialization marker")
        for stage in ("blockMesh", "checkMesh", "setFields"):
            if (case / ("exit." + stage + ".txt")).read_text().strip() != "0":
                raise native.ComparisonFailure(stage + ": nonzero/missing stage exit")
            scan_log(case / ("log." + stage))
        mesh_log = (case / "log.checkMesh").read_text()
        if not re.search(r"\bMesh OK\.?\s*$", mesh_log, re.M):
            raise native.ComparisonFailure("checkMesh did not report Mesh OK")
        geometry, volumes, centres, summary = mesh_metrics(case, config)
        report["mesh"] = summary
        initial_files = {p.name for p in (case / "0").iterdir() if p.name != "uniform"}
        if not INITIAL_REQUIRED <= initial_files:
            raise native.ComparisonFailure("missing initial fields: " + ", ".join(sorted(INITIAL_REQUIRED - initial_files)))
        initial_alpha, initial_temperature = None, None
        report["initialization"] = {"status": "IN_PROGRESS", "fields": {}}
        for name in sorted(initial_files):
            _, value, result = field_check(case / "0" / name, geometry, initial=True)
            report["initialization"]["fields"][name] = result
            if name == "alpha.metal":
                initial_alpha = value
            elif name == "T":
                initial_temperature = value
        initial_volume = math.fsum(a * v for a, v in zip(initial_alpha, volumes))
        if initial_volume <= 0:
            raise native.ComparisonFailure("initial metal volume is not positive")
        report["initial_metal_volume_m3"] = initial_volume
        initial_metal = [i for i, value in enumerate(initial_alpha) if value > 0.5]
        if not initial_metal:
            raise native.ComparisonFailure("no initial metal-dominated cells")
        initial_metal_max = max(initial_temperature[i] for i in initial_metal)
        report["initial_metal_temperature_max_K"] = initial_metal_max
        report["initialization"].update(status="PASS", field_names=sorted(initial_files),
            fields_checked=len(initial_files), metal_cells=len(initial_metal),
            metal_volume_m3=initial_volume, metal_T_max_K=initial_metal_max)
        report["phase_interval_K"] = {"solidus": 1928.15, "liquidus": 1978,
            "source": "Pinned fiveLasersOnSubstrate transportProperties; not experimentally calibrated"}
        output_times = {}
        for path in case.iterdir():
            if native.NUMBER.fullmatch(path.name) and float(path.name) > 0:
                value = float(path.name)
                if value in output_times or not path.is_dir():
                    raise native.ComparisonFailure("duplicate/non-directory output time: " + path.name)
                output_times[value] = path
        if mesh_only:
            if output_times or (case / ".solve-started").exists():
                raise native.ComparisonFailure("mesh-only check requires a fresh initialized case without solver attempt")
            report["status"] = "MESH_INITIALIZATION_CHECKS_PASSED"
            return report
        log = parse_log(case, config)
        report.update(steps=len(log["times"]), final_time=log["times"][-1], diagnostic_events=len(log["events"]),
            path_evidence=log["path_evidence"], linear_summaries=log["linear_summaries"],
            diagnostic_ranges=log["diagnostic_ranges"], execution_times=log["execution"], solver_alerts=log["solver_alerts"])
        for alert in log["solver_alerts"]:
            issue(report, "REVIEW_REQUIRED", "log.laserbeamFoam:{}: {}".format(alert["line_number"], alert["message"]))
        expected_times = [float(Decimal(config["delta_t"]) * step)
                          for step in range(config["write_interval"], config["steps"] + 1, config["write_interval"])]
        report["expected_output_times_s"] = expected_times
        report["output_times_s"] = sorted(output_times)
        if set(output_times) != set(expected_times):
            raise native.ComparisonFailure("output time set differs; missing={}, extra={}".format(
                sorted(set(expected_times) - set(output_times)), sorted(set(output_times) - set(expected_times))))
        first_names = None
        for output_time, directory in sorted(output_times.items()):
            names = {p.name for p in directory.iterdir() if p.name != "uniform"}
            if first_names is None:
                first_names = names
            if names != first_names:
                issue(report, "FAIL", directory.name + ": written field set differs from first output")
            missing = REQUIRED - names
            if missing:
                issue(report, "FAIL", directory.name + ": missing fields: " + ", ".join(sorted(missing)))
            fields, values = {}, {}
            report["fields"][directory.name] = {}
            for name in sorted(names):
                try:
                    path = directory / name
                    if not path.is_file():
                        raise native.ReviewRequired("non-file physical field")
                    fields[name], values[name], result = field_check(path, geometry)
                    report["fields"][directory.name][name] = result
                except (native.ComparisonFailure, native.ReviewRequired, OSError, ValueError) as exc:
                    status = "FAIL" if isinstance(exc, native.ComparisonFailure) else "REVIEW_REQUIRED"
                    issue(report, status, directory.name + "/" + name + ": " + str(exc))
            try:
                if not (directory / "uniform").is_dir():
                    raise native.ComparisonFailure("missing uniform runtime-state directory")
                uniform = native.compare_uniform_directory(directory / "uniform", directory / "uniform", 1e-12, 1e-10, geometry)
                report["uniform"][directory.name] = uniform
                if uniform["status"] != "PASS":
                    issue(report, uniform["status"], directory.name + "/uniform: " + str(uniform["issues"]))
            except (native.ComparisonFailure, native.ReviewRequired, OSError, ValueError) as exc:
                issue(report, "FAIL" if isinstance(exc, native.ComparisonFailure) else "REVIEW_REQUIRED",
                      directory.name + "/uniform: " + str(exc))
            if REQUIRED <= set(values):
                try:
                    observed = observations(directory, fields, values, volumes, centres, initial_volume, output_time, initial_alpha)
                    observed["metal_temperature_above_initial_max_K"] = observed["metal_T_max_K"] - initial_metal_max
                    observed["metal_temperature_risen"] = observed["metal_T_max_K"] > initial_metal_max
                    report["observations"].append(observed)
                except (native.ComparisonFailure, native.ReviewRequired, ValueError) as exc:
                    issue(report, "FAIL" if isinstance(exc, native.ComparisonFailure) else "REVIEW_REQUIRED", directory.name + ": " + str(exc))
        if not any(row["deposition_max_W_per_m3"] > 0 for row in report["observations"]):
            issue(report, "REVIEW_REQUIRED", "no positive output deposition; target heat path not established")
        if report["resources"]["stages"]["laserbeamFoam"]["status"] != "RECORDED":
            issue(report, "REVIEW_REQUIRED", "missing/incomplete solver GNU time wall/RSS record")
        if report["resources"]["stage_timing_status"] != "RECORDED":
            issue(report, "REVIEW_REQUIRED", "incomplete command-stage GNU time records; maximum stage RSS is not fully established")
        execution_file = dict(line.split("=", 1) for line in (case / "execution.txt").read_text().splitlines() if "=" in line)
        if execution_file.get("mpi_ranks") != "1" or execution_file.get("threads") != "1":
            issue(report, "FAIL", "execution.txt does not confirm serial/rank1/thread1 execution")
        report["observation_note"] = "No residual, volume-drift or significant-interface thresholds invented; activity is not physical validation. No convergence, hot-spot rank or AI speedup established."
    except native.ComparisonFailure as exc:
        issue(report, "FAIL", str(exc))
    except (native.ReviewRequired, OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError) as exc:
        issue(report, "REVIEW_REQUIRED", str(exc))
    finally:
        initialization = report.get("initialization", {})
        if initialization.get("status") == "IN_PROGRESS":
            initialization.update(status=report["status"],
                field_names=sorted(initialization["fields"]), fields_checked=len(initialization["fields"]))
        report["offline_check_wall_seconds"] = time.perf_counter() - started
        report["offline_check_scope"] = "Check only, including inventory/parser; excludes report serialization and feedback export. Not solver time or RSS."
    return report


def csv_text(rows):
    if not rows:
        return ""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, separators=(",", ":")) if isinstance(value, (list, dict)) else value
                         for key, value in row.items()})
    return stream.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--feedback-bundle", action="store_true")
    args = parser.parse_args(argv)
    if args.mesh_only and args.feedback_bundle:
        parser.error("--mesh-only cannot be combined with --feedback-bundle")
    case = args.case_dir.absolute()
    code = 2
    try:
        if not case.is_dir() or any(p.is_symlink() for p in (case, *case.parents)):
            raise ValueError("missing/symlinked case directory or ancestor")
        report = check(case, args.mesh_only)
        mesh_pass = report["status"] == "MESH_INITIALIZATION_CHECKS_PASSED"
        code = 0 if mesh_pass else CODE[report["status"]]
        summary = ("Status: {}\nExperiment: {}; formal benchmark: PROPOSED\n"
                   "Accuracy: UNVERIFIED; reference: NOT_ESTABLISHED\n"
                   "Initial fields checked: {}; initialization: {}\n"
                   "Steps: {}; output times: {}; parsed field files: {}\n"
                   "Solver wall seconds: {}; max RSS KiB: {}; case bytes before report/export: {}\n"
                   "Resource policy: MONITORED_ONLY\nOffline checker seconds: {}\n").format(
                       report["status"], report.get("experiment_id"),
                       report.get("initialization", {}).get("fields_checked", 0),
                       report.get("initialization", {}).get("status", "NOT_ESTABLISHED"), report.get("steps"),
                       len(report.get("output_times_s", [])), sum(len(d) for d in report["fields"].values()),
                       report["resources"].get("solver_wall_seconds"), report["resources"].get("max_rss_kib"),
                       report["resources"].get("data_bytes"), report["offline_check_wall_seconds"])
        summary += "\n".join("{}: {}".format(item["status"], item["message"]) for item in report["issues"]) + "\n"
        mesh_summary = dict(report.get("mesh", {}), check_mode=report["mode"], check_status=report["status"],
            initialization=report.get("initialization", {"status": "NOT_ESTABLISHED", "fields_checked": 0}),
            issues=report["issues"])
        payload = {"mesh-summary.json": json.dumps(mesh_summary, indent=2, allow_nan=False) + "\n"}
        if args.mesh_only:
            payload["mesh-check.txt"] = summary
        else:
            payload.update({"m.json": json.dumps(report, indent=2, allow_nan=False) + "\n", "m.txt": summary,
                "observations.csv": csv_text(report["observations"]), "execution_times.csv": csv_text(report["execution_times"])})
        for name in payload:
            target = case / name
            if target.exists() or target.is_symlink():
                metadata = target.lstat()
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    raise ValueError("refusing to overwrite non-regular/linked report " + name)
        for name, text in payload.items():
            (case / name).write_text(text, encoding="utf-8")
        print(summary, end="")
    except (OSError, ValueError, KeyError, native.ComparisonFailure) as exc:
        code = 2
        print("ERROR [m-check] " + str(exc), file=sys.stderr)
    if args.feedback_bundle:
        try:
            from export_smoke_feedback import export_feedback, print_result
            print_result(export_feedback(case, check_exit_code=code, profile="m"))
        except (OSError, ValueError, TypeError, tarfile.TarError) as exc:
            print("ERROR [feedback] archive_status=FAILED; check exit unchanged: " + str(exc), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
