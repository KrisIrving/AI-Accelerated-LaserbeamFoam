#!/usr/bin/env python3
"""Prepare authorized M exploration copies; never run OpenFOAM or resume CFD."""
import argparse
import hashlib
import json
import math
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import prepare_smoke_case as base

REPO = Path(__file__).resolve().parents[1]
PROFILES = {"M1": ([40, 20, 40], 1000, "1e-5", 100, 1800),
            "M2": ([40, 20, 40], 3000, "3e-5", 300, 2700),
            "M3": ([80, 40, 80], 1000, "1e-5", 100, 3600)}


def config_for(experiment):
    if experiment not in PROFILES:
        raise ValueError("unknown authorized experiment: " + str(experiment))
    config = json.loads((REPO / "benchmarks/threeD-exploration" / (experiment + ".json")).read_text(encoding="utf-8"))
    cells, steps, end, interval, timeout = PROFILES[experiment]
    expected = {"schema": "threeD-exploration-v1", "status": "EXPLORATION_AUTHORIZED",
                "formal_benchmark": "PROPOSED", "id": experiment,
                "source": "tutorials/laserbeamFoam/fiveLasersOnSubstrate",
                "source_commit": "3c93f2657e089e22e9a8298648292969e85a4bad",
                "solver": "laserbeamFoam", "cells": cells, "steps": steps,
                "delta_t": "1e-8", "end_time": end, "write_interval": interval,
                "mesh_timeout_seconds": 180, "solver_timeout_seconds": timeout,
                "max_rss_kib": 8388608, "max_data_bytes": 3221225472,
                "resource_policy": "MONITORED_ONLY"}
    if config != expected:
        raise ValueError("configuration differs from explicitly authorized " + experiment + " profile")
    return config


def below(path, root, description, must_exist=False):
    path = Path(path).absolute()
    if path.is_symlink():
        raise ValueError("symlinked " + description)
    resolved, root = path.resolve(strict=must_exist), root.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(description + " must be below this checkout/" + root.name)
    # No parent symlink can redirect a recorded path, even within the tree.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("symlinked component in " + description)
        if part == root:
            break
    return resolved


def build_record(build_dir):
    build = below(build_dir, REPO / "validation", "isolated build", must_exist=True)
    summary = dict(line.split("=", 1) for line in (build / "summary.txt").read_text(encoding="utf-8").splitlines()
                   if "=" in line)
    commit = base.git("rev-parse", "HEAD").decode().strip()
    if summary.get("project_commit") != commit:
        raise ValueError("build HEAD differs; generate a NEW validate_build.sh record; never edit old records")
    if not summary.get("status", "").startswith("BUILD_ARTIFACT_CHECKS_PASSED;"):
        raise ValueError("build artifact checks have not passed")
    if summary.get("openfoam_version") != "v2512" or not summary.get("WM_OPTIONS"):
        raise ValueError("matching OpenFOAM.com v2512 build configuration missing")
    return build, summary, commit


def nonnegative_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("M1 resource measurement missing/invalid: " + name)
    return value


def refresh_m1(case):
    checked = subprocess.run([sys.executable, str(REPO / "scripts/check_m_case.py"),
                              "--case-dir", str(case)], check=False)
    if checked.returncode:
        raise ValueError("M1 current offline numerical check failed; retain its report and stop")


