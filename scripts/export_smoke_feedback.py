#!/usr/bin/env python3
"""Export bounded, redacted diagnostic text only; never run CFD or upload data."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tarfile
import uuid

TOOL_VERSION = "smoke-feedback-v1"
REPO = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
SOLVERS = ("laserbeamFoam", "aiLaserbeamFoam")
STAGES = ("blockMesh", "checkMesh", "setFields") + SOLVERS
ALLOWED = ("smoke.txt", "smoke.json", "solver.exit.txt", "solver.time.txt",
           "preparation.time.txt", "time.workflow.mesh.txt", "time.workflow.solve.txt") + tuple(
    prefix + stage + suffix for stage in STAGES
    for prefix, suffix in (("log.", ""), ("exit.", ".txt"), ("time.", ".txt")))
EXIT_CODES = {"SMOKE_CHECKS_PASSED": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}


def safe_directory(path):
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError("parent traversal in directory path")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlinked directory path")
    if not path.is_dir():
        raise ValueError("missing directory")
    return path


def read_text(path):
    """Bound the read and reject symlinks, special files and binary payloads."""
    if path.is_symlink():
        raise ValueError("symlinked file")
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError("non-regular file")
    descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("non-regular opened file")
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("file exceeds size limit")
    text = data.decode("utf-8")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise ValueError("binary/control-character payload")
    return text


def redact(text):
    # Do not export environment dumps. Scrub known identities as well as generic
    # host/user lines, absolute paths, IPv4 addresses and user@host prompts.
    text = re.sub(r"(?im)^(\s*(?:user(?:name)?|host(?:name)?|buildHost|machine|login)\s*[:=]\s*).*$",
                  r"\1<REDACTED>", text)
    text = re.sub(r"\b[\w.-]+@[\w.-]+\b", "<USER@HOST>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>", text)
    text = re.sub(r"(?<![\w.])(?:[A-Za-z]:[\\/]|\\\\)[^\s\"'<>]*", "<PATH>", text)
    # Includes POSIX paths in JSON strings (with spaces), then unquoted paths.
    text = re.sub(r'"/(?:[^"\n]|\\.)*"', '"<PATH>"', text)
    text = re.sub(r"(?<![\w/])/(?!/)[^\s\"'<>]*", "<PATH>", text)
    identities = {socket.gethostname(), os.environ.get("USER", ""), os.environ.get("USERNAME", "")}
    for value in sorted(identities, key=len, reverse=True):
        if value:
            text = re.sub(r"(?<![\w.-])" + re.escape(value) + r"(?![\w.-])", "<IDENTITY>", text)
    return text


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def export_feedback(case, check_exit_code=None):
    case = safe_directory(case)
    payload, missing, omitted = {}, [], {}

    def load(name):
        try:
            return json.loads(read_text(case / name))
        except (OSError, ValueError) as exc:
            omitted[name] = type(exc).__name__ + ": metadata unavailable or invalid"
            return {}

    manifest, report = load("manifest.json"), load("smoke.json")
    if not isinstance(manifest, dict):
        manifest = {}
    if not isinstance(report, dict):
        report = {}
    solver = manifest.get("solver") if manifest.get("solver") in SOLVERS else None
    total = 0
    for name in ALLOWED:
        path = case / name
        if not path.exists() and not path.is_symlink():
            missing.append(name)
            continue
        try:
            data = redact(read_text(path)).encode("utf-8")
            if total + len(data) > MAX_TOTAL_BYTES:
                raise ValueError("total payload exceeds size limit")
            payload[name] = data
            total += len(data)
        except (OSError, ValueError) as exc:
            omitted[name] = type(exc).__name__ + ": " + redact(str(exc))

    def commit(value):
        return value if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) else "UNVERIFIED"

    summary = {}
    try:
        build = safe_directory(manifest.get("build_dir", ""))
        validation = (REPO / "validation").resolve()
        if not build.is_relative_to(validation):
            raise ValueError("build metadata is outside repository validation directory")
        summary = dict(line.split("=", 1) for line in read_text(build / "summary.txt").splitlines() if "=" in line)
    except (OSError, ValueError, TypeError):
        omitted["build-summary"] = "Original build summary unavailable; build provenance UNVERIFIED"
    source = commit(manifest.get("project_commit"))
    built = commit(summary.get("project_commit"))
    declared = commit(manifest.get("build_commit"))
    verified = source == built == declared and source != "UNVERIFIED"
    config = manifest.get("config", {})
    if not isinstance(config, dict):
        config = {}
    config_summary = {k: config[k] for k in ("schema", "status", "source_commit", "cells", "steps",
                     "delta_t", "end_time", "mesh_timeout_seconds", "solver_timeout_seconds") if k in config}
    config_digest = hashlib.sha256(json_bytes(config)).hexdigest() if config else "UNVERIFIED"
    provenance = {"schema": TOOL_VERSION, "source_commit": source, "build_commit": built,
        "manifest_build_commit": declared, "provenance_status": "RECORDS_MATCH" if verified else "PROVENANCE_PENDING",
        "provenance_note": "Original manifest/build summary records only; no current HEAD or environment substitution. "
                           "Matching records do not reverify executed binaries. Config hash is canonical JSON, not input-file integrity.",
        "openfoam_version": summary.get("openfoam_version", "UNVERIFIED"),
        "WM_OPTIONS": summary.get("WM_OPTIONS", "UNVERIFIED"), "solver": solver or "UNVERIFIED",
        "mpi_ranks": manifest.get("mpi_ranks", "UNVERIFIED"), "config": config_summary,
        "config_canonical_sha256": config_digest,
        "observed": {k: report.get(k, "UNVERIFIED") for k in ("cells", "steps", "final_time", "diagnostic_events")},
        "check_status": report.get("status", "UNVERIFIED"), "tool_version": TOOL_VERSION}
    payload["provenance.json"] = redact(json_bytes(provenance).decode()).encode()

    from check_smoke_case import gnu_time_record
    timing = {name: gnu_time_record(case / ("time.workflow." + name + ".txt"))
              if "time.workflow." + name + ".txt" in payload else {"status": "UNVERIFIED"}
              for name in ("mesh", "solve")}
    timing_complete = all(v["status"] == "RECORDED" for v in timing.values())
    try:
        prep = payload["preparation.time.txt"].decode().strip().split("=", 1)
        import math
        timing_complete &= prep[0] == "preparation_wall_seconds" and math.isfinite(float(prep[1])) and float(prep[1]) >= 0
    except (KeyError, ValueError, IndexError):
        timing_complete = False
    original_status = report.get("status", "UNVERIFIED")
    original_exit = check_exit_code if check_exit_code is not None else EXIT_CODES.get(original_status)
    required = {"smoke.txt", "smoke.json", "solver.exit.txt", "solver.time.txt", "preparation.time.txt",
                "time.workflow.mesh.txt", "time.workflow.solve.txt", "log.blockMesh", "log.checkMesh", "log.setFields"}
    if solver:
        required.add("log." + solver)
        required.update(prefix + stage + ".txt" for stage in (*STAGES[:3], solver)
                        for prefix in ("exit.", "time."))
    absent_required = sorted(required - payload.keys())
    solver_exit = payload.get("solver.exit.txt", b"").decode().strip()
    result = {"archive_status": "EXPORTED", "check_status": original_status,
        "check_exit_code": original_exit,
        "solver_exit_code": int(solver_exit) if re.fullmatch(r"-?\d+", solver_exit) else "UNVERIFIED",
        "exit_code_source": "CURRENT_OFFLINE_CHECK" if check_exit_code is not None else "INFERRED_FROM_SAVED_REPORT",
        "timing_status": "RECORDED_SCOPE" if timing_complete else "INCOMPLETE_TIMING",
        "collection_status": "PARTIAL" if omitted or absent_required or not timing_complete else "COMPLETE",
        "missing_required": absent_required, "missing_optional": sorted(set(missing) - required),
        "omitted": omitted, "tool_version": TOOL_VERSION,
        "privacy": "Best-effort redacted copies only; inspect before sharing. Originals unchanged; no upload. "
                   "SHA256SUMS covers archived redacted bytes, not original logs or CFD fields."}
    payload["bundle.json"] = json_bytes(result)
    payload["FILES.txt"] = ("\n".join(sorted([*payload, "FILES.txt", "SHA256SUMS"])) + "\n").encode()
    payload["SHA256SUMS"] = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                                          for name, data in sorted(payload.items())).encode()
    if sum(map(len, payload.values())) > MAX_TOTAL_BYTES:
        raise ValueError("final payload exceeds total size limit")
    # Assemble entirely in memory before creating any final artifact. No source
    # paths, symlinks, owner names or host metadata enter the tar headers.
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in sorted(payload.items()):
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(data), 0o600
            archive.addfile(entry, io.BytesIO(data))
    data = buffer.getvalue()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("compressed archive exceeds size limit")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        if sorted(archive.getnames()) != sorted(payload):
            raise ValueError("archive inventory verification failed")
        for entry in archive:
            if not entry.isfile() or archive.extractfile(entry).read() != payload[entry.name]:
                raise ValueError("archive readability/content verification failed")
    feedback = case / "feedback"
    feedback.mkdir(exist_ok=True)
    safe_directory(feedback)
    stem = "threeD-smoke-feedback." + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "." + uuid.uuid4().hex
    archive_path = feedback / (stem + ".tar.gz")
    with archive_path.open("xb") as stream:
        stream.write(data)
    with (feedback / (stem + ".sha256")).open("x", encoding="ascii") as stream:
        stream.write(hashlib.sha256(data).hexdigest() + "  " + archive_path.name + "\n")
    with (feedback / (stem + ".files.txt")).open("xb") as stream:
        stream.write(payload["FILES.txt"])
    result.update(archive_path=str(archive_path), archive_bytes=len(data))
    return result


def print_result(result):
    print("Feedback archive: {} ({} bytes)".format(result["archive_path"], result["archive_bytes"]))
    print("Archive: {}; collection: {}; timing: {}; original check: {} (exit {})".format(
        result["archive_status"], result["collection_status"], result["timing_status"],
        result["check_status"], result["check_exit_code"]))
    for name, reason in result["omitted"].items():
        print("WARNING [feedback] {}: {}".format(name, reason), file=sys.stderr)
    print("Review redacted contents before sharing; no files were uploaded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--diagnostics-only", required=True, action="store_true",
                        help="export existing evidence without checking fields or starting CFD")
    args = parser.parse_args()
    try:
        print_result(export_feedback(args.case_dir))
        return 0
    except (OSError, ValueError, TypeError, tarfile.TarError) as exc:
        print("ERROR [feedback] archive_status=FAILED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
