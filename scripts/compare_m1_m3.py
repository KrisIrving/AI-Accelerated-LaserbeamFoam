#!/usr/bin/env python3
"""Read-only Cartesian cross-grid diagnostics. No CFD or equivalence verdict.

Use native addressing, not cell-index order, for 2x2x2 volume restriction.
Only selected volume fields are re-read; existing full exploration checks are
reported separately and are not silently replaced by this diagnostic tool.
"""
import argparse
import bisect
import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time
from decimal import Decimal

import check_m_case as checks
import compare_plate2d_ab as native
from check_smoke_case import check_inputs, gnu_time_record
from export_smoke_feedback import redact, safe_directory

REPO = Path(__file__).resolve().parents[1]
FIELDS = ("T", "alpha.metal", "epsilon1", "Deposition", "U")
DIMS = {"T": [0, 0, 0, 1, 0, 0, 0], "alpha.metal": [0] * 7,
        "epsilon1": [0] * 7, "Deposition": checks.DEPOSITION_DIMENSIONS,
        "U": [0, 1, -1, 0, 0, 0, 0]}
CODE = {"COMPARISON_COMPLETED": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


class Source:
    def __init__(self, path, label):
        self.path, self.label = safe_directory(path), label
        self.case_bytes = checks.safe_inventory(self.path)
        self.hashes = {}

    def file(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or ".." in relative.parts:
            raise native.ComparisonFailure("unsafe source relative path")
        path = self.path / relative
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise native.ComparisonFailure(self.label + "/" + relative.as_posix() + ": missing/linked file")
        self.hashes.setdefault(relative.as_posix(), digest(path))
        return path

    def unchanged(self):
        for relative, previous in self.hashes.items():
            path = self.path / relative
            if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)) or digest(path) != previous:
                raise native.ComparisonFailure(self.label + "/" + relative + ": changed during comparison")


def read_volume(source, relative, geometry, name, initial=False):
    """Parse once; validate explicit boundary entries without repeated reads."""
    try:
        parsed = native.parse_field(source.file(relative))
        components = 3 if name == "U" else 1
        if parsed["class"] != ("volVectorField" if components == 3 else "volScalarField"):
            raise native.ComparisonFailure("unexpected volume field class")
        if parsed["dimensions"] != DIMS[name]:
            raise native.ComparisonFailure("unexpected dimensions for " + name)
        kind = "vector" if components == 3 else "scalar"
        values = native.expand_field(parsed["internal"], geometry["cells"], components, kind)
        patches = dict(geometry["patches"])
        extra = set(parsed["boundary"]) - set(patches)
        if initial and extra == {"defaultFaces"} and parsed["boundary"]["defaultFaces"] == {"type": ["empty"]}:
            patches["defaultFaces"] = 0
        if set(parsed["boundary"]) != set(patches):
            raise native.ReviewRequired("field patch set differs from native mesh")
        for patch, size in patches.items():
            state = parsed["boundary"][patch]
            if not isinstance(state, dict) or not state.get("type"):
                raise native.ReviewRequired("missing/invalid boundary type: " + patch)
            for key, entry in state.items():
                if isinstance(entry, list) and entry and entry[0] in ("uniform", "nonuniform"):
                    boundary = native.expand_field(entry, size, components, kind)
                    if name == "alpha.metal" and key in ("value", "inletValue", "refValue"):
                        if any(a < -1e-12 or a > 1 + 1e-12 for a in boundary):
                            raise native.ComparisonFailure("alpha boundary outside existing bounds")
                else:
                    native.compare_tree(entry, entry, 1e-12, 1e-10, patch + "/" + key)
        if name == "T" and min(values) <= 0:
            raise native.ComparisonFailure("non-positive absolute temperature")
        if name == "alpha.metal" and (min(values) < -1e-12 or max(values) > 1 + 1e-12):
            raise native.ComparisonFailure("alpha internal outside existing bounds")
        return values
    except (native.ComparisonFailure, native.ReviewRequired) as exc:
        raise type(exc)(source.label + "/" + str(relative) + ": " + str(exc)) from exc


def lattice(centres, volumes, summary, shape):
    bounds = summary["bounds_m"]
    spacing = [(hi - lo) / n for (lo, hi), n in zip(bounds, shape)]
    tol = max(8 * summary["coordinate_roundoff_tolerance_m"],
              128 * math.ulp(max(abs(x) for pair in bounds for x in pair)))
    lookup = {}
    for cell, centre in enumerate(centres):
        key = tuple(round((x - bounds[a][0]) / spacing[a] - 0.5) for a, x in enumerate(centre))
        if any(not 0 <= key[a] < shape[a] or
               abs(centre[a] - (bounds[a][0] + (key[a] + 0.5) * spacing[a])) > tol for a in range(3)):
            raise native.ComparisonFailure("native cell centre is off the Cartesian lattice")
        if key in lookup:
            raise native.ComparisonFailure("duplicate Cartesian cell position")
        if not math.isclose(volumes[cell], math.prod(spacing), rel_tol=1e-10, abs_tol=0):
            raise native.ComparisonFailure("native volume disagrees with Cartesian bounds")
        lookup[key] = cell
    if len(lookup) != math.prod(shape):
        raise native.ComparisonFailure("incomplete Cartesian cell lattice")
    return {"shape": shape, "bounds": bounds, "spacing": spacing, "tolerance": tol,
            "lookup": lookup, "centres": centres, "volumes": volumes}