def conditional_evidence(config, m1_case_dir, reason, refresh=True):
    if config["id"] == "M1":
        if m1_case_dir is not None or reason:
            raise ValueError("M1 does not take a predecessor or conditional reason")
        return None
    if not m1_case_dir or not reason or len(reason.strip()) < 12:
        raise ValueError("M2/M3 require --m1-case-dir and a specific --reason (at least 12 characters)")
    m1 = below(m1_case_dir, REPO / "runs", "M1 case", must_exist=True)
    for name in ("manifest.json", "m.json"):
        if (m1 / name).is_symlink():
            raise ValueError("symlinked M1 evidence: " + name)
    manifest = json.loads((m1 / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("experiment_id") != "M1" or manifest.get("config") != config_for("M1"):
        raise ValueError("conditional predecessor is not the authorized independent M1")
    if refresh:
        # Offline only. Refresh the numerical report so an old PASS cannot hide changed results.
        refresh_m1(m1)
    report = json.loads((m1 / "m.json").read_text(encoding="utf-8"))
    if report.get("status") != "EXPLORATION_CHECKS_PASSED" or report.get("experiment_id") != "M1":
        raise ValueError("M1 has not passed the complete exploration checks")
    resources = report.get("resources", {})
    wall = nonnegative_number(resources.get("solver_wall_seconds"), "solver_wall_seconds")
    rss = nonnegative_number(resources.get("max_rss_kib"), "max_rss_kib")
    data = nonnegative_number(resources.get("data_bytes"), "data_bytes")
    if wall == 0 or rss == 0 or data == 0:
        raise ValueError("M1 resource measurement has insufficient positive resolution for conditional forecasting")
    original = config_for("M1")
    if wall > original["solver_timeout_seconds"] or rss > original["max_rss_kib"] or data > original["max_data_bytes"]:
        raise ValueError("M1 measured resource cost exceeds its observation/time budget; stop conditional experiments")
    cells_ratio = math.prod(config["cells"]) / math.prod(original["cells"])
    steps_ratio = config["steps"] / original["steps"]
    forecast = {"solver_wall_seconds": wall * cells_ratio * steps_ratio,
                "max_rss_kib": rss * cells_ratio, "data_bytes": data * max(cells_ratio, steps_ratio)}
    limits = {"solver_wall_seconds": config["solver_timeout_seconds"],
              "max_rss_kib": config["max_rss_kib"], "data_bytes": config["max_data_bytes"]}
    exceeded = [key for key in forecast if forecast[key] > limits[key]]
    if exceeded:
        raise ValueError("conditional scaling scenario exceeds budget: " + ", ".join(exceeded) +
                         "; forecast=" + json.dumps(forecast, sort_keys=True) +
                         "; limits=" + json.dumps(limits, sort_keys=True) +
                         "; estimates are not measured predictions; review before a different configuration")
    return {"m1_case_dir": str(m1), "reason": reason.strip(),
            "m1_project_commit": manifest.get("project_commit"), "forecast": forecast,
            "forecast_status": "SCALING_SCENARIO_NOT_GUARANTEE",
            "forecast_note": "M1 measured wall scaled by cell and step ratios; RSS by cells; data by max ratio. "
                             "Nonlinear iteration, evolving physics and I/O can invalidate these estimates."}


def disk_preflight(path, config):
    probe = Path(path)
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < config["max_data_bytes"]:
        raise ValueError("available filesystem space is below the 3 GiB observation budget; no case/stage started")
    return {"available_disk_bytes": free, "resource_policy": "MONITORED_ONLY",
            "note": "Disk availability checked now; RSS/data budgets are observed, not enforced hard limits."}


def preflight(case_dir):
    case = below(case_dir, REPO / "runs", "run directory", must_exist=True)
    manifest_path = case / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("symlinked manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = config_for(manifest["experiment_id"])
    if manifest.get("schema") != "threeD-exploration-run-v1" or manifest.get("config") != config:
        raise ValueError("run manifest differs from authorized configuration")
    build, summary, commit = build_record(manifest["build_dir"])
    if any((manifest.get("project_commit") != commit, manifest.get("build_commit") != commit,
            manifest.get("WM_OPTIONS") != summary["WM_OPTIONS"], manifest.get("solver") != "laserbeamFoam",
            manifest.get("mpi_ranks") != 1, manifest.get("threads") != 1)):
        raise ValueError("prepared run/build/source/solver identity no longer matches")
    condition = manifest.get("conditional") or {}
    evidence = conditional_evidence(config, condition.get("m1_case_dir"), condition.get("reason"))
    result = {"status": "PREFLIGHT_PASSED", "experiment_id": config["id"],
              "resources": disk_preflight(case, config), "conditional": evidence}
    # Explicit and small diagnostics; private paths stay in the local manifest.
    write_preflight(case, result)
    print("PREFLIGHT_PASSED: " + config["id"] + "; RSS/data MONITORED_ONLY; no CFD started")
    if evidence:
        print("Conditional cost scaling scenario (not guarantee): " + json.dumps(evidence["forecast"]))
    return result


def write_preflight(case, result):
    target = case / "preflight.json"
    if target.exists() or target.is_symlink():
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("preflight.json must be a regular, unlinked local report; refusing unsafe output")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def prepare(run_dir, build_dir, experiment, m1_case_dir=None, reason=None):
    started = time.perf_counter()
    config = config_for(experiment)
    out = Path(run_dir).absolute()
    if out.exists() or out.is_symlink():
        raise ValueError("run directory exists; choose a NEW name; no resume or cleanup")
    out = below(out, REPO / "runs", "run directory")
    build, summary, commit = build_record(build_dir)
    conditional = conditional_evidence(config, m1_case_dir, reason)
    resource_check = disk_preflight(out, config)
    source, revision = config["source"], config["source_commit"]
    paths = base.git("ls-tree", "-r", "--name-only", revision, "--",
                     *(source + "/" + d for d in ("initial", "constant", "system"))).decode().splitlines()
    if not paths:
        raise ValueError("pinned upstream inputs missing")
    payload = {}
    for path in paths:
        if base.git("ls-tree", revision, "--", path).decode().split()[0] not in ("100644", "100755"):
            raise ValueError("non-regular source input: " + path)
        payload[Path(path).relative_to(source)] = base.git("show", revision + ":" + path)
    control = payload[Path("system/controlDict")].decode("ascii")
    changes = {"application": "laserbeamFoam", "startFrom": "startTime", "startTime": 0,
               "stopAt": "endTime", "endTime": config["end_time"], "deltaT": config["delta_t"],
               "maxDeltaT": config["delta_t"], "adjustTimeStep": "no", "writeControl": "timeStep",
               "writeInterval": config["write_interval"], "purgeWrite": 0,
               "writeFormat": "ascii", "writePrecision": 17, "writeCompression": "off",
               "timePrecision": 12, "runTimeModifiable": "no"}
    for key, value in changes.items():
        control = base.set_entry(control, key, value)
    payload[Path("system/controlDict")] = control.encode("ascii")
    mesh = payload[Path("system/blockMeshDict")].decode("ascii")
    mesh, count = re.subn(r"(?m)^(\s*hex\s+\([^)]*\)\s+)\([^)]*\)",
                          lambda m: m[1] + "(" + " ".join(map(str, config["cells"])) + ")", mesh)
    if count != 1:
        raise ValueError("expected one active block in pinned 3D case")
    payload[Path("system/blockMeshDict")] = mesh.encode("ascii")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    for relative, content in payload.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (out / "inputs.sha256").write_text("".join(
        hashlib.sha256(content).hexdigest() + "  " + path.as_posix() + "\n"
        for path, content in sorted(payload.items())), encoding="ascii")
    manifest = {"schema": "threeD-exploration-run-v1", "experiment_id": experiment,
                "project_commit": commit, "build_commit": summary["project_commit"], "build_dir": str(build),
                "WM_OPTIONS": summary["WM_OPTIONS"], "solver": "laserbeamFoam", "mpi_ranks": 1, "threads": 1,
                "config": config, "conditional": conditional, "execution": "NOT_RUN", "accuracy": "UNVERIFIED"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "Allrun").write_text("#!/usr/bin/env bash\nexec bash " +
        shlex.quote(str(REPO / "scripts/run_m_case.sh")) + " --case-dir " + shlex.quote(str(out)) + ' "$@"\n', encoding="utf-8", newline="\n")
    (out / "Allclean").write_text("#!/usr/bin/env bash\necho 'Exploration evidence retained: no automatic cleanup or resume.' >&2\nexit 2\n", encoding="utf-8", newline="\n")
    for name in ("Allrun", "Allclean"):
        (out / name).chmod(0o755)
    (out / "metadata.sha256").write_text("".join(
        hashlib.sha256((out / name).read_bytes()).hexdigest() + "  " + name + "\n"
        for name in ("manifest.json", "Allrun", "Allclean")), encoding="ascii")
    (out / "preparation.time.txt").write_text("preparation_wall_seconds={:.9f}\n".format(time.perf_counter() - started), encoding="utf-8")
    write_preflight(out, {"status": "PREPARATION_PASSED", "resources": resource_check, "conditional": conditional})
    print("PREPARED " + experiment + ": authorized exploration; formal benchmark PROPOSED; no CFD started")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=tuple(PROFILES))
    parser.add_argument("--run-dir")
    parser.add_argument("--build-dir")
    parser.add_argument("--m1-case-dir")
    parser.add_argument("--reason", help="specific scientific purpose for conditional M2/M3")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--case-dir")
    args = parser.parse_args()
    try:
        if args.preflight:
            if not args.case_dir or any((args.experiment, args.run_dir, args.build_dir, args.m1_case_dir, args.reason)):
                raise ValueError("preflight takes only --preflight --case-dir CASE")
            preflight(args.case_dir)
        else:
            if not all((args.experiment, args.run_dir, args.build_dir)) or args.case_dir:
                raise ValueError("preparation requires --experiment M1|M2|M3 --run-dir NEW --build-dir BUILD")
            prepare(args.run_dir, args.build_dir, args.experiment, args.m1_case_dir, args.reason)
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print("ERROR [prepare-m/preflight] " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
