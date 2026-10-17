#!/usr/bin/env python3
"""One-time 1-us M1/M3/M1-IC read-only audit; never invoke OpenFOAM."""
import argparse
import csv
import gc
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import signal
import subprocess
import time

import check_m_case as checks
import compare_m1_m3 as spatial
import compare_plate2d_ab as native

REPO = Path(__file__).resolve().parents[1]
SOURCE = (
    "applications/solvers/laserbeamFoam/laserbeamFoam.C",
    "applications/solvers/laserbeamFoam/updateProps.H",
    "applications/solvers/laserbeamFoam/createFields.H",
    "applications/solvers/laserbeamFoam/pEqn.H",
    "src/laserHeatSource/laserHeatSource.C",
    "src/laserHeatSource/laserRayParticle.C",
)
FIELDS = ("alpha.metal", "alpha_filtered", "rayQ", "Deposition")


class MeshTokenStream(native.Parser):
    """Reuse the existing grammar, retaining one mesh token instead of millions."""
    def __init__(self, text):
        self.stream = iter(native.TOKEN.finditer(text))
        self.pending = None

    def peek(self):
        if self.pending is None:
            match = next(self.stream, None)
            self.pending = match.group() if match else None
        return self.pending

    def pop(self):
        value = self.peek()
        if value is None:
            raise native.ReviewRequired("unexpected end of dictionary/list")
        self.pending = None
        return value


def sha(path):
    return spatial.digest(path)


def threshold_stats(values):
    return {"min": min(values), "max": max(values),
            "mean": math.fsum(values) / len(values),
            "min_minus_half": min(values) - 0.5,
            "max_minus_half": max(values) - 0.5,
            "lt_half": sum(x < 0.5 for x in values),
            "eq_half": sum(x == 0.5 for x in values),
            "gt_half": sum(x > 0.5 for x in values)}


def read_scalar(path, geometry, name, initial=False):
    parsed = native.parse_field(path)
    expected = {"alpha.metal": [0]*7, "alpha_filtered": [0]*7,
                "rayQ": [1, 0, -3, 0, 0, 0, 0],
                "Deposition": checks.DEPOSITION_DIMENSIONS}[name]
    if parsed["class"] != "volScalarField" or parsed["dimensions"] != expected:
        raise native.ComparisonFailure("unexpected field class/dimensions")
    patches = dict(geometry["patches"])
    if initial and parsed["boundary"].get("defaultFaces") == {"type": ["empty"]}:
        patches["defaultFaces"] = 0
    if set(patches) != set(parsed["boundary"]):
        raise native.ComparisonFailure("field/native patch set differs")
    for patch, size in patches.items():
        state = parsed["boundary"][patch]
        if not state.get("type"):
            raise native.ComparisonFailure("missing patch type")
        for entry in state.values():
            if isinstance(entry, list) and entry and entry[0] in ("uniform", "nonuniform"):
                native.expand_field(entry, size, 1, "scalar")
    return native.expand_field(parsed["internal"], geometry["cells"], 1, "scalar")


def interior_normals(grid, alpha):
    """Gauss-linear on verified uniform Cartesian interior cells only.

    Equal centre-to-face weights give the centred difference. Boundary cells
    are excluded; this is a saved-field reconstruction, not live event data.
    """
    delta = 1e-8 / (math.fsum(grid["volumes"]) / len(alpha))**(1/3)
    result = {}
    for key, cell in grid["lookup"].items():
        if any(k == 0 or k == grid["shape"][a]-1 for a, k in enumerate(key)):
            continue
        derivatives = []
        for axis in range(3):
            lo, hi = list(key), list(key)
            lo[axis] -= 1
            hi[axis] += 1
            derivatives.append((alpha[grid["lookup"][tuple(hi)]] -
                                alpha[grid["lookup"][tuple(lo)]]) /
                               (2*grid["spacing"][axis]))
        mag = math.sqrt(math.fsum(x*x for x in derivatives))
        result[cell] = mag/(mag+delta)
    return result, delta