def build_mapping(coarse, fine):
    if fine["shape"] != [2 * n for n in coarse["shape"]]:
        raise native.ReviewRequired("only native 2x refinement in all three axes is supported")
    tol = max(coarse["tolerance"], fine["tolerance"])
    if any(abs(a - b) > tol for ca, fa in zip(coarse["bounds"], fine["bounds"]) for a, b in zip(ca, fa)):
        raise native.ComparisonFailure("mesh bounds differ; no common-cell mapping")
    groups = [None] * len(coarse["centres"])
    for key, cell in coarse["lookup"].items():
        children = [fine["lookup"][tuple(2 * k + d for k, d in zip(key, offset))]
                    for offset in itertools.product((0, 1), repeat=3)]
        total = math.fsum(fine["volumes"][j] for j in children)
        if not math.isclose(total, coarse["volumes"][cell], rel_tol=1e-10):
            raise native.ComparisonFailure("eight native child volumes do not equal parent volume")
        for axis in range(3):
            mean = math.fsum(fine["centres"][j][axis] * fine["volumes"][j] for j in children) / total
            if abs(mean - coarse["centres"][cell][axis]) > tol:
                raise native.ComparisonFailure("child centroid does not match native parent centre")
        groups[cell] = children
    # Each lattice key occurs exactly once, so groups partition all fine cells.
    return groups


def restrict(values, groups, fine_volumes, coarse_volumes, components=1):
    return [math.fsum(values[j * components + k] * fine_volumes[j] for j in children) / coarse_volumes[i]
            for i, children in enumerate(groups) for k in range(components)]


def norms(a, b, volumes, components=1, selected=None):
    selected = range(len(volumes)) if selected is None else selected
    errors, refs, weights = [], [], []
    for i in selected:
        errors.append(math.sqrt(math.fsum((b[i * components + k] - a[i * components + k]) ** 2
                                         for k in range(components))))
        refs.append(math.sqrt(math.fsum(a[i * components + k] ** 2 for k in range(components))))
        weights.append(volumes[i])
    if not weights:
        return {"cells": 0, "volume_m3": 0, "L1": None, "L2": None, "Linf": None,
                "relative_L1": None, "relative_L2": None, "relative_Linf": None}
    volume = math.fsum(weights)
    l1 = math.fsum(e * v for e, v in zip(errors, weights)) / volume
    l2 = math.sqrt(math.fsum(e * e * v for e, v in zip(errors, weights)) / volume)
    r1 = math.fsum(r * v for r, v in zip(refs, weights)) / volume
    r2 = math.sqrt(math.fsum(r * r * v for r, v in zip(refs, weights)) / volume)
    ratio = lambda e, r: e / r if r else (0.0 if not e else None)
    return {"cells": len(weights), "volume_m3": volume, "L1": l1, "L2": l2, "Linf": max(errors),
            "relative_L1": ratio(l1, r1), "relative_L2": ratio(l2, r2),
            "relative_Linf": ratio(max(errors), max(refs))}


def y_layers(grid, fields, case_id, time_s):
    rows = []
    nx, ny, nz = grid["shape"]
    for y in range(ny):
        cells = [grid["lookup"][(x, y, z)] for x in range(nx) for z in range(nz)]
        volumes = [grid["volumes"][i] for i in cells]
        volume = math.fsum(volumes)
        alpha = fields["alpha.metal"]
        metal = [i for i in cells if alpha[i] > 0.5]
        row = {"case": case_id, "time_s": time_s, "y_layer": y,
               "y_centre_m": grid["bounds"][1][0] + (y + 0.5) * grid["spacing"][1],
               "y_lower_m": grid["bounds"][1][0] + y * grid["spacing"][1],
               "cells": len(cells), "metal_dominated_cells": len(metal),
               "alpha_min": min(alpha[i] for i in cells), "alpha_max": max(alpha[i] for i in cells),
               "alpha_volume_mean": math.fsum(alpha[i] * grid["volumes"][i] for i in cells) / volume,
               "metal_volume_m3": math.fsum(alpha[i] * grid["volumes"][i] for i in cells)}
        for name in ("T", "epsilon1", "Deposition"):
            row[name + "_volume_mean"] = (math.fsum(fields[name][i] * grid["volumes"][i] for i in cells) / volume
                                              if name in fields else None)
            row[name + "_metal_max"] = max((fields[name][i] for i in metal), default=None) if name in fields else None
        rows.append(row)
    return rows


def initial_surface(grid, alpha):
    nx, ny, nz = grid["shape"]
    surfaces, contiguous = [], True
    pure = all(abs(a) <= 1e-12 or abs(a - 1) <= 1e-12 for a in alpha)
    for x in range(nx):
        for z in range(nz):
            occupied = [y for y in range(ny) if alpha[grid["lookup"][(x, y, z)]] > 0.5]
            if not occupied:
                contiguous = False
                continue
            contiguous &= occupied == list(range(occupied[0], ny))
            surfaces.append(grid["bounds"][1][0] + occupied[0] * grid["spacing"][1])
    planar = pure and contiguous and len(surfaces) == nx * nz and max(surfaces) - min(surfaces) <= grid["tolerance"]
    return {"definition": "Lower native cell face of first alpha>0.5 cell in each x-z column; not a reconstructed iso-surface",
            "planar_binary_step": planar, "columns": nx * nz, "occupied_columns": len(surfaces),
            "metal_dominated_y_layers": len({grid["centres"][i][1] for i, a in enumerate(alpha) if a > 0.5}),
            "surface_y_range_m": [min(surfaces), max(surfaces)] if surfaces else None,
            "effective_surface_y_m": math.fsum(surfaces) / len(surfaces) if planar else None,
            "discrete_metal_thickness_m": grid["bounds"][1][1] - math.fsum(surfaces) / len(surfaces) if planar else None,
            "metal_volume_m3": math.fsum(a * v for a, v in zip(alpha, grid["volumes"]))}


