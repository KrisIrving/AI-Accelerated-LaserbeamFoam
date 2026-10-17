#!/usr/bin/env python3
"""Independent M1-IC preparation/initialization/check profile. No CFD invocation.

Only initialize writes a native field, only in the fresh controlled run. Sources
are read-only. Existing M profiles and their default checker remain unchanged.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

import compare_m1_m3 as cross
import check_m_case as checks
import prepare_m_case as prep

REPO = Path(__file__).resolve().parents[1]
METHOD = "M3_NATIVE_ALPHA_VOLUME_RESTRICTION_8_TO_1"
REFERENCE = "ic-data/restriction-reference.json"
N = cross.native


def config_for():
    value = json.loads((REPO / "benchmarks/threeD-exploration/M1-IC.json").read_text())
    expected = dict(prep.config_for("M1"), schema="m1-ic-exploration-v1",
        status="CONTROLLED_EXPLORATION_AUTHORIZED", id="M1-IC", steps=300,
        end_time="3e-6", solver_timeout_seconds=600, initialization=METHOD, decision="DEC-007")
    if value != expected:
        raise N.ComparisonFailure("M1-IC configuration differs from DEC-007 authorization")
    return value


def json_write(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def manifest(case):
    data = json.loads(cross.Source(case, "M1-IC").file("manifest.json").read_text())
    if (data.get("schema") != "m1-ic-run-v1" or data.get("experiment_id") != "M1-IC"
            or data.get("config") != config_for() or data.get("solver") != "laserbeamFoam"
            or data.get("mpi_ranks") != 1 or data.get("threads") != 1
            or data.get("project_commit") != data.get("build_commit")
            or not re.fullmatch(r"[0-9a-f]{40}", data.get("project_commit", ""))):
        raise N.ComparisonFailure("invalid independent M1-IC manifest")
    return data


def hash_inventory(case, roots):
    result = {}
    for root in roots:
        for path in (case / root).rglob("*"):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise N.ComparisonFailure("unsafe initialized artifact: " + str(path.relative_to(case)))
            if path.is_file():
                result[path.relative_to(case).as_posix()] = cross.digest(path)
    return result


def reference(case, record, verify_sources=True):
    source = cross.Source(case, "M1-IC")
    path = source.file(REFERENCE)
    if cross.digest(path) != record["reference_sha256"]:
        raise N.ComparisonFailure("restriction reference checksum mismatch")
    ref = json.loads(path.read_text())
    if ref.get("method") != METHOD:
        raise N.ComparisonFailure("unknown initialization method")
    if verify_sources:
        for label in ("M1", "M3"):
            original = cross.Source(record["source_cases"][label], label)
            for name, checksum in ref["sources"][label]["sha256"].items():
                if cross.digest(original.file(name)) != checksum:
                    raise N.ComparisonFailure(label + "/" + name + ": source changed since IC preparation")
            original.unchanged()
    return ref


def bounded_alpha(values):
    if not values or any(not math.isfinite(a) or not 0 <= a <= 1 for a in values):
        raise N.ComparisonFailure("restricted/source alpha must be finite and within [0,1]; no clipping")


def volume_restriction(coarse, fine, alpha):
    bounded_alpha(alpha)
    if len(alpha) != len(fine["volumes"]) or any(not math.isfinite(v) or v <= 0
            for grid in (coarse, fine) for v in grid["volumes"]):
        raise N.ComparisonFailure("restriction requires positive finite native cell volumes and matching alpha size")
    groups = cross.build_mapping(coarse, fine)
    # Normalize each convex average by the sum of its validated child volumes.
    # This preserves constants without clipping tiny roundoff above one. No
    # global normalization is used to force an expected metal volume.
    values = [math.fsum(alpha[j] * fine["volumes"][j] for j in children) /
              math.fsum(fine["volumes"][j] for j in children) for children in groups]
    bounded_alpha(values)
    total = math.fsum(a * v for a, v in zip(alpha, fine["volumes"]))
    restricted = math.fsum(a * v for a, v in zip(values, coarse["volumes"]))
    if total <= 0 or not math.isclose(total, restricted, rel_tol=1e-10, abs_tol=0):
        raise N.ComparisonFailure("restriction metal integral differs from native M3")
    return values, total


def prepared_inputs(case):
    result = {}
    for line in case["source"].file("inputs.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        if name in result:
            raise N.ComparisonFailure("duplicate prepared input path")
        result[name] = checksum
    return result


def prepare(run_dir, build_dir, m1_dir, m3_dir):
    started = time.perf_counter()
    config = config_for()
    out = prep.below(run_dir, REPO / "runs", "M1-IC run")
    if out.exists():
        raise N.ComparisonFailure("run exists; choose a fresh independent directory")
    if (REPO / "runs/.m1-ic-solve-attempt").exists():
        raise N.ComparisonFailure("M1-IC CFD authorization already consumed; retain evidence")
    # This authorization is one CFD attempt, not automatic replication/resume.
    for path in (REPO / "runs").glob("*/manifest.json"):
        if path.is_symlink() or path.parent.is_symlink():
            raise N.ComparisonFailure("symlinked run manifest")
        old = json.loads(path.read_text())
        if old.get("experiment_id") == "M1-IC" and (path.parent / ".solve-started").exists():
            raise N.ComparisonFailure("M1-IC already attempted; owner approval required for another run")
    build, summary, commit = prep.build_record(build_dir)
    resources = prep.disk_preflight(out, config)
    cases = [cross.load_case(prep.below(p, REPO / "runs", label + " source", True), label)
             for p, label in ((m1_dir, "M1"), (m3_dir, "M3"))]
    for source in cases:
        if source["manifest"]["config"] != prep.config_for(source["source"].label):
            raise N.ComparisonFailure("source is not the authorized original M1/M3 profile")
        audit = cross.box_selection_audit(source["grid"], source["initial"]["alpha.metal"], source["initialization_input"])
        if not audit.get("raw_alpha_matches_centre_selection"):
            raise N.ComparisonFailure("source initial alpha does not match original centre selection")
        if prep.base.git("diff", source["manifest"]["project_commit"], commit, "--", "applications", "src", "Allwmake"):
            raise N.ComparisonFailure("solver/library/build source differs from original M run; review required")
    a, b = cases
    inventories = [prepared_inputs(c) for c in cases]
    differences = {k for k in set(inventories[0]) | set(inventories[1])
                   if inventories[0].get(k) != inventories[1].get(k)}
    if differences != {"system/blockMeshDict"}:
        raise N.ComparisonFailure("M1/M3 prepared inputs must differ only in system/blockMeshDict")
    values, total = volume_restriction(a["grid"], b["grid"], b["initial"]["alpha.metal"])
    payload = {name: a["source"].file(name).read_bytes() for name in inventories[0]}
    control = payload["system/controlDict"].decode("ascii")
    for key, value in (("endTime", config["end_time"]), ("writeInterval", config["write_interval"])):
        control = prep.base.set_entry(control, key, value)
    payload["system/controlDict"] = control.encode("ascii")
    ref = {"method": METHOD, "shape": config["cells"], "mesh": a["mesh"],
        "centres": a["grid"]["centres"], "volumes": a["grid"]["volumes"], "alpha": values,
        "original_M1_alpha": a["initial"]["alpha.metal"],
        "native_M3_initial_metal_volume_m3": total, "sources": {}}
    for c in cases:
        c["source"].unchanged()
        ref["sources"][c["source"].label] = {
            "run_commit": c["manifest"]["project_commit"], "build_commit": c["manifest"]["build_commit"],
            "sha256": c["source"].hashes}
    out.mkdir(parents=True)
    for name, content in payload.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (out / "ic-data").mkdir()
    json_write(out / REFERENCE, ref)
    record = {"schema": "m1-ic-run-v1", "experiment_id": "M1-IC", "config": config,
        "project_commit": commit, "build_commit": commit, "build_dir": str(build),
        "WM_OPTIONS": summary["WM_OPTIONS"], "solver": "laserbeamFoam", "mpi_ranks": 1, "threads": 1,
        "source_cases": {c["source"].label: str(c["source"].path) for c in cases},
        "reference_sha256": cross.digest(out / REFERENCE), "execution": "NOT_RUN", "accuracy": "UNVERIFIED"}
    json_write(out / "manifest.json", record)
    (out / "inputs.sha256").write_text("".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
        for name, data in sorted(payload.items())), encoding="ascii")
    (out / "Allrun").write_text("#!/usr/bin/env bash\nexec bash " + shlex.quote(str(REPO / "scripts/run_m1_ic_case.sh")) +
        " --case-dir " + shlex.quote(str(out)) + ' "$@"\n', encoding="utf-8", newline="\n")
    (out / "Allclean").write_text("#!/usr/bin/env bash\necho 'Evidence retained; no cleanup or resume.' >&2\nexit 2\n", newline="\n")
    for name in ("Allrun", "Allclean"):
        (out / name).chmod(0o755)
    (out / "metadata.sha256").write_text("".join(cross.digest(out / name) + "  " + name + "\n"
        for name in ("manifest.json", "Allrun", "Allclean", REFERENCE)), encoding="ascii")
    (out / "preparation.time.txt").write_text("preparation_wall_seconds={:.9f}\n".format(time.perf_counter() - started))
    prep.write_preflight(out, {"status": "PREPARATION_PASSED", "resources": resources})
    print("PREPARED M1-IC; no mesh/CFD run; native reconstructed interface UNVERIFIED")
    return out


def preflight(case):
    case = prep.below(case, REPO / "runs", "M1-IC case", True)
    record = manifest(case)
    build, summary, commit = prep.build_record(record["build_dir"])
    if record["project_commit"] != commit or record["WM_OPTIONS"] != summary["WM_OPTIONS"]:
        raise N.ComparisonFailure("prepared M1-IC HEAD/build/options no longer match")
    for path in (REPO / "runs").glob("*/.solve-started"):
        other = path.parent
        if other != case and json.loads((other / "manifest.json").read_text()).get("experiment_id") == "M1-IC":
            raise N.ComparisonFailure("another M1-IC attempt exists; no automatic second run")
    reference(case, record)
    prep.write_preflight(case, {"status": "PREFLIGHT_PASSED", "resources": prep.disk_preflight(case, record["config"])})
    print("PREFLIGHT_PASSED M1-IC; CPU serial; source hashes checked; no CFD")


def attempt(case):
    case = prep.below(case, REPO / "runs", "M1-IC case", True)
    record = manifest(case)
    if not (case / ".mesh-complete").is_file() or (case / ".solve-started").exists():
        raise N.ComparisonFailure("single attempt requires completed mesh and no prior solve")
    # Atomic checkout-wide reservation prevents two prepared copies consuming
    # the one authorized run concurrently. Retain this marker after failure.
    guard = REPO / "runs/.m1-ic-solve-attempt"
    guard.mkdir()
    json_write(guard / "attempt.json", {"case": str(case.relative_to(REPO / "runs")),
        "project_commit": record["project_commit"], "authorization": "DEC-007; one solver attempt"})
    print("M1-IC single CFD attempt reserved; do not remove authorization evidence")


def expected_alpha(ref, centres, volumes, summary):
    old = cross.lattice(ref["centres"], ref["volumes"], ref["mesh"], ref["shape"])
    new = cross.lattice(centres, volumes, summary, ref["shape"])
    if any(abs(a - b) > max(old["tolerance"], new["tolerance"])
           for x, y in zip(old["bounds"], new["bounds"]) for a, b in zip(x, y)):
        raise N.ComparisonFailure("new coarse bounds differ from native M1 source")
    result = [None] * len(volumes)
    for key, i in new["lookup"].items():
        j = old["lookup"][key]
        if not math.isclose(volumes[i], old["volumes"][j], rel_tol=1e-10, abs_tol=0):
            raise N.ComparisonFailure("new coarse volume differs at " + str(key))
        result[i] = ref["alpha"][j]
    bounded_alpha(result)
    return result


def scalar_entry(values):
    return ["nonuniform", "List<scalar>", str(len(values)), [format(v, ".17g") for v in values]]


def boundary_for_alpha(case, boundary, alpha, geometry):
    """Retain BC types/inlet settings; refresh derived zeroGradient face values.

    The pinned case uses zeroGradient and inletOutlet (plus optional empty).
    Refuse other types/entries rather than inventing their initialization law.
    """
    result = copy.deepcopy(boundary)
    patches = dict(geometry["patches"])
    if "defaultFaces" not in patches and result.get("defaultFaces") == {"type": ["empty"]}:
        del result["defaultFaces"]
    if set(result) != set(patches):
        raise N.ComparisonFailure("alpha boundary/mesh patch sets differ")
    owner = N.label_list(case / "constant/polyMesh/owner")
    start = geometry["internal_faces"]
    for name, size in patches.items():
        state = result[name]
        kind = state.get("type")
        if kind == ["zeroGradient"] and set(state) <= {"type", "value"}:
            result[name]["value"] = scalar_entry([alpha[owner[i]] for i in range(start, start + size)])
        elif kind == ["inletOutlet"] and set(state) == {"type", "inletValue", "value"}:
            for key in ("inletValue", "value"):
                vals = N.expand_field(state[key], size, 1, "scalar")
                if any(v != 0 for v in vals):
                    raise N.ComparisonFailure("pinned alpha inletOutlet must retain zero " + key)
                result[name][key] = ["uniform", "0"]
        elif kind == ["empty"] and size == 0 and set(state) == {"type"}:
            pass
        else:
            raise N.ReviewRequired("unsupported M1-IC alpha BC: " + name + ": " + str(state))
        start += size
    if start != len(owner):
        raise N.ComparisonFailure("boundary owner addressing length mismatch")
    return result


def render_tokens(value):
    if isinstance(value, list):
        return "(" + " ".join(render_tokens(v) for v in value) + ")"
    if not isinstance(value, str) or not re.fullmatch(r'[^\s{};()\[\]]+', value):
        raise N.ReviewRequired("unsupported alpha serialization token")
    return value


def alpha_text(alpha, boundary):
    text = ("// M1-IC: conservative native M3 alpha restriction; BC laws retained.\n"
            "FoamFile {version 2.0; format ascii; class volScalarField; location \"0\"; object alpha.metal;}\n"
            "dimensions [0 0 0 0 0 0 0];\ninternalField " +
            " ".join(render_tokens(t) for t in scalar_entry(alpha)) + ";\nboundaryField\n{\n")
    for patch, entries in boundary.items():
        text += "  " + render_tokens(patch) + "\n  {\n"
        for key, value in entries.items():
            text += "    " + render_tokens(key) + " " + " ".join(render_tokens(t) for t in value) + ";\n"
        text += "  }\n"
    return text + "}\n"


def initialize(case):
    case = prep.below(case, REPO / "runs", "M1-IC case", True)
    record = manifest(case)
    if (not (case / ".mesh-started").is_dir() or (case / ".solve-started").exists()
            or (case / ".mesh-complete").exists() or (case / "ic-initialization.json").exists()):
        raise N.ComparisonFailure("initialize requires fresh mesh stage; never replace initialized/evolved evidence")
    if (case / "exit.setFields.txt").read_text().strip() != "0":
        raise N.ComparisonFailure("setFields did not succeed before restriction")
    ref = reference(case, record)
    geometry, volumes, centres, summary = checks.mesh_metrics(case, record["config"])
    alpha = expected_alpha(ref, centres, volumes, summary)
    before = hash_inventory(case, ("0", "constant/polyMesh"))
    field, old_alpha, _ = checks.field_check(case / "0/alpha.metal", geometry, initial=True)
    if field["class"] != "volScalarField" or field["dimensions"] != [0] * 7:
        raise N.ComparisonFailure("invalid native post-setFields alpha class/dimensions")
    # Compare the baseline boundary law against the immutable prepared template.
    template = N.parse_field(case / "initial/alpha.metal")
    boundary = boundary_for_alpha(case, template["boundary"], alpha, geometry)
    original = dict(ref, alpha=ref["original_M1_alpha"])
    expected_old = expected_alpha(original, centres, volumes, summary)
    if len(old_alpha) != len(expected_old) or any(abs(a - b) > 1e-12 for a, b in zip(old_alpha, expected_old)):
        raise N.ComparisonFailure("pre-intervention setFields alpha differs from original native M1")
    expected_before = boundary_for_alpha(case, template["boundary"], old_alpha, geometry)
    # setFields may leave zeroGradient value caches absent/stale. Only its BC
    # types and prescribed inlet values must equal the prepared laws.
    actual_before = boundary_for_alpha(case, field["boundary"], old_alpha, geometry)
    N.compare_tree(expected_before, actual_before, 1e-12, 1e-10, "pre-intervention alpha boundary laws")
    # Atomic replacement only inside the fresh experiment; never edit source cases.
    target = case / "0/alpha.metal"
    temp = case / "0/.alpha-ic.tmp"
    with temp.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(alpha_text(alpha, boundary))
    checks.field_check(temp, geometry, initial=True)
    temp.replace(target)
    after = hash_inventory(case, ("0", "constant/polyMesh"))
    if {p for p in before if before[p] != after.get(p)} != {"0/alpha.metal"} or set(before) != set(after):
        raise N.ComparisonFailure("initialization changed an artifact other than 0/alpha.metal")
    total = math.fsum(a * v for a, v in zip(alpha, volumes))
    if not math.isclose(total, ref["native_M3_initial_metal_volume_m3"], rel_tol=1e-10, abs_tol=0):
        raise N.ComparisonFailure("initialized metal integral differs from source M3")
    output = {"status": "IC_INITIALIZATION_PASSED", "method": METHOD,
        "pre_intervention_setFields_alpha_matches_native_M1": True,
        "pre_intervention_metal_volume_m3": math.fsum(a * v for a, v in zip(old_alpha, volumes)),
        "reference_sha256": record["reference_sha256"], "metal_volume_m3": total,
        "native_M3_initial_metal_volume_m3": ref["native_M3_initial_metal_volume_m3"],
        "alpha_min": min(alpha), "alpha_max": max(alpha), "fractional_cells": sum(0 < a < 1 for a in alpha),
        "before_sha256": before, "after_sha256": after, "sources": ref["sources"],
        "boundary_note": "BC laws retained; zeroGradient value caches recomputed from new owner alpha",
        "reconstructed_interface": "UNVERIFIED; alpha=0.5 does not define a measured PLIC surface"}
    json_write(case / "ic-initialization.json", output)
    print("IC_INITIALIZATION_PASSED; only native 0/alpha.metal changed; interface reconstruction UNVERIFIED")


def validate_initial(case, record, geometry, volumes, centres, summary, alpha):
    ref = reference(case, record)
    actual = expected_alpha(ref, centres, volumes, summary)
    if len(alpha) != len(actual) or any(abs(a - b) > 1e-12 for a, b in zip(alpha, actual)):
        raise N.ComparisonFailure("M1-IC/0/alpha.metal differs from source volume restriction")
    bounded_alpha(alpha)
    evidence_path = cross.Source(case, "M1-IC").file("ic-initialization.json")
    evidence = json.loads(evidence_path.read_text())
    if evidence.get("status") != "IC_INITIALIZATION_PASSED" or evidence.get("reference_sha256") != record["reference_sha256"]:
        raise N.ComparisonFailure("missing/invalid controlled initialization evidence")
    if evidence.get("sources") != ref["sources"]:
        raise N.ComparisonFailure("controlled initialization source records differ")
    if (case / "exit.restrictAlpha.txt").read_text().strip() != "0":
        raise N.ComparisonFailure("controlled initialization command did not exit zero")
    initialization_resources = cross.gnu_time_record(case / "time.restrictAlpha.txt")
    if initialization_resources["status"] != "RECORDED":
        raise N.ReviewRequired("missing restrictAlpha wall/RSS record")
    current = hash_inventory(case, ("0", "constant/polyMesh"))
    if current != evidence["after_sha256"]:
        raise N.ComparisonFailure("controlled initialization snapshot changed")
    before = evidence["before_sha256"]
    if set(before) != set(current) or {p for p in before if before[p] != current[p]} != {"0/alpha.metal"}:
        raise N.ComparisonFailure("non-alpha initial artifact changed during controlled initialization")
    expected_bc = boundary_for_alpha(case, N.parse_field(case / "initial/alpha.metal")["boundary"], actual, geometry)
    actual_bc = N.parse_field(case / "0/alpha.metal")["boundary"]
    N.compare_tree(expected_bc, actual_bc, 1e-12, 1e-10, "M1-IC/0/alpha.metal/boundaryField")
    total = math.fsum(a * v for a, v in zip(alpha, volumes))
    if not math.isclose(total, ref["native_M3_initial_metal_volume_m3"], rel_tol=1e-10, abs_tol=0):
        raise N.ComparisonFailure("M1-IC initial metal quantity mismatch")
    grid = cross.lattice(centres, volumes, summary, record["config"]["cells"])
    return {"status": "PASS", "method": METHOD, "box_centre_selection": "NOT_APPLICABLE",
        "reference_sha256": record["reference_sha256"], "source_records": ref["sources"],
        "metal_volume_m3": total, "layers": cross.y_layers(grid, {"alpha.metal": alpha}, "M1-IC", 0),
        "surface": cross.initial_surface(grid, alpha), "reconstructed_interface": "UNVERIFIED",
        "initialization_resources": initialization_resources}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "check":
        return checks.main(argv[1:], manifest_reader=manifest, initial_validator=validate_initial, feedback_profile="m1-ic")
    parser = argparse.ArgumentParser(description=__doc__, epilog=
        "Offline: m1_ic.py check --case-dir CASE [--mesh-only | --feedback-bundle]")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    for name in ("run-dir", "build-dir", "m1-case-dir", "m3-case-dir"):
        p.add_argument("--" + name, required=True, type=Path)
    for action in ("preflight", "initialize", "attempt"):
        sub.add_parser(action).add_argument("--case-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            prepare(args.run_dir, args.build_dir, args.m1_case_dir, args.m3_case_dir)
        elif args.action == "preflight":
            preflight(args.case_dir)
        elif args.action == "attempt":
            attempt(args.case_dir)
        else:
            initialize(args.case_dir)
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, N.ComparisonFailure,
            N.ReviewRequired, subprocess.CalledProcessError) as exc:
        print("ERROR [M1-IC/" + args.action + "] " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