def audit_case(case, label, rows):
    manifest = json.loads((case/"manifest.json").read_text())
    shape = manifest["config"]["cells"]
    original = native.Parser
    native.Parser = MeshTokenStream
    try:
        geometry, volumes, centres, mesh = checks.mesh_metrics(case, {"cells": shape})
    finally:
        native.Parser = original
    grid = spatial.lattice(centres, volumes, mesh, shape)
    values = {name: read_scalar(case/"1e-06"/name, geometry, name) for name in FIELDS}
    initial = read_scalar(case/"0/alpha.metal", geometry, "alpha.metal", True)
    schemes = native.read_ascii(case/"system/fvSchemes")
    grad = re.search(r"gradSchemes\s*\{([^{}]*)\}", schemes)
    grad_ok = bool(grad and re.fullmatch(r"\s*default\s+Gauss\s+linear\s*;\s*", grad[1]))
    if not grad_ok:
        raise native.ReviewRequired("gradient reconstruction only supports default Gauss linear")
    normals, delta = interior_normals(grid, values["alpha_filtered"])
    layers = [[] for _ in range(shape[1])]
    for key, cell in grid["lookup"].items():
        layers[key[1]].append(cell)
    for j, cells in enumerate(layers):
        af = threshold_stats([values["alpha_filtered"][i] for i in cells])
        a = threshold_stats([values["alpha.metal"][i] for i in cells])
        dep = [values["Deposition"][i] for i in cells]
        rq = [values["rayQ"][i] for i in cells]
        ns = [normals[i] for i in cells if i in normals]
        power = math.fsum(max(values["Deposition"][i], 0)*volumes[i] for i in cells)
        rows.append(dict(case=label, layer=j, cells=len(cells),
            y_um=math.fsum(centres[i][1] for i in cells)/len(cells)*1e6,
            initial_alpha_min=min(initial[i] for i in cells),
            initial_alpha_max=max(initial[i] for i in cells),
            alpha_min=a["min"], alpha_max=a["max"],
            alpha_filtered_min=af["min"], alpha_filtered_max=af["max"],
            alpha_filtered_min_minus_half=af["min_minus_half"],
            alpha_filtered_max_minus_half=af["max_minus_half"],
            alpha_filtered_lt_half=af["lt_half"], alpha_filtered_eq_half=af["eq_half"],
            alpha_filtered_gt_half=af["gt_half"],
            alpha_filtered_alpha_max_abs_diff=max(abs(values["alpha_filtered"][i]-values["alpha.metal"][i]) for i in cells),
            rayQ_positive_cells=sum(x > 0 for x in rq), rayQ_min=min(rq), rayQ_max=max(rq),
            deposition_positive_cells=sum(x > 0 for x in dep), deposition_min=min(dep), deposition_max=max(dep),
            deposition_positive_W=power,
            rayQ_positive_but_alpha_ineligible=sum(values["rayQ"][i] > 0 and values["alpha_filtered"][i] < 0.5 for i in cells),
            normals_interior_cells=len(ns), normal_mag_min=min(ns) if ns else None,
            normal_mag_max=max(ns) if ns else None,
            interior_interface_eligible=sum(i in normals and normals[i] > 0.5 and values["alpha_filtered"][i] >= 0.5 for i in cells)))
    dep = values["Deposition"]
    positive = [i for i, x in enumerate(dep) if x > 0]
    power = math.fsum(dep[i]*volumes[i] for i in positive)
    vtk = []
    for laser in range(5):
        text = (case/f"VTKs/rays_laser{laser}_1e-06.vtk").read_text()
        points = re.search(r"(?m)^POINTS (\d+) ", text)
        lines = re.search(r"(?m)^LINES (\d+) ", text)
        vtk.append({"laser": laser, "points": int(points[1]) if points else None,
                    "lines": int(lines[1]) if lines else None})
    source_hashes = {}
    for name in SOURCE:
        historical = subprocess.check_output(["git", "show", manifest["project_commit"]+":"+name], cwd=REPO)
        source_hashes[name] = {"runtime_sha256": hashlib.sha256(historical).hexdigest(),
                               "matches_audited_checkout": historical == (REPO/name).read_bytes()}
    result = {"run_commit": manifest["project_commit"], "cells": geometry["cells"],
        "mesh": mesh["geometry_status"], "gradient_scheme": "Gauss linear",
        "deltaN_m_inverse": delta, "normal_boundary_cells_excluded": len(dep)-len(normals),
        "positive_deposition_W": power, "peak_deposition_W_m3": max(dep),
        "deposition_y_centroid_um": math.fsum(dep[i]*volumes[i]*centres[i][1] for i in positive)/power*1e6,
        "positive_deposition_cells": len(positive),
        "positive_deposition_below_cutoff_cells": sum(values["alpha_filtered"][i] < 0.5 for i in positive),
        "positive_deposition_without_positive_rayQ": sum(values["rayQ"][i] <= 0 for i in positive),
        "positive_deposition_interior_normal_gt_half": sum(i in normals and normals[i] > 0.5 for i in positive),
        "initial_half_layer_cells": sum(0.49 < x < 0.51 for x in initial),
        "filter_internal_rule_max_abs_error": max(abs(f-(1.0 if a > 0.99 else 0.0 if a < 0.01 else a)) for a, f in zip(values["alpha.metal"], values["alpha_filtered"])),
        "vtk": vtk, "runtime_sources": source_hashes}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source_repo.resolve(strict=True), args.out.resolve()
    if not out.is_relative_to(REPO/"validation") or out.exists() or out.is_relative_to(source):
        raise SystemExit("require fresh current-checkout validation output outside source repo")
    out.mkdir(parents=True)
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    def stop(*_):
        raise TimeoutError("115-second analysis deadline; reserve final hash verification time")
    signal.signal(signal.SIGALRM, stop)
    signal.signal(signal.SIGTERM, stop)
    signal.alarm(115)
    report = {"status": "INCONCLUSIVE", "hypothesis": "IC half layer is below inclusive alpha_filtered>=0.5 optical gate at saved 1us state",
              "time_s": 1e-6, "tool_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip(),
              "cases": {}, "sources_sha256": {}, "source_hashes_unchanged": False,
              "budgets": {"wall_seconds": 120, "rss_bytes": 1024**3, "stronger_virtual_memory_limit_bytes": 1024**3},
              "limitations": ["Internal cells only; normal reconstructed from saved alpha_filtered on verified Cartesian Gauss-linear stencil, not saved/live n_filtered",
                  "rayQ is an accumulated traversal diagnostic, not unique ray events or deposited power; declared dimensions [1,0,-3,0,0,0,0]",
                  "Empty VTK paths cannot establish first-hit positions, branch identity, escapingInterface, Fresnel coefficient or per-ray energy budget",
                  "Single saved time does not establish every previous heat-source call or exclusive explanation of temperature differences"]}
    rows, files = [], {}
    try:
        for label in ("M1", "M1-IC", "M3"):
            case = source/"runs"/f"threeD-{label}-001"
            relatives = ["manifest.json", "system/fvSchemes", "constant/LaserProperties", "0/alpha.metal"]
            relatives += ["constant/polyMesh/"+n for n in ("points", "faces", "owner", "neighbour", "boundary")]
            relatives += ["1e-06/"+n for n in FIELDS]
            relatives += [f"VTKs/rays_laser{i}_1e-06.vtk" for i in range(5)]
            for relative in relatives:
                p = case/relative
                if any(x.is_symlink() for x in (p, *p.parents)) or not p.is_file():
                    raise native.ReviewRequired("missing or linked input: "+label+"/"+relative)
                files[label+"/"+relative] = p
            props = native.read_ascii(case/"constant/LaserProperties")
            if re.search(r"\bdep_cutoff\b", props):
                raise native.ReviewRequired("explicit dep_cutoff requires separate review")
        files.update({"tool/"+n: REPO/n for n in (*SOURCE, "scripts/audit_optical_threshold.py",
                      "scripts/check_m_case.py", "scripts/compare_m1_m3.py", "scripts/compare_plate2d_ab.py")})
        report["sources_sha256"] = {name: sha(p) for name, p in files.items()}
        for label in ("M1", "M1-IC", "M3"):
            report["cases"][label] = audit_case(source/"runs"/f"threeD-{label}-001", label, rows)
            (out/"progress.json").write_text(json.dumps(report, indent=2)+"\n")
            print("Completed read-only 1us audit:", label, flush=True)
            gc.collect()
        half = [r for r in rows if r["case"] == "M1-IC" and 0.49 < r["initial_alpha_min"] and r["initial_alpha_max"] < 0.51]
        if half and all(r["alpha_filtered_lt_half"] == r["cells"] and r["deposition_positive_cells"] == 0 and r["rayQ_positive_cells"] > 0 for r in half):
            report["status"] = "THRESHOLD_HYPOTHESIS_SUPPORTED"
        elif half and all(r["alpha_filtered_lt_half"] == 0 for r in half):
            report["status"] = "NOT_SUPPORTED"
    except (MemoryError, TimeoutError, OSError, ValueError, native.ReviewRequired, native.ComparisonFailure) as exc:
        report["error"] = type(exc).__name__+": "+str(exc)
    finally:
        signal.alarm(0)
        changed = [n for n, h in report["sources_sha256"].items() if sha(files[n]) != h]
        report["source_hashes_unchanged"] = not changed and bool(report["sources_sha256"])
        report["changed_sources"] = changed
        report["wall_seconds_including_final_hashes"] = time.monotonic()-started
        report["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if changed or report["wall_seconds_including_final_hashes"] > 120 or report["max_rss_kib"] > 1048576:
            report["status"] = "INCONCLUSIVE"
        (out/"audit.json").write_text(json.dumps(report, indent=2)+"\n")
        if rows:
            with (out/"layers.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        (out/"sources.private.json").write_text(json.dumps({n: str(p) for n, p in files.items()}, indent=2)+"\n")
    print(report["status"], report["wall_seconds_including_final_hashes"], "s; RSS", report["max_rss_kib"], "KiB", flush=True)
    return 0 if len(report["cases"]) == 3 and report["source_hashes_unchanged"] and "error" not in report else 2


if __name__ == "__main__":
    raise SystemExit(main())