def field_metrics(grid, fields, initial_volume):
    alpha, temperature, epsilon, q = (fields[n] for n in ("alpha.metal", "T", "epsilon1", "Deposition"))
    volumes, centres = grid["volumes"], grid["centres"]
    metal = [i for i, a in enumerate(alpha) if a > 0.5]
    if not metal:
        raise native.ReviewRequired("no metal-dominated cells for requested diagnostics")
    liquid = [i for i in metal if epsilon[i] > 0.5]
    metal_volume = math.fsum(a * v for a, v in zip(alpha, volumes))
    positive = [max(x, 0.0) * v for x, v in zip(q, volumes)]
    power = math.fsum(positive)
    square = math.fsum(max(x, 0.0) ** 2 * v for x, v in zip(q, volumes))
    ranked = sorted(range(len(q)), key=lambda i: q[i], reverse=True)
    top = max(1, math.ceil(0.01 * len(q)))
    threshold_centres = [centres[i] for i in liquid]
    alpha_t = math.fsum(a * t * v for a, t, v in zip(alpha, temperature, volumes))
    q_peak_cell = max(range(len(q)), key=q.__getitem__)
    q_centre = [math.fsum(p * point[a] for p, point in zip(positive, centres)) / power for a in range(3)] if power else None
    result = {"T_max_K": max(temperature), "metal_T_max_K": max(temperature[i] for i in metal),
        "metal_T_mask_volume_mean_K": math.fsum(temperature[i] * volumes[i] for i in metal) / math.fsum(volumes[i] for i in metal),
        "metal_T_alpha_weighted_mean_K": alpha_t / metal_volume if metal_volume else None,
        "metal_volume_m3": metal_volume, "metal_volume_relative_change": (metal_volume - initial_volume) / initial_volume,
        "liquid_metal_volume_m3": math.fsum(a * e * v for a, e, v in zip(alpha, epsilon, volumes)),
        "metal_speed_max_m_s": max(math.sqrt(sum(x * x for x in fields["U"][3*i:3*i+3])) for i in metal),
        "metal_epsilon_max": max(epsilon[i] for i in metal), "alpha_min": min(alpha), "alpha_max": max(alpha),
        "epsilon_min": min(epsilon), "epsilon_max": max(epsilon),
        "mixed_cells_0_1": sum(0 < a < 1 for a in alpha), "mixed_cells_001_099": sum(0.01 < a < 0.99 for a in alpha),
        "threshold_melt_cells": len(liquid), "threshold_melt_y_layers": len({p[1] for p in threshold_centres}),
        "threshold_melt_centre_bounds_m": [[min(p[a] for p in threshold_centres), max(p[a] for p in threshold_centres)]
                                            for a in range(3)] if liquid else None,
        "threshold_melt_cell_edge_bounds_m": [[min(p[a] for p in threshold_centres) - grid["spacing"][a]/2,
                                               max(p[a] for p in threshold_centres) + grid["spacing"][a]/2]
                                              for a in range(3)] if liquid else None,
        "deposition_signed_integral_W": math.fsum(x * v for x, v in zip(q, volumes)),
        "deposition_positive_integral_W": power,
        "deposition_negative_integral_W": math.fsum(min(x, 0.0) * v for x, v in zip(q, volumes)),
        "deposition_peak_W_m3": max(q), "deposition_positive_effective_volume_m3": power * power / square if square else None,
        "deposition_first_peak_centre_m": centres[q_peak_cell], "deposition_peak_cells": sum(x == q[q_peak_cell] for x in q),
        "deposition_top_1pct_cells_power_fraction": math.fsum(positive[i] for i in ranked[:top]) / power if power else None,
        "deposition_positive_centroid_m": q_centre,
        "deposition_positive_rms_extent_m": [math.sqrt(math.fsum(p * (point[a] - q_centre[a]) ** 2
            for p, point in zip(positive, centres)) / power) for a in range(3)] if power else None}
    return result


def dictionary(source, relative, case_paths=False):
    text = source.file(relative).read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)
    if case_paths:
        # Only this literal prefix is understood; never expand environment vars.
        text = text.replace("$FOAM_CASE/constant/", "constant/")
    if any(c in text for c in ("$", "#", "\\")):
        raise native.ReviewRequired(str(relative) + ": unsupported dictionary directive/substitution")
    parser = native.Parser(text)
    if parser.header()["class"] != ["dictionary"]:
        raise native.ReviewRequired(str(relative) + ": unsupported input dictionary class")
    data = parser.dictionary()
    parser.done()
    return data


