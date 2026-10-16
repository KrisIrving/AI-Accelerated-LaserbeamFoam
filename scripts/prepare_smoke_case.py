#!/usr/bin/env python3
"""Prepare a proposed native 3D smoke copy; never invoke CFD, DEM or cleanup."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def entries(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)


def set_entry(text, key, value):
    pattern = r"(?m)^(\s*" + re.escape(key) + r"\s+)[^;\n]+;"
    text, count = re.subn(pattern, lambda m: m[1] + str(value) + ";", text)
    if count != 1:
        raise ValueError("expected one controlDict entry: " + key)
    return text


def prepare(run_dir, build_dir, solver, mesh_timeout=None, solver_timeout=None):
    started = time.perf_counter()
    config = json.loads((REPO / "benchmarks/threeD-smoke/config.json").read_text())
    out, build = Path(run_dir).absolute(), Path(build_dir).resolve(strict=True)
    # Check lexical existence first: never follow a dangling destination symlink.
    if out.exists() or out.is_symlink():
        raise ValueError("run directory exists; choose a NEW name")
    out = out.resolve()
    if not out.is_relative_to((REPO / "runs").resolve()) or out == (REPO / "runs").resolve():
        raise ValueError("run directory must be below this checkout/runs")
    if not build.is_relative_to((REPO / "validation").resolve()):
        raise ValueError("select this checkout's isolated validation build")
    summary = entries(build / "summary.txt")
    commit = git("rev-parse", "HEAD").decode().strip()
    if summary.get("project_commit") != commit:
        raise ValueError("build HEAD differs; use validate_build.sh with a NEW build report; do not edit old records")
    if not summary.get("status", "").startswith("BUILD_ARTIFACT_CHECKS_PASSED;"):
        raise ValueError("build artifact checks have not passed")
    if summary.get("openfoam_version") != "v2512":
        raise ValueError("build is not OpenFOAM.com v2512")
    if solver not in ("laserbeamFoam", "aiLaserbeamFoam"):
        raise ValueError("unsupported solver")
    for value in (mesh_timeout, solver_timeout):
        if value is not None and value <= 0:
            raise ValueError("timeouts must be positive seconds")
    config["mesh_timeout_seconds"] = mesh_timeout or config["mesh_timeout_seconds"]
    config["solver_timeout_seconds"] = solver_timeout or config["solver_timeout_seconds"]
    source, revision = config["source"], config["source_commit"]
    paths = git("ls-tree", "-r", "--name-only", revision, "--",
                *(source + "/" + d for d in ("initial", "constant", "system"))).decode().splitlines()
    if not paths:
        raise ValueError("pinned upstream inputs missing")
    # Read pinned tracked blobs, not potentially evolved local tutorial copies.
    payload = {}
    for path in paths:
        relative = Path(path).relative_to(source)
        mode = git("ls-tree", revision, "--", path).decode().split()[0]
        if mode not in ("100644", "100755"):
            raise ValueError("non-regular source input: " + path)
        payload[relative] = git("show", revision + ":" + path)
    control = payload[Path("system/controlDict")].decode("ascii")
    changes = {"application": solver, "startFrom": "startTime", "startTime": 0,
               "stopAt": "endTime", "endTime": config["end_time"], "deltaT": config["delta_t"],
               "maxDeltaT": config["delta_t"], "adjustTimeStep": "no", "writeControl": "timeStep",
               "writeInterval": config["steps"], "writeFormat": "ascii", "writePrecision": 17,
               "writeCompression": "off", "timePrecision": 12, "runTimeModifiable": "no"}
    for key, value in changes.items():
        control = set_entry(control, key, value)
    payload[Path("system/controlDict")] = control.encode("ascii")
    mesh = payload[Path("system/blockMeshDict")].decode("ascii")
    mesh, count = re.subn(r"(?m)^(\s*hex\s+\([^)]*\)\s+)\([^)]*\)",
                          lambda m: m[1] + "(" + " ".join(map(str, config["cells"])) + ")", mesh)
    if count != 1:
        raise ValueError("expected one active block in pinned 3D case")
    payload[Path("system/blockMeshDict")] = mesh.encode("ascii")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()  # atomic refusal if another preparation won the race
    for relative, content in payload.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (out / "inputs.sha256").write_text("".join(
        hashlib.sha256(content).hexdigest() + "  " + path.as_posix() + "\n"
        for path, content in sorted(payload.items())), encoding="ascii")
    manifest = {"schema": "threeD-smoke-run-v1", "project_commit": commit,
                "build_commit": summary["project_commit"], "build_dir": str(build),
                "WM_OPTIONS": summary["WM_OPTIONS"], "solver": solver, "mpi_ranks": 1,
                "config": config, "execution": "NOT_RUN", "accuracy": "UNVERIFIED"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    command = "exec bash " + shlex.quote(str(REPO / "scripts/run_smoke_case.sh"))
    command += " --case-dir " + shlex.quote(str(out)) + ' "$@"\n'
    (out / "Allrun").write_text("#!/usr/bin/env bash\n" + command, encoding="utf-8")
    (out / "Allclean").write_text(
        "#!/usr/bin/env bash\necho 'Recorded smoke case: no automatic cleanup; choose a new run directory.' >&2\nexit 2\n",
        encoding="ascii")
    for name in ("Allrun", "Allclean"):
        (out / name).chmod(0o755)
    (out / "metadata.sha256").write_text("".join(
        hashlib.sha256((out / name).read_bytes()).hexdigest() + "  " + name + "\n"
        for name in ("manifest.json", "Allrun", "Allclean")), encoding="ascii")
    print("PREPARED / PROPOSED: no mesh, initialization utility or solver has run")
    (out / "preparation.time.txt").write_text(
        "preparation_wall_seconds={:.9f}\n".format(time.perf_counter() - started), encoding="ascii")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--solver", choices=("laserbeamFoam", "aiLaserbeamFoam"), default="laserbeamFoam")
    parser.add_argument("--accept-proposed-config", action="store_true",
                        help="opt into this exploratory configuration; not formal benchmark approval")
    parser.add_argument("--mesh-timeout", type=int)
    parser.add_argument("--solver-timeout", type=int)
    args = parser.parse_args()
    try:
        if not args.accept_proposed_config:
            raise ValueError("configuration is PROPOSED; explicit --accept-proposed-config is required")
        prepare(args.run_dir, args.build_dir, args.solver, args.mesh_timeout, args.solver_timeout)
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print("ERROR [prepare-smoke] " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
