#!/usr/bin/env python3
"""Conservative, offline comparison of the prepared Plate2D A/B runs.

This checks rename equivalence, not conservation closure or CFD validation.
Only native, uncompressed ASCII OpenFOAM fields on the same serial mesh are
supported. Anything not understood is REVIEW_REQUIRED, never a silent pass.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "T", "p_rgh", "U", "alpha.metal", "epsilon1", "Deposition", "phi",
    "H", "pH", "B", "J", "Joulesource", "JcrossB",
}
COMPONENTS = {"Scalar": 1, "Vector": 3, "Tensor": 9,
              "SymmTensor": 6, "SphericalTensor": 1}
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
NONFINITE = re.compile(r"^[+-]?(?:nan|inf(?:inity)?)$", re.I)
LOG_NUMBER = re.compile(
    r"(?<![A-Za-z_\d.])(?:[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    r"|[+-]?(?:nan|inf(?:inity)?))(?![A-Za-z_\d.])", re.I)
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[{}();\[\]]|[^\s{}();\[\]]+')


class ReviewRequired(Exception):
    pass


class ComparisonFailure(Exception):
    pass


def finite_number(token):
    if not isinstance(token, str):
        raise ReviewRequired("nested/non-token numeric value")
    if NONFINITE.fullmatch(token):
        raise ComparisonFailure("non-finite numeric value: " + token)
    if not NUMBER.fullmatch(token):
        raise ReviewRequired("unsupported numeric token: " + token)
    number = float(token)
    if not math.isfinite(number):
        raise ComparisonFailure("non-finite numeric value: " + token)
    return number


def read_ascii(path):
    if path.suffix == ".gz":
        raise ReviewRequired("compressed file: " + str(path))
    try:
        text = path.read_text(encoding="ascii")
    except (UnicodeError, OSError) as exc:
        raise ReviewRequired("cannot read native ASCII file {}: {}".format(path, exc))
    # Comments may contain directives; only reject active syntax.
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)
    if any(ord(character) < 32 and character not in "\t\r\n" for character in text):
        raise ReviewRequired("non-text control bytes: " + str(path))
    if "#" in text or "$" in text or "\\" in text:
        raise ReviewRequired("directives, substitutions or escapes: " + str(path))
    return text


class Parser:
    def __init__(self, text):
        self.tokens = TOKEN.findall(text)
        self.index = 0

    def pop(self):
        if self.index >= len(self.tokens):
            raise ReviewRequired("unexpected end of dictionary/list")
        result = self.tokens[self.index]
        self.index += 1
        return result

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def expect(self, value):
        found = self.pop()
        if found != value:
            raise ReviewRequired("expected {!r}, found {!r}".format(value, found))

    def item(self):
        token = self.pop()
        if token in ("(", "["):
            closing = ")" if token == "(" else "]"
            values = []
            while self.peek() != closing:
                values.append(self.item())
            self.expect(closing)
            return values
        if token == "{":
            return self.dictionary("}")
        if token in ("}", ")", "]", ";"):
            raise ReviewRequired("unexpected punctuation: " + token)
        return token

    def dictionary(self, end=None):
        result = {}
        while self.peek() is not None and self.peek() != end:
            key = self.pop()
            if key in (";", "(", ")", "[", "]", "{", "}"):
                raise ReviewRequired("invalid dictionary key: " + key)
            if key in result:
                raise ReviewRequired("duplicate dictionary key: " + key)
            if self.peek() == "{":
                self.pop()
                result[key] = self.dictionary("}")
                if self.peek() == ";":
                    self.pop()
            else:
                values = []
                while self.peek() != ";":
                    if self.peek() is None or self.peek() == end:
                        raise ReviewRequired("unterminated value for " + key)
                    values.append(self.item())
                self.pop()
                result[key] = values
        if end is not None:
            self.expect(end)
        return result

    def header(self):
        self.expect("FoamFile")
        self.expect("{")
        header = self.dictionary("}")
        if header.get("format") != ["ascii"]:
            raise ReviewRequired("only FoamFile format ascii is supported")
        if not isinstance(header.get("class"), list) or len(header["class"]) != 1:
            raise ReviewRequired("missing/invalid FoamFile class")
        return header

    def done(self):
        if self.peek() == ";":
            self.pop()
        if self.peek() is not None:
            raise ReviewRequired("unparsed trailing tokens")


def parse_field(path):
    parser = Parser(read_ascii(path))
    header = parser.header()
    field_class = header["class"][0]
    match = re.fullmatch(r"(vol|surface)(Scalar|Vector|Tensor|SymmTensor|SphericalTensor)Field", field_class)
    if not match:
        raise ReviewRequired("unsupported field class: " + field_class)
    data = parser.dictionary()
    for name in ("dimensions", "internalField", "boundaryField"):
        if name not in data:
            raise ReviewRequired("missing field entry " + name)
    if set(data) != {"dimensions", "internalField", "boundaryField"}:
        raise ReviewRequired("unsupported extra top-level field entries")
    dims = data["dimensions"]
    if len(dims) != 1 or not isinstance(dims[0], list) or len(dims[0]) != 7:
        raise ReviewRequired("invalid dimensions")
    dimensions = [finite_number(value) for value in dims[0]]
    if not isinstance(data["boundaryField"], dict):
        raise ReviewRequired("boundaryField is not a dictionary")
    return {"class": field_class, "location": match[1],
            "components": COMPONENTS[match[2]], "dimensions": dimensions,
            "internal": data["internalField"], "boundary": data["boundaryField"]}


def integer(token):
    if not isinstance(token, str) or not re.fullmatch(r"\d+", token):
        raise ReviewRequired("expected non-negative integer")
    return int(token)


def label_list(path):
    parser = Parser(read_ascii(path))
    header = parser.header()
    if header["class"] != ["labelList"]:
        raise ReviewRequired("unsupported mesh label list class")
    count = integer(parser.pop())
    values = parser.item()
    parser.done()
    if not isinstance(values, list) or len(values) != count:
        raise ComparisonFailure("mesh label list length mismatch")
    return [integer(value) for value in values]


def mesh_geometry(case):
    mesh = case / "constant" / "polyMesh"
    owner = label_list(mesh / "owner")
    neighbour = label_list(mesh / "neighbour")
    if not owner or len(neighbour) > len(owner):
        raise ComparisonFailure("invalid owner/neighbour counts")
    parser = Parser(read_ascii(mesh / "boundary"))
    if parser.header()["class"] != ["polyBoundaryMesh"]:
        raise ReviewRequired("unsupported boundary mesh class")
    count = integer(parser.pop())
    parser.expect("(")
    patches = {}
    ranges = []
    for _ in range(count):
        name = parser.pop().strip('"')
        parser.expect("{")
        values = parser.dictionary("}")
        if name in patches:
            raise ComparisonFailure("duplicate mesh patch")
        try:
            size = integer(values["nFaces"][0])
            start = integer(values["startFace"][0])
        except (KeyError, IndexError):
            raise ReviewRequired("invalid mesh patch addressing")
        patches[name] = size
        ranges.append((start, size))
    parser.expect(")")
    parser.done()
    face = len(neighbour)
    for start, size in ranges:
        if start != face:
            raise ComparisonFailure("mesh boundary ranges are not contiguous")
        face += size
    if face != len(owner):
        raise ComparisonFailure("mesh boundary/owner face counts disagree")
    return {"cells": max(owner + neighbour) + 1,
            "internal_faces": len(neighbour), "patches": patches}


def component_value(value, components):
    if components == 1 and isinstance(value, str):
        return [finite_number(value)]
    if not isinstance(value, list) or len(value) != components:
        raise ComparisonFailure("field component shape mismatch")
    return [finite_number(atom) for atom in value]


def expand_field(value, count, components, element_type=None):
    if not isinstance(value, list) or not value:
        raise ReviewRequired("invalid uniform/nonuniform field value")
    if value[0] == "uniform" and len(value) == 2:
        row = component_value(value[1], components)
        return row * count
    if value[0] == "nonuniform" and len(value) == 4:
        expected_type = element_type or {1: "scalar", 3: "vector", 6: "symmTensor", 9: "tensor"}[components]
        if value[1] != "List<" + expected_type + ">":
            raise ReviewRequired("unsupported nonuniform element type")
        if integer(value[2]) != count or not isinstance(value[3], list) or len(value[3]) != count:
            raise ComparisonFailure("nonuniform field entity count mismatch")
        result = []
        for row in value[3]:
            result.extend(component_value(row, components))
        return result
    raise ReviewRequired("unsupported field value syntax")


def numeric_statistics(a, b, atol, rtol):
    if len(a) != len(b):
        raise ComparisonFailure("numeric array length mismatch")
    differences = [abs(x - y) for x, y in zip(a, b)]
    passed = all(d <= atol + rtol * max(abs(x), abs(y))
                 for x, y, d in zip(a, b, differences))
    # hypot avoids overflow in accumulated squared norms.
    l2 = 0.0
    for difference in differences:
        l2 = math.hypot(l2, difference)
    if not math.isfinite(l2):
        raise ComparisonFailure("non-finite difference norm")
    return {"count": len(a), "max_abs": max(differences, default=0.0),
            "l2": l2, "within_tolerance": passed,
            "exact_equal": all(x == y for x, y in zip(a, b))}


def compare_tree(a, b, atol, rtol, path="boundary"):
    if type(a) is not type(b):
        raise ComparisonFailure(path + ": dictionary shape differs")
    if isinstance(a, dict):
        if set(a) != set(b):
            raise ComparisonFailure(path + ": dictionary keys differ")
        for key in sorted(a):
            compare_tree(a[key], b[key], atol, rtol, path + "/" + key)
    elif isinstance(a, list):
        if len(a) != len(b):
            raise ComparisonFailure(path + ": list shape differs")
        for index, (x, y) in enumerate(zip(a, b)):
            compare_tree(x, y, atol, rtol, path + "/" + str(index))
    elif NONFINITE.fullmatch(a) or NONFINITE.fullmatch(b):
        raise ComparisonFailure(path + ": non-finite token")
    elif NUMBER.fullmatch(a) and NUMBER.fullmatch(b):
        if not numeric_statistics([finite_number(a)], [finite_number(b)], atol, rtol)["within_tolerance"]:
            raise ComparisonFailure(path + ": numeric coefficient differs")
    elif a != b:
        raise ComparisonFailure(path + ": token differs")


def compare_fields(path_a, path_b, geometry, atol, rtol):
    a, b = parse_field(path_a), parse_field(path_b)
    for key in ("class", "dimensions", "components", "location"):
        if a[key] != b[key]:
            raise ComparisonFailure("field " + key + " differs")
    count = geometry["cells" if a["location"] == "vol" else "internal_faces"]
    element_type = a["class"][len(a["location"]):-len("Field")]
    element_type = element_type[0].lower() + element_type[1:]
    av = expand_field(a["internal"], count, a["components"], element_type)
    bv = expand_field(b["internal"], count, b["components"], element_type)
    result = {"class": a["class"], "internal": numeric_statistics(av, bv, atol, rtol), "patches": {}}
    if path_a.name == "alpha.metal":
        result["alpha_bounds"] = {"A": [min(av), max(av)], "B": [min(bv), max(bv)]}
    if set(a["boundary"]) != set(b["boundary"]):
        raise ComparisonFailure("boundary patch sets differ")
    # Output patch expansion must be explicit. Regex patch specifications need
    # OpenFOAM semantics and are deliberately not guessed here.
    if set(a["boundary"]) != set(geometry["patches"]):
        raise ReviewRequired("field patch names differ from explicit mesh patches")
    for patch, size in geometry["patches"].items():
        da, db = a["boundary"][patch], b["boundary"][patch]
        if not isinstance(da, dict) or not isinstance(db, dict) or set(da) != set(db):
            raise ComparisonFailure("boundary dictionary differs: " + patch)
        patch_result = {"value_status": "no explicit value (not replaced by zero)", "values": {}}
        for key in sorted(da):
            va, vb = da[key], db[key]
            if isinstance(va, list) and va and va[0] in ("uniform", "nonuniform"):
                # Gradient/value data may have different units, but the rank
                # follows the field for the supported native patch entries.
                ea = expand_field(va, size, a["components"], element_type)
                eb = expand_field(vb, size, b["components"], element_type)
                patch_result["values"][key] = numeric_statistics(ea, eb, atol, rtol)
                if key == "value":
                    patch_result["value_status"] = "compared explicit value"
            else:
                compare_tree(va, vb, atol, rtol, patch + "/" + key)
        result["patches"][patch] = patch_result
    return result


def manifest(case, name):
    path = case / name
    if path.is_symlink():
        raise ComparisonFailure("symlink manifest is not accepted")
    if not path.is_file():
        raise ReviewRequired("missing manifest " + str(path))
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+[* ]?(.+)", line)
        if not match:
            raise ReviewRequired("unsupported sha256sum manifest line")
        relative = match[2].replace("\\", "/")
        while relative.startswith("./"):
            relative = relative[2:]
        target = case / relative
        try:
            target.resolve().relative_to(case.resolve())
        except ValueError:
            raise ComparisonFailure("manifest path escapes case")
        if relative in entries or not target.is_file() or target.is_symlink():
            raise ComparisonFailure("duplicate/missing manifest member " + relative)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != match[1].lower():
            raise ComparisonFailure("manifest hash no longer matches " + relative)
        entries[relative] = actual
    if not entries:
        raise ReviewRequired("empty manifest")
    return entries


def normalized_control(path, application):
    text = path.read_bytes().decode("ascii")
    pattern = re.compile(r"(?m)^([ \t]*application[ \t]+)(\w+)(?=[ \t]*;)")
    matches = list(pattern.finditer(text))
    if len(matches) != 1 or matches[0][2] != application:
        raise ComparisonFailure("unexpected controlDict application in " + str(path))
    return pattern.sub(lambda m: m[1] + "__SOLVER__", text)


def tree_files(case, roots, exclude_mesh=False):
    result = set()
    for root in roots:
        for path in (case / root).rglob("*"):
            if path.is_symlink():
                raise ComparisonFailure("symlink in input/mesh tree: " + str(path))
            relative = str(path.relative_to(case)).replace("\\", "/")
            if path.is_file() and not (exclude_mesh and relative.startswith("constant/polyMesh/")):
                result.add(relative)
    return result


def check_manifests(a, b):
    result = {}
    for filename in ("inputs.sha256", "mesh.sha256"):
        ma, mb = manifest(a, filename), manifest(b, filename)
        if set(ma) != set(mb):
            raise ComparisonFailure(filename + ": path sets differ")
        for name in ma:
            if filename == "inputs.sha256" and name == "system/controlDict":
                if normalized_control(a / name, "laserbeamFoam") != normalized_control(b / name, "aiLaserbeamFoam"):
                    raise ComparisonFailure("controlDict differs beyond application")
            elif ma[name] != mb[name]:
                if filename == "mesh.sha256":
                    raise ReviewRequired("mesh hashes differ; no mapping attempted")
                raise ComparisonFailure("input differs: " + name)
        if filename == "inputs.sha256":
            required = {"system/controlDict"}
            if not required.issubset(ma) or not all(any(p.startswith(prefix + "/") for p in ma)
                                                    for prefix in ("initial", "constant", "system")):
                raise ReviewRequired("inputs manifest does not cover the prepared input trees")
            actual = tree_files(a, ("initial", "constant", "system"), exclude_mesh=True)
            actual_b = tree_files(b, ("initial", "constant", "system"), exclude_mesh=True)
            if actual != set(ma) or actual_b != set(mb):
                raise ComparisonFailure("input manifest omits or adds files")
        else:
            for case, recorded in ((a, ma), (b, mb)):
                actual = tree_files(case, ("constant/polyMesh",))
                if actual != set(recorded):
                    raise ComparisonFailure("mesh manifest does not cover all mesh files")
        result[filename] = {"verified_files": len(ma), "matching": True}
    return result


def parse_log(case, application):
    exit_file = case / "solver.exit.txt"
    time_file = case / "solver.time.txt"
    if not exit_file.is_file() or exit_file.read_text().strip() != "0":
        raise ComparisonFailure("missing/nonzero solver exit status in " + str(case))
    if not time_file.is_file() or not time_file.read_text().strip():
        raise ReviewRequired("missing solver.time.txt")
    log = case / ("log." + application)
    if not log.is_file():
        raise ComparisonFailure("missing solver log")
    lines = log.read_text(encoding="utf-8", errors="strict").splitlines()
    nonempty = [line.strip() for line in lines if line.strip()]
    if not nonempty or nonempty[-1] != "End":
        raise ComparisonFailure("solver log does not terminate normally with End")
    if re.search(r"FOAM FATAL|Floating point exception|Segmentation fault|MPI_ABORT|Traceback", "\n".join(lines), re.I):
        raise ComparisonFailure("fatal-error marker in solver log")
    if any(NONFINITE.fullmatch(match[0]) for line in lines for match in LOG_NUMBER.finditer(line)):
        raise ComparisonFailure("non-finite numeric token in solver log")
    events, times, categories = [], [], set()
    patterns = (
        ("linear", r"Solving for .+Initial residual.+Final residual.+No Iterations"),
        ("epsilon", r"Correcting epsilon1, mean residual"),
        ("continuity", r"continuity errors\s*:"),
        ("vof", r"Phase-1 volume fraction\s*="),
        ("courant", r"Courant Number mean:"),
        ("deltaT", r"^\s*deltaT\s*="),
        ("deposition", r"Total Q deposited:"),
    )
    for line in lines:
        time_match = re.fullmatch(r"\s*Time\s*=\s*(\S+)\s*", line)
        if time_match:
            time = finite_number(time_match[1])
            times.append(time)
            events.append({"kind": "time", "label": "Time = #", "values": [time]})
            continue
        for kind, pattern in patterns:
            if re.search(pattern, line):
                matches = list(LOG_NUMBER.finditer(line))
                values = [finite_number(match[0]) for match in matches]
                if not values:
                    raise ReviewRequired("recognized log event has no numeric data")
                label = " ".join(LOG_NUMBER.sub("#", line).split())
                events.append({"kind": kind, "label": label, "values": values})
                categories.add(kind)
                break
    if len(times) != 10 or any(y <= x for x, y in zip(times, times[1:])):
        raise ComparisonFailure("expected exactly ten increasing Time events")
    if not math.isclose(times[-1], 1e-7, rel_tol=1e-12, abs_tol=1e-16):
        raise ComparisonFailure("final solver time is not 1e-7")
    required = {"linear", "epsilon", "continuity", "vof", "courant", "deposition"}
    if not required.issubset(categories):
        raise ReviewRequired("missing diagnostic log categories: " + ", ".join(sorted(required - categories)))
    return {"times": times, "events": events, "categories": sorted(categories),
            "timing_record": time_file.read_text()[:4000]}


def result_times(case):
    result = {}
    for path in case.iterdir():
        if path.is_dir() and NUMBER.fullmatch(path.name):
            time = finite_number(path.name)
            if time > 0:
                if time in result:
                    raise ComparisonFailure("duplicate numeric time directory")
                result[time] = path
    if not result or not any(math.isclose(t, 1e-7, rel_tol=1e-12, abs_tol=1e-16) for t in result):
        raise ComparisonFailure("missing new/final result directory")
    return result


def compare_uniform_directory(directory_a, directory_b, atol, rtol):
    """Compare native dictionary artifacts; never silently skip uniform/."""
    if directory_a.exists() != directory_b.exists():
        raise ComparisonFailure("uniform subdirectory presence differs")
    if not directory_a.exists():
        return {"present": False, "files": {}}
    if not directory_a.is_dir() or not directory_b.is_dir():
        raise ComparisonFailure("uniform must be a directory")
    paths_a = {p.name: p for p in directory_a.iterdir()}
    paths_b = {p.name: p for p in directory_b.iterdir()}
    if set(paths_a) != set(paths_b):
        raise ComparisonFailure("uniform file sets differ")
    result = {"present": True, "files": {}, "exclusions": []}
    for name in sorted(paths_a):
        pa, pb = paths_a[name], paths_b[name]
        if pa.is_symlink() or pb.is_symlink():
            raise ComparisonFailure("symlink in uniform subdirectory")
        if not pa.is_file() or not pb.is_file():
            raise ReviewRequired("nested/non-file uniform artifact: " + name)
        parser_a, parser_b = Parser(read_ascii(pa)), Parser(read_ascii(pb))
        ha, hb = parser_a.header(), parser_b.header()
        if ha["class"] != hb["class"]:
            raise ComparisonFailure("uniform artifact class differs: " + name)
        da, db = parser_a.dictionary(), parser_b.dictionary()
        compare_tree(da, db, atol, rtol, "uniform/" + name)
        # No runtime metadata entries are discarded; if a future solver writes
        # nondeterministic data here it requires an explicit reviewed policy.
        result["files"][name] = {"class": ha["class"][0], "dictionary_compared": True,
                                "exact_equal_tokens": da == db}
    return result


def compare_runs(run_dir, atol=1e-12, rtol=1e-10):
    report = {"status": "PASS", "scope": "pure-copy rename equivalence; no physical conservation closure",
              "atol": atol, "rtol": rtol, "issues": [], "fields": {}, "uniform": {},
              "conservation_note": "Alpha bounds and volume-fraction log events are compared. No phase-flux or thermal-energy budget is integrated."}
    a, b = Path(run_dir) / "A", Path(run_dir) / "B"

    def issue(status, message):
        report["issues"].append({"status": status, "message": message})
        if status == "FAIL" or report["status"] == "PASS":
            report["status"] = status

    try:
        if not a.is_dir() or not b.is_dir():
            raise ComparisonFailure("run directory must contain A and B")
        report["manifests"] = check_manifests(a, b)
        ga, gb = mesh_geometry(a), mesh_geometry(b)
        if ga != gb:
            raise ReviewRequired("mesh geometry/counts differ")
        report["geometry"] = ga
        la, lb = parse_log(a, "laserbeamFoam"), parse_log(b, "aiLaserbeamFoam")
        if la["times"] != lb["times"]:
            raise ComparisonFailure("Time event lists differ")
        if len(la["events"]) != len(lb["events"]):
            raise ComparisonFailure("diagnostic log event counts differ")
        log_comparisons = []
        for index, (ea, eb) in enumerate(zip(la["events"], lb["events"])):
            if ea["kind"] != eb["kind"] or ea["label"] != eb["label"]:
                raise ComparisonFailure("diagnostic log event order/label differs at " + str(index))
            stats = numeric_statistics(ea["values"], eb["values"], atol, rtol)
            log_comparisons.append({"kind": ea["kind"], "label": ea["label"],
                                    "A": ea["values"], "B": eb["values"], "difference": stats})
            if not stats["within_tolerance"]:
                issue("FAIL", "diagnostic log numeric difference at event " + str(index))
        report["logs"] = {"times": la["times"], "compared_events": len(la["events"]),
                          "events": log_comparisons,
                          "exact_equal": all(event["difference"]["exact_equal"] for event in log_comparisons),
                          "time_increments": [la["times"][0]] + [y - x for x, y in zip(la["times"], la["times"][1:])],
                          "categories": la["categories"], "A_timing_record": la["timing_record"],
                          "B_timing_record": lb["timing_record"]}
        ta, tb = result_times(a), result_times(b)
        if set(ta) != set(tb):
            raise ComparisonFailure("result time directory sets differ")
        if not set(ta).issubset(set(la["times"])):
            raise ComparisonFailure("output time is absent from solver Time trajectory")
        for time in sorted(ta):
            if any(p.is_symlink() for directory in (ta[time], tb[time]) for p in directory.iterdir()):
                raise ComparisonFailure("symlink in result directory")
            files_a = {p.name for p in ta[time].iterdir() if p.is_file()}
            files_b = {p.name for p in tb[time].iterdir() if p.is_file()}
            if files_a != files_b:
                raise ComparisonFailure("field file sets differ at time " + str(time))
            if not REQUIRED_FIELDS.issubset(files_a):
                raise ComparisonFailure("missing required fields at time {}: {}".format(time, sorted(REQUIRED_FIELDS - files_a)))
            if any(p.is_dir() and p.name != "uniform" for p in ta[time].iterdir()) or any(p.is_dir() and p.name != "uniform" for p in tb[time].iterdir()):
                raise ReviewRequired("unexpected result subdirectory; dynamic/distributed meshes are unsupported")
            report["uniform"][str(time)] = compare_uniform_directory(ta[time] / "uniform", tb[time] / "uniform", atol, rtol)
            report["fields"][str(time)] = {}
            for name in sorted(files_a):
                try:
                    field_report = compare_fields(ta[time] / name, tb[time] / name, ga, atol, rtol)
                    report["fields"][str(time)][name] = field_report
                    stats = [field_report["internal"]]
                    stats.extend(stat for patch in field_report["patches"].values() for stat in patch["values"].values())
                    if not all(stat["within_tolerance"] for stat in stats):
                        issue("FAIL", "field exceeds tolerance: {}/{}".format(time, name))
                except ComparisonFailure as exc:
                    issue("FAIL", "{}/{}: {}".format(time, name, exc))
                except (ReviewRequired, ValueError, IndexError, TypeError) as exc:
                    issue("REVIEW_REQUIRED", "{}/{}: {}".format(time, name, exc))
    except ComparisonFailure as exc:
        issue("FAIL", str(exc))
    except (ReviewRequired, OSError, UnicodeError, ValueError, IndexError, TypeError) as exc:
        issue("REVIEW_REQUIRED", str(exc))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-12)
    parser.add_argument("--rtol", type=float, default=1e-10)
    args = parser.parse_args(argv)
    if not args.run_dir.is_dir():
        parser.error("--run-dir must already exist")
    if not all(math.isfinite(x) and x >= 0 for x in (args.atol, args.rtol)):
        parser.error("tolerances must be finite and non-negative")
    report = compare_runs(args.run_dir, args.atol, args.rtol)
    (args.run_dir / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["Status: " + report["status"], "Scope: " + report["scope"],
             "Tolerance: atol={}, rtol={}".format(args.atol, args.rtol), report["conservation_note"]]
    lines.extend("{}: {}".format(item["status"], item["message"]) for item in report["issues"])
    lines.append("Detailed internal/patch errors, manifests and log counts: comparison.json")
    (args.run_dir / "comparison.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report["status"])
    return {"PASS": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