def input_geometry(source):
    data = dictionary(source, "system/setFieldsDict")
    boxes = []
    regions = data.get("regions", [[]])[0]
    if not isinstance(regions, list) or len(regions) % 2:
        raise native.ReviewRequired("unsupported setFields regions structure")
    for kind, entry in zip(regions[::2], regions[1::2]):
        if kind != "boxToCell" or not isinstance(entry, dict):
            raise native.ReviewRequired("only explicit boxToCell initialization is diagnosed")
        box = entry.get("box")
        if not isinstance(box, list) or len(box) != 2 or any(not isinstance(p, list) or len(p) != 3 for p in box):
            raise native.ReviewRequired("unsupported boxToCell bounds")
        box = [[native.finite_number(x) for x in p] for p in box]
        if any(a > b for a, b in zip(*box)):
            raise native.ComparisonFailure("inverted boxToCell bounds")
        boxes.append({"kind": kind, "box_m": box, "fieldValues_tokens": entry.get("fieldValues")})
    return {"defaultFieldValues_tokens": data.get("defaultFieldValues"), "regions": boxes}


def box_selection_audit(grid, alpha, initialization):
    """Test the centre-selection hypothesis against raw alpha; never edit it."""
    regions = initialization["regions"]
    if (initialization["defaultFieldValues_tokens"] != [["volScalarFieldValue", "alpha.metal", "0"]]
            or len(regions) != 1 or regions[0]["fieldValues_tokens"] != [["volScalarFieldValue", "alpha.metal", "1"]]):
        return {"status": "NOT_SUPPORTED", "note": "Only the original single binary alpha box is audited"}
    low, high = regions[0]["box_m"]
    expected = [int(all(lo <= x <= hi for x, lo, hi in zip(centre, low, high))) for centre in grid["centres"]]
    errors = [abs(a - b) for a, b in zip(alpha, expected)]
    return {"status": "DIAGNOSTIC_COMPUTED", "hypothesis": "Select native cell centre inside the input box",
        "box_lower_y_m": low[1], "predicted_metal_cells": sum(expected),
        "predicted_metal_volume_m3": math.fsum(a * v for a, v in zip(expected, grid["volumes"])),
        "raw_alpha_matches_centre_selection": max(errors) <= 1e-12,
        "mismatch_cells": sum(e > 1e-12 for e in errors), "max_abs_alpha_difference": max(errors),
        "note": "Audit only; not a correction, normalization or verification of the executed setFields binary"}


def laser_inputs(source):
    data = dictionary(source, "constant/LaserProperties", case_paths=True)
    entries = data.get("lasers", [[]])[0]
    if not isinstance(entries, list) or not entries or len(entries) % 2:
        raise native.ReviewRequired("unsupported lasers dictionary list")
    lasers = []
    for name, entry in zip(entries[::2], entries[1::2]):
        if any(key.startswith("HS_osc") for key in entry):
            raise native.ReviewRequired("oscillating laser trajectory requires a separate diagnostic extractor")
        direction = [native.finite_number(x) for x in entry["V_incident"][0]]
        if len(direction) != 3 or not math.hypot(*direction):
            raise native.ComparisonFailure("invalid laser incident direction")
        direction = [x / math.hypot(*direction) for x in direction]
        table = entry["timeVsLaserPosition"]
        if table.get("outOfBounds") != ["clamp"]:
            raise native.ReviewRequired("only clamped linear laser tables are supported")
        if set(table) - {"file", "outOfBounds"}:
            raise native.ReviewRequired("unsupported laser position interpolation options")
        relative = table["file"][0].strip('"')
        if not re.fullmatch(r"constant/[A-Za-z0-9_.-]+", relative):
            raise native.ComparisonFailure("unsafe laser table path")
        parser = native.Parser(native.read_ascii(source.file(relative)))
        rows = parser.item()
        parser.done()
        samples = []
        for row in rows:
            if len(row) != 2 or len(row[1]) != 3:
                raise native.ReviewRequired("unsupported laser position table row")
            samples.append([native.finite_number(row[0]), [native.finite_number(x) for x in row[1]]])
        if not samples or any(b[0] <= a[0] for a, b in zip(samples, samples[1:])):
            raise native.ComparisonFailure("non-monotone/empty laser position table")
        lasers.append({"name": name, "direction": direction, "radius_m": native.finite_number(entry["laserRadius"][0]),
                       "table": samples, "table_source": relative})
    return lasers


def laser_position(laser, t):
    samples = laser["table"]
    index = bisect.bisect_right([r[0] for r in samples], t)
    if index == 0:
        return samples[0][1]
    if index == len(samples):
        return samples[-1][1]
    a, b = samples[index - 1], samples[index]
    weight = (t - a[0]) / (b[0] - a[0])
    return [x + weight * (y - x) for x, y in zip(a[1], b[1])]


def laser_profiles(grid, lasers, surface, fields, case_id, t):
    geometry_rows, profile_rows = [], []
    for laser in lasers:
        position = laser_position(laser, t)
        face = surface["effective_surface_y_m"]
        distance = (face - position[1]) / laser["direction"][1] if face is not None and laser["direction"][1] else None
        target = [position[a] + distance * laser["direction"][a] for a in range(3)] if distance is not None else position
        x, z = [min(range(grid["shape"][a]), key=lambda i: abs(
            grid["bounds"][a][0] + (i + 0.5) * grid["spacing"][a] - target[a])) for a in (0, 2)]
        xc, zc = [grid["bounds"][a][0] + (i + 0.5) * grid["spacing"][a] for a, i in ((0, x), (2, z))]
        geometry_rows.append({"case": case_id, "time_s": t, "laser": laser["name"],
            "launch_x_m": position[0], "launch_y_m": position[1], "launch_z_m": position[2],
            "incident_x": laser["direction"][0], "incident_y": laser["direction"][1], "incident_z": laser["direction"][2],
            "radius_m": laser["radius_m"], "initial_surface_y_m": face,
            "forward_distance_to_initial_plane_m": distance,
            "initial_plane_intersection_forward": distance is not None and distance >= 0,
            "target_within_xz_bounds": all(grid["bounds"][a][0] <= target[a] <= grid["bounds"][a][1] for a in (0, 2)),
            "sample_column_x_m": xc, "sample_column_z_m": zc,
            "sample_offset_x_m": xc - target[0], "sample_offset_z_m": zc - target[2]})
        for y in range(grid["shape"][1]):
            cell = grid["lookup"][(x, y, z)]
            yc = grid["centres"][cell][1]
            profile_rows.append({"case": case_id, "time_s": t, "laser": laser["name"], "y_centre_m": yc,
                "y_minus_initial_surface_m": yc - face if face is not None else None,
                "x_m": xc, "z_m": zc, **{name: fields[name][cell] if name in fields else None
                                         for name in ("T", "alpha.metal", "epsilon1", "Deposition")}})
    return geometry_rows, profile_rows


def load_case(path, label, *, manifest_reader=None):
    source = Source(path, label)
    source.file("manifest.json")
    manifest = (manifest_reader or checks.manifest)(source.path)
    if manifest["experiment_id"] != label:
        raise native.ComparisonFailure(label + ": incorrect experiment identity")
    for key in ("project_commit", "build_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", manifest[key]):
            raise native.ComparisonFailure(label + ": invalid original " + key)
    for name in ("inputs.sha256", "initialized.sha256", "m.json"):
        source.file(name)
    try:
        check_inputs(source.path)
    except ValueError as exc:
        raise native.ComparisonFailure(label + ": " + str(exc)) from exc
    previous = json.loads((source.path / "m.json").read_text(encoding="utf-8"))
    if previous.get("status") != checks.PASSED:
        raise native.ComparisonFailure(label + ": existing full exploration report is not PASS")
    if any(previous.get(k) != manifest[k] for k in ("project_commit", "build_commit")):
        raise native.ComparisonFailure(label + ": full report provenance differs from manifest")
    for name in ("points", "faces", "owner", "neighbour", "boundary"):
        source.file("constant/polyMesh/" + name)
    geometry, volumes, centres, summary = checks.mesh_metrics(source.path, manifest["config"])
    grid = lattice(centres, volumes, summary, manifest["config"]["cells"])
    times = {}
    for directory in source.path.iterdir():
        if native.NUMBER.fullmatch(directory.name) and Decimal(directory.name) > 0:
            t = Decimal(directory.name)
            if not directory.is_dir() or t in times:
                raise native.ComparisonFailure(label + ": duplicate/invalid output time")
            times[t] = directory.name
    c = manifest["config"]
    expected = {Decimal(c["delta_t"]) * i for i in range(c["write_interval"], c["steps"] + 1, c["write_interval"])}
    if set(times) != expected:
        raise native.ComparisonFailure(label + ": incomplete/unexpected output times")
    initial = {name: read_volume(source, "0/" + name, geometry, name, initial=True) for name in ("T", "alpha.metal")}
    surface = initial_surface(grid, initial["alpha.metal"])
    if surface["metal_volume_m3"] <= 0:
        raise native.ComparisonFailure(label + ": nonpositive initial metal volume")
    source.file("solver.exit.txt")
    source.file("log.laserbeamFoam")
    log = checks.parse_log(source.path, c)
    if log["solver_alerts"]:
        raise native.ReviewRequired(label + ": native log has solver alerts")
    execution_blocks, previous_cpu, previous_clock = [], 0.0, 0.0
    for start in range(0, len(log["execution"]), 100):
        block = log["execution"][start:start + 100]
        last = block[-1]
        execution_blocks.append({"first_step": block[0]["step"], "last_step": last["step"],
            "end_time_s": last["time_s"], "execution_cpu_seconds_per_step": (last["execution_cpu_s"] - previous_cpu) / len(block),
            "reported_clock_seconds_per_step": (last["clock_s"] - previous_clock) / len(block)})
        previous_cpu, previous_clock = last["execution_cpu_s"], last["clock_s"]
    resource = {}
    for name in ("solver.time.txt", "time.workflow.mesh.txt", "time.workflow.solve.txt"):
        resource[name] = gnu_time_record(source.file(name))
        if resource[name]["status"] != "RECORDED":
            raise native.ReviewRequired(label + ": missing wall/RSS in " + name)
    resource["previous_report_offline_seconds"] = previous.get("offline_check_wall_seconds")
    resource["previous_report_case_bytes"] = previous.get("resources", {}).get("data_bytes")
    resource["current_case_bytes_before_comparison"] = source.case_bytes
    preparation = source.file("preparation.time.txt").read_text().strip().split("=", 1)
    if len(preparation) != 2 or preparation[0] != "preparation_wall_seconds":
        raise native.ReviewRequired(label + ": unsupported preparation time record")
    prep = native.finite_number(preparation[1])
    if prep < 0:
        raise native.ComparisonFailure(label + ": negative preparation time")
    resource["recorded_workflow_seconds"] = prep + sum(resource["time.workflow." + stage + ".txt"]["wall_seconds"]
                                                       for stage in ("mesh", "solve"))
    resource["recorded_workflow_scope"] = "Preparation body plus mesh/solve wrappers, excluding final explicit offline comparison, build, Git and operator waiting"
    return {"source": source, "manifest": manifest, "geometry": geometry, "mesh": summary, "grid": grid,
            "times": times, "initial": initial, "surface": surface, "initialization_input": input_geometry(source),
            "lasers": laser_inputs(source), "log": {"steps": len(log["times"]), "diagnostic_events": len(log["events"]),
            "linear_summaries": log["linear_summaries"], "solver_alerts": log["solver_alerts"],
            "logged_lasers": log["path_evidence"]["logged_lasers"],
            "ray_seed_records": len(log["path_evidence"]["seed_counts"]),
            "distinct_logged_seed_counts": sorted({tuple(row) for row in log["path_evidence"]["seed_counts"]}),
            "execution_blocks_100_steps": execution_blocks,
            "execution_note": "Native cumulative CPU/reported ClockTime differences, not module times or GNU wall"}, "resources": resource}


def compare_cases(m1, m3, report, requested_times=None):
    sources, cases = [], []
    report["source_records"] = {}
    for path, label in ((m1, "M1"), (m3, "M3")):
        print("Reading native geometry and logs: " + label, flush=True)
        try:
            case = load_case(path, label)
        except (native.ComparisonFailure, native.ReviewRequired) as exc:
            raise type(exc)(label + ": " + str(exc)) from exc
        except (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError) as exc:
            raise native.ReviewRequired(label + ": " + str(exc)) from exc
        cases.append(case)
        sources.append(case["source"])
        report["source_records"][label] = {"original_run_commit": case["manifest"]["project_commit"],
            "original_build_commit": case["manifest"]["build_commit"], "existing_full_check_status": checks.PASSED,
            "full_check_scope": "Existing report, not independently rerun for every field by this tool",
            "mesh": case["mesh"], "log": case["log"], "resources": case["resources"],
            "initialization_input": case["initialization_input"], "lasers": case["lasers"]}
    coarse, fine = cases
    if set(coarse["times"]) != set(fine["times"]):
        raise native.ComparisonFailure("M1/M3 output time sets differ")
    for key in ("delta_t", "end_time", "steps", "write_interval"):
        if coarse["manifest"]["config"][key] != fine["manifest"]["config"][key]:
            raise native.ComparisonFailure("time configuration differs: " + key)
    prepared = []
    for c in cases:
        prepared.append({line.split("  ", 1)[1]: line.split("  ", 1)[0]
                         for line in c["source"].file("inputs.sha256").read_text().splitlines()})
    differences = [{"path": name, "M1_sha256": prepared[0].get(name), "M3_sha256": prepared[1].get(name)}
                   for name in sorted(set(prepared[0]) | set(prepared[1])) if prepared[0].get(name) != prepared[1].get(name)]
    report["prepared_input_differences"] = differences
    unexpected = [item["path"] for item in differences if item["path"] != "system/blockMeshDict"]
    if unexpected:
        report["status"] = "REVIEW_REQUIRED"
        report["issues"].append({"status": "REVIEW_REQUIRED", "message": "Prepared inputs differ beyond grid: " + ", ".join(unexpected)})
    groups = build_mapping(coarse["grid"], fine["grid"])
    vc, vf = coarse["grid"]["volumes"], fine["grid"]["volumes"]
    report["mapping"] = {"status": "NATIVE_COORDINATES_VOLUMES_VERIFIED", "fine_children_per_coarse_cell": 8,
                         "coarse_cells": len(vc), "fine_cells": len(vf), "method": "Volume-weighted restriction; no interpolation"}
    times = sorted(coarse["times"]) if requested_times is None else sorted(set(Decimal(t) for t in requested_times))
    if not times or any(not t.is_finite() or t not in coarse["times"] for t in times):
        raise native.ComparisonFailure("requested times must be existing common output times")
    report["selected_fields"] = list(FIELDS)
    report["selected_field_dimensions"] = DIMS
    report["times_s"] = [float(t) for t in times]
    report["initial"] = {c["source"].label: c["surface"] for c in cases}
    for case in cases:
        report["initial"][case["source"].label]["box_selection_audit"] = box_selection_audit(
            case["grid"], case["initial"]["alpha.metal"], case["initialization_input"])
    ac, af = coarse["initial"]["alpha.metal"], fine["initial"]["alpha.metal"]
    report["initial"]["mapped_alpha_difference"] = norms(ac, restrict(af, groups, vf, vc), vc)
    report["initial"]["mapped_T_difference"] = norms(coarse["initial"]["T"], restrict(fine["initial"]["T"], groups, vf, vc), vc)
    report["initial"]["metal_volume_relative_difference_M3_vs_M1"] = (fine["surface"]["metal_volume_m3"] / coarse["surface"]["metal_volume_m3"] - 1)
    report["resource_comparison"] = {"solver_wall_ratio_M3_over_M1": fine["resources"]["solver.time.txt"]["wall_seconds"] /
        coarse["resources"]["solver.time.txt"]["wall_seconds"] if coarse["resources"]["solver.time.txt"]["wall_seconds"] else None,
        "note": "Different spatial workloads; not a speedup or a module hotspot attribution"}
    report["profiles"], report["laser_geometry"], report["laser_profiles"] = [], [], []
    report["metrics"], report["mapped_differences"] = [], {}
    for c in cases:
        label = c["source"].label
        report["profiles"].extend(y_layers(c["grid"], c["initial"], label, 0))
        geometry, profiles = laser_profiles(c["grid"], c["lasers"], c["surface"], c["initial"], label, 0)
        report["laser_geometry"].extend(geometry)
        report["laser_profiles"].extend(profiles)
    for t in times:
        print("Comparing selected native fields at time " + str(t), flush=True)
        fields = []
        for c in cases:
            values = {name: read_volume(c["source"], c["times"][t] + "/" + name, c["geometry"], name) for name in FIELDS}
            fields.append(values)
            report["metrics"].append({"case": c["source"].label, "time_s": float(t),
                **field_metrics(c["grid"], values, c["surface"]["metal_volume_m3"])})
            report["profiles"].extend(y_layers(c["grid"], values, c["source"].label, float(t)))
            geometry, profiles = laser_profiles(c["grid"], c["lasers"], c["surface"], values, c["source"].label, float(t))
            report["laser_geometry"].extend(geometry)
            report["laser_profiles"].extend(profiles)
        a, b = fields
        mapped = {name: restrict(b[name], groups, vf, vc, 3 if name == "U" else 1) for name in FIELDS}
        differences = {name: norms(a[name], mapped[name], vc, 3 if name == "U" else 1) for name in FIELDS}
        product_a = [x * y for x, y in zip(a["alpha.metal"], a["epsilon1"])]
        product_b = [x * y for x, y in zip(b["alpha.metal"], b["epsilon1"])]
        differences["alpha_times_epsilon1"] = norms(product_a, restrict(product_b, groups, vf, vc), vc)
        differences["restricted_M3_summary"] = {
            "deposition_peak_W_m3": max(mapped["Deposition"]),
            "deposition_integral_W": math.fsum(q * v for q, v in zip(mapped["Deposition"], vc)),
            "liquid_volume_m3": math.fsum(q * v for q, v in zip(restrict(product_b, groups, vf, vc), vc)),
            "metal_volume_m3": math.fsum(q * v for q, v in zip(mapped["alpha.metal"], vc))}
        common_metal = [i for i, x in enumerate(a["alpha.metal"]) if x > 0.5 and mapped["alpha.metal"][i] > 0.5]
        numerator = restrict([x * y for x, y in zip(b["alpha.metal"], b["T"])], groups, vf, vc)
        metal_temperature = [n / weight if weight > 0 else 0.0 for n, weight in zip(numerator, mapped["alpha.metal"])]
        differences["T_common_metal_alpha_weighted_restriction"] = norms(a["T"], metal_temperature, vc, selected=common_metal)
        common_set = set(common_metal)
        differences["common_metal_coverage"] = {
            "cells": len(common_metal), "geometric_volume_m3": math.fsum(vc[i] for i in common_metal),
            "M1_alpha_volume_outside_common_mask_m3": math.fsum(a["alpha.metal"][i] * vc[i] for i in range(len(vc)) if i not in common_set),
            "restricted_M3_alpha_volume_outside_common_mask_m3": math.fsum(mapped["alpha.metal"][i] * vc[i] for i in range(len(vc)) if i not in common_set),
            "note": "Intersection may exclude differently initialized or mixed parent cells; inspect native peaks and full-domain differences too"}
        report["mapped_differences"][str(t)] = differences
    for source in sources:
        source.unchanged()
    report["consumed_sources_sha256"] = {source.label + "/" + key: value for source in sources for key, value in sorted(source.hashes.items())}
    report["consumed_sources_unchanged_during_comparison"] = True
    report["interpretation"] = {"physical_accuracy": "UNVERIFIED", "grid_convergence": "NOT_ESTABLISHED",
        "initial_interface_discretization_differs": report["initial"]["mapped_alpha_difference"]["Linf"] > 1e-12,
        "interface_difference_flag_note": "Diagnostic comparison using existing alpha 1e-12 roundoff bound; not a new acceptance criterion",
        "geometry_confounder": "Compare initial volume/surface and mapped alpha; no initial field was corrected",
        "early_melting_cause": "NOT_ESTABLISHED; geometry, deposition sampling and spatial discretization remain coupled",
        "multiple_reflections": "NOT_ESTABLISHED", "hotspot": "NOT_ESTABLISHED", "ai_speedup": "NOT_STUDIED"}


def csv_bytes(rows):
    if not rows:
        return b""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, separators=(",", ":")) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    return stream.getvalue().encode()


def publish(out, report, archive_name="m1-m3-comparison-feedback.tar.gz"):
    summary = ("Status: {status}\nScope: cross-grid diagnostics, not equivalence or grid convergence\n"
               "Selected times: {times}; fields: T, alpha.metal, epsilon1, Deposition, U\n"
               "Mapping: {mapping}\nConsumed source hash recheck: {unchanged}\n"
               "Physical accuracy / causal attribution / AI speedup: UNVERIFIED\n").format(
                   status=report["status"], times=len(report.get("times_s", [])),
                   mapping=report.get("mapping", {}).get("status", "NOT_ESTABLISHED"),
                   unchanged=report.get("consumed_sources_unchanged_during_comparison", False))
    for label, initial in report.get("initial", {}).items():
        if label in ("M1", "M3", "M1-IC"):
            summary += "{} initial metal volume={} m3; binary surface y={} m\n".format(
                label, initial["metal_volume_m3"], initial["effective_surface_y_m"])
    summary += "\n".join(issue["status"] + ": " + issue["message"] for issue in report["issues"]) + "\n"
    payload = {"comparison.txt": summary.encode(),
        "comparison.json": (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(),
        "metrics.csv": csv_bytes(report.get("metrics", [])), "profiles_y.csv": csv_bytes(report.get("profiles", [])),
        "laser_geometry.csv": csv_bytes(report.get("laser_geometry", [])),
        "laser_profiles_y.csv": csv_bytes(report.get("laser_profiles", [])),
        "sources.sha256": "".join(h + "  " + name + "\n" for name, h in sorted(report.get("consumed_sources_sha256", {}).items())).encode()}
    payload = {name: redact(data.decode()).encode() for name, data in payload.items()}
    if any(len(data) > 4 * 1024 * 1024 for data in payload.values()) or sum(map(len, payload.values())) > 16 * 1024 * 1024:
        raise ValueError("comparison report exceeds small-feedback limit; retain reports locally, narrow --times")
    payload["FILES.txt"] = ("\n".join(sorted(set(payload) | {"FILES.txt", "SHA256SUMS"})) + "\n").encode()
    payload["SHA256SUMS"] = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                                      for name, data in sorted(payload.items())).encode()
    for name, data in payload.items():
        with (out / name).open("xb") as stream:
            stream.write(data)
    archive_path = out / archive_name
    with archive_path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, data in sorted(payload.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode = len(data), 0o600
            archive.addfile(item, io.BytesIO(data))
    if archive_path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("compressed diagnostic feedback exceeds 8 MiB")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        if {m.name for m in members} != set(payload) or len(members) != len(payload):
            raise ValueError("archive member inventory mismatch")
        for item in members:
            if not item.isfile() or archive.extractfile(item).read() != payload[item.name]:
                raise ValueError("archive readback mismatch")
    checksum = digest(archive_path)
    (out / (archive_path.name + ".sha256")).write_text(checksum + "  " + archive_path.name + "\n", encoding="ascii")
    print(summary, end="")
    print("Archive:", archive_path)
    print("Archive status: EXPORTED; generated report readback and SHA256 verified; no raw fields included")
    print("SHA256:", checksum)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-case-dir", required=True, type=Path)
    parser.add_argument("--m3-case-dir", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--times", nargs="+", help="Optional common output times, e.g. 1e-6 2e-6 3e-6")
    args = parser.parse_args(argv)
    out = args.report_dir.absolute()
    try:
        if any(p.is_symlink() for p in (out, *out.parents)) or not out.resolve().is_relative_to((REPO / "validation").resolve()):
            raise ValueError("new report directory must be below this checkout/validation without symlinks")
        for case in (args.m1_case_dir, args.m3_case_dir):
            source = Path(case).absolute().resolve()
            if out.resolve().is_relative_to(source) or source.is_relative_to(out.resolve()):
                raise ValueError("report directory must be disjoint from both source cases")
        out.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as exc:
        print("ERROR [report-directory] " + str(exc), file=sys.stderr)
        return 2
    started = time.perf_counter()
    report = {"schema": "m1-m3-spatial-diagnostics-v1", "status": "COMPARISON_COMPLETED", "issues": [],
        "definitions": {"T_restriction": "Volume mean, not mass/energy/enthalpy conservation",
            "metal_T_mean": "sum(alpha*T*V)/sum(alpha*V), no density, heat capacity or latent heat",
            "common_metal_T": "Coarse alpha>0.5 AND restricted fine alpha>0.5; fine sum(alpha*T*V)/sum(alpha*V)",
            "liquid_volume": "sum(alpha*epsilon1*V); restrict the product, not product of restricted factors",
            "norms": "d=fine restricted minus coarse; L1=sum(V*|d|)/sum(V), L2=sqrt(sum(V*|d|^2)/sum(V)), Linf=max|d|; vector Euclidean magnitude",
            "relative_norms": "Divide by matching coarse norm; zero reference with nonzero difference is null",
            "deposition": "Signed integral=sum(Q*V). Concentration uses max(Q,0); negative integral reported separately",
            "threshold_melt": "alpha>0.5 AND epsilon1>0.5; centre/occupied-cell extent is not experimental melt dimension",
            "profile": "Native y-layer averages plus nearest nominal laser-axis x-z columns; no interpolation, sampling offsets recorded",
            "source_hash_window": "Each consumed file hashed just before first diagnostic read and again after analysis, not historical authentication or coverage of unread fields",
            "scope": "Selected native volume fields and boundaries only; not replacement for full M exploration checks"}}
    try:
        report["comparison_tool_source_sha256"] = digest(Path(__file__))
        report["comparison_python_version"] = sys.version.split()[0]
        report["tool_sources_sha256"] = {name: digest(Path(__file__).resolve().parent / name) for name in (
            "compare_m1_m3.py", "check_m_case.py", "compare_plate2d_ab.py", "check_smoke_case.py", "export_smoke_feedback.py")}
        report["comparison_tool_commit"] = subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE).strip()
        compare_cases(args.m1_case_dir, args.m3_case_dir, report, args.times)
    except (native.ComparisonFailure, native.ReviewRequired, OSError, ValueError, TypeError, KeyError,
            IndexError, ArithmeticError, subprocess.CalledProcessError) as exc:
        report["status"] = "FAIL" if isinstance(exc, native.ComparisonFailure) else "REVIEW_REQUIRED"
        report["issues"].append({"status": report["status"], "message": redact(str(exc))})
    report["comparison_wall_seconds"] = time.perf_counter() - started
    report["comparison_timing_scope"] = "Native input/mesh/selected field/log parsing and consumed-source hash recheck; excludes reports and archive publication"
    try:
        publish(out, report)
    except (OSError, ValueError, tarfile.TarError) as exc:
        print("ERROR [feedback] " + str(exc), file=sys.stderr)
        return 2
    return CODE[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
