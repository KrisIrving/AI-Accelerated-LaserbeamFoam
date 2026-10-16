#!/usr/bin/env python3
"""Conservative, offline comparison of the prepared Plate2D A/B runs.

This checks rename equivalence, not conservation closure or CFD validation.
Native ASCII fields are compared on the same serial mesh. Unsupported uniform
state files may pass by explicit byte identity; unsupported fields never do.
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
TRAPFPE_STARTUP = re.compile(
    r"trapFpe:\s+Floating point exception trapping enabled(?:\s+\(FOAM_SIGFPE\))?\.?", re.I)
FATAL_LOG_MARKERS = (
    ("FOAM FATAL ERROR", re.compile(r"\bFOAM FATAL(?: IO)? ERROR\b", re.I)),
    ("floating-point exception", re.compile(
        r"\bFloating point exception\b|\bSIGFPE\b|\bFoam::sigFpe::sigHandler(?:Action)?\b", re.I)),
    ("segmentation fault", re.compile(r"\bSegmentation fault\b|\bSIGSEGV\b", re.I)),
    ("MPI_ABORT", re.compile(r"\bMPI_ABORT\b", re.I)),
    ("Traceback", re.compile(r"(?:^\s*|\]\s*)Traceback\b|\bTraceback\s*\(most recent call last\):", re.I)),
)


class ReviewRequired(Exception):
    pass


class ComparisonFailure(Exception):
    def __init__(self, message, context=None):
        super().__init__(message)
        self.context = context


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
    allowed = {"dimensions", "internalField", "boundaryField"}
    if field_class == "surfaceScalarField":
        allowed.add("oriented")
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ReviewRequired("{}: unsupported extra top-level field entries for {}: {}".format(
            path, field_class, ", ".join(unknown)))
    orientation = {"present": "oriented" in data, "value": None}
    if orientation["present"]:
        entry = data["oriented"]
        # OpenFOAM-v2512 orientedType.C registers exactly these enum words.
        # Do not apply its failsafe fallback for unknown words during auditing.
        if (not isinstance(entry, list) or len(entry) != 1
                or not isinstance(entry[0], str)
                or entry[0] not in ("unknown", "oriented", "unoriented")):
            raise ComparisonFailure("{}: invalid oriented entry {!r}; expected one of: unknown, oriented, unoriented".format(path, entry))
        orientation["value"] = entry[0]
    dims = data["dimensions"]
    if len(dims) != 1 or not isinstance(dims[0], list) or len(dims[0]) != 7:
        raise ReviewRequired("invalid dimensions")
    dimensions = [finite_number(value) for value in dims[0]]
    if not isinstance(data["boundaryField"], dict):
        raise ReviewRequired("boundaryField is not a dictionary")
    return {"class": field_class, "location": match[1],
            "components": COMPONENTS[match[2]], "dimensions": dimensions,
            "orientation": orientation,
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
    relative = [d / max(abs(x), abs(y)) if max(abs(x), abs(y)) else 0.0
                for x, y, d in zip(a, b, differences)]
    return {"count": len(a), "max_abs": max(differences, default=0.0),
            "max_relative": max(relative, default=0.0),
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
    if a["orientation"]["present"] != b["orientation"]["present"]:
        # DimensionedFieldIO.C can preserve a constructor-set ORIENTED flag.
        # A missing entry therefore cannot be mapped to an explicit flag here.
        raise ReviewRequired("oriented presence differs: A={!r}, B={!r}; missing-entry state cannot be inferred without construction context".format(
            a["orientation"], b["orientation"]))
    if a["orientation"]["value"] != b["orientation"]["value"]:
        raise ComparisonFailure("oriented differs: A={!r}, B={!r}".format(
            a["orientation"]["value"], b["orientation"]["value"]))
    count = geometry["cells" if a["location"] == "vol" else "internal_faces"]
    element_type = a["class"][len(a["location"]):-len("Field")]
    element_type = element_type[0].lower() + element_type[1:]
    av = expand_field(a["internal"], count, a["components"], element_type)
    bv = expand_field(b["internal"], count, b["components"], element_type)
    result = {"class": a["class"], "internal": numeric_statistics(av, bv, atol, rtol), "patches": {}}
    if a["class"] == "surfaceScalarField":
        result["orientation"] = {"A": a["orientation"], "B": b["orientation"]}
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
    log = case / ("log." + application)

    def fail_log(message, line_number=None, matched_line=None, marker=None):
        context = {"variant": case.name, "log_file": str(log)}
        location = "{}: {}".format(case.name, log)
        if line_number is not None:
            context.update(line_number=line_number, matched_line=matched_line, marker=marker)
            location += ":{}".format(line_number)
            message += ": " + matched_line
        raise ComparisonFailure(location + ": " + message, context)

    if not log.is_file():
        fail_log("missing solver log")
    exit_ok = exit_file.is_file() and exit_file.read_text().strip() == "0"
    try:
        lines = log.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError):
        if not exit_ok:
            fail_log("missing/nonzero solver exit status and unreadable log; see " + str(exit_file))
        raise
    # Only the complete known startup line is benign. Never discard a line
    # merely because it contains trapFpe/FOAM_SIGFPE: it may also contain an error.
    # Scan before exit/End checks so real crashes retain their first error line.
    for line_number, line in enumerate(lines, 1):
        if TRAPFPE_STARTUP.fullmatch(line.strip()):
            continue
        for marker, pattern in FATAL_LOG_MARKERS:
            if pattern.search(line):
                fail_log("fatal log event ({})".format(marker), line_number, line, marker)
    if not exit_ok:
        fail_log("missing/nonzero solver exit status; see " + str(exit_file))
    if not time_file.is_file() or not time_file.read_text().strip():
        raise ReviewRequired("missing solver.time.txt")
    nonempty = [line.strip() for line in lines if line.strip()]
    if not nonempty or nonempty[-1] != "End":
        fail_log("solver log does not terminate normally with End")
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
        if path.is_symlink() and NUMBER.fullmatch(path.name):
            raise ComparisonFailure("symlink output time directory: " + str(path))
        if path.is_dir() and NUMBER.fullmatch(path.name):
            time = finite_number(path.name)
            if time > 0:
                if time in result:
                    raise ComparisonFailure("duplicate numeric time directory")
                result[time] = path
    if not result or not any(math.isclose(t, 1e-7, rel_tol=1e-12, abs_tol=1e-16) for t in result):
        raise ComparisonFailure("missing new/final result directory")
    return result


def uniform_inventory(directory):
    """Record directories (including empty ones) without following links."""
    entries = {}

    def visit(path, relative):
        if path.is_symlink():
            location = "uniform/" + relative
            raise ComparisonFailure(location + ": symlink is not accepted", {"path": location})
        if path.is_dir():
            entries[relative] = "directory"
            for child in sorted(path.iterdir()):
                visit(child, relative + "/" + child.name if relative else child.name)
        elif path.is_file():
            entries[relative] = "file"
        else:
            raise ReviewRequired("uniform/{}: unsupported non-regular entry".format(relative))

    visit(directory, "")
    return entries


def uniform_file_comparison(pa, pb, geometry, atol, rtol):
    """Interpret supported data first; byte fallback is limited to state files."""
    data_a, data_b = pa.read_bytes(), pb.read_bytes()
    identical = data_a == data_b

    def class_hint(data):
        # Classification only, also for binary fields. The actual field must
        # still pass the native parser, never a byte-only shortcut.
        text = re.sub(rb"/\*.*?\*/|//[^\n]*", b" ", data, flags=re.S)
        header = re.search(rb"\bFoamFile\s*\{([^}]*)\}", text)
        match = re.search(rb"\bclass\s+([^;\s]+)\s*;", header[1]) if header else None
        return match[1].decode("ascii", errors="replace") if match else ""

    classes = [class_hint(data) for data in (data_a, data_b)]
    if any(re.fullmatch(r"(?:vol|surface)\w*Field", value) for value in classes):
        if geometry is None:
            raise ReviewRequired("mesh geometry is required for native uniform field")
        result = compare_fields(pa, pb, geometry, atol, rtol)
        stats = [result["internal"]] + [stat for patch in result["patches"].values() for stat in patch["values"].values()]
        result.update(method="NUMERICAL_SEMANTIC", byte_identical=identical,
                      status="PASS" if all(stat["within_tolerance"] for stat in stats) else "FAIL")
        return result

    def byte_fallback(reason):
        return {"method": "BYTE_IDENTICAL" if identical else "UNSUPPORTED",
                "status": "PASS" if identical else "REVIEW_REQUIRED",
                "byte_identical": identical, "reason": reason}

    try:
        parser_a, parser_b = Parser(read_ascii(pa)), Parser(read_ascii(pb))
        ha, hb = parser_a.header(), parser_b.header()
    except ReviewRequired as exc:
        return byte_fallback(str(exc))
    if ha["class"] != hb["class"]:
        raise ComparisonFailure("uniform artifact class differs")
    if ha["class"][0] not in ("dictionary", "IOdictionary"):
        return byte_fallback("unsupported uniform class: " + ha["class"][0])
    # Malformed supported dictionaries and non-finite/numerically different
    # values must not be concealed by identical bytes.
    da, db = parser_a.dictionary(), parser_b.dictionary()
    compare_tree(da, db, atol, rtol, "dictionary")
    return {"class": ha["class"][0], "method": "NUMERICAL_SEMANTIC",
            "status": "PASS", "byte_identical": identical,
            "dictionary_compared": True, "exact_equal_tokens": da == db}


def compare_uniform_directory(directory_a, directory_b, atol, rtol, geometry=None):
    """Check structure separately from content and retain all local issues."""
    result = {"present": directory_a.exists() or directory_b.exists(), "status": "PASS",
              "files": {}, "directories": [], "issues": [], "exclusions": []}

    def issue(status, path, message):
        result["issues"].append({"status": status, "path": path, "message": message})
        if status == "FAIL" or result["status"] == "PASS":
            result["status"] = status

    try:
        if directory_a.is_symlink() or directory_b.is_symlink():
            raise ComparisonFailure("uniform: symlink is not accepted")
        if directory_a.exists() != directory_b.exists():
            raise ComparisonFailure("uniform: subdirectory presence differs")
        if not result["present"]:
            return result
        if not directory_a.is_dir() or not directory_b.is_dir():
            raise ComparisonFailure("uniform: must be a directory on both sides")
        paths_a, paths_b = uniform_inventory(directory_a), uniform_inventory(directory_b)
        for name in sorted(set(paths_a) | set(paths_b)):
            path = "uniform/" + name
            if paths_a.get(name) != paths_b.get(name):
                issue("FAIL", path, "path/type differs: A={}, B={}".format(paths_a.get(name), paths_b.get(name)))
            elif paths_a[name] == "directory":
                if name:
                    result["directories"].append(name)
            else:
                try:
                    compared = uniform_file_comparison(directory_a / name, directory_b / name, geometry, atol, rtol)
                    result["files"][name] = compared
                    if compared["status"] != "PASS":
                        issue(compared["status"], path, compared.get("reason", "native field exceeds tolerance"))
                except ComparisonFailure as exc:
                    result["files"][name] = {"status": "FAIL", "method": "NUMERICAL_SEMANTIC", "reason": str(exc)}
                    issue("FAIL", path, str(exc))
                except (ReviewRequired, OSError, ValueError, IndexError, TypeError) as exc:
                    result["files"][name] = {"status": "REVIEW_REQUIRED", "method": "UNSUPPORTED", "reason": str(exc)}
                    issue("REVIEW_REQUIRED", path, str(exc))
    except ComparisonFailure as exc:
        issue("FAIL", (exc.context or {}).get("path", "uniform"), str(exc))
    except (ReviewRequired, OSError) as exc:
        issue("REVIEW_REQUIRED", "uniform", str(exc))
    return result


def compare_runs(run_dir, atol=1e-12, rtol=1e-10):
    report = {"status": "PASS", "scope": "pure-copy rename equivalence; no physical conservation closure",
              "atol": atol, "rtol": rtol, "issues": [], "fields": {}, "uniform": {},
              "output_files": {}, "fields_complete": False,
              "conservation_note": "Alpha bounds and volume-fraction log events are compared. No phase-flux or thermal-energy budget is integrated."}
    a, b = Path(run_dir) / "A", Path(run_dir) / "B"

    def issue(status, message, context=None):
        item = {"status": status, "message": message}
        if context:
            item.update(context)
        report["issues"].append(item)
        if status == "FAIL" or report["status"] == "PASS":
            report["status"] = status

    try:
        if a.is_symlink() or b.is_symlink():
            raise ComparisonFailure("A/B case directory must not be a symlink")
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
        fields_valid = True
        for time in sorted(ta):
            for directory in (ta[time], tb[time]):
                for path in directory.iterdir():
                    relative = path.relative_to(directory.parent).as_posix()
                    if path.is_symlink():
                        raise ComparisonFailure("symlink in result directory: " + relative, {"path": relative})
                    if path.is_dir() and path.name != "uniform":
                        issue("REVIEW_REQUIRED", "unsupported result subdirectory: " + relative, {"path": relative})
                    elif not path.is_dir() and not path.is_file():
                        issue("REVIEW_REQUIRED", "unsupported non-regular result entry: " + relative, {"path": relative})
            files_a = {p.name for p in ta[time].iterdir() if p.is_file() and p.name != "uniform"}
            files_b = {p.name for p in tb[time].iterdir() if p.is_file() and p.name != "uniform"}
            report["output_files"][str(time)] = {"A": sorted(files_a), "B": sorted(files_b)}
            if files_a != files_b:
                fields_valid = False
                for name in sorted(files_a ^ files_b):
                    path = "{}/{}".format(time, name)
                    issue("FAIL", "field missing from {}: {}".format("B" if name in files_a else "A", path), {"path": path, "stage": "fields"})
            missing = REQUIRED_FIELDS - (files_a & files_b)
            if missing:
                fields_valid = False
                issue("FAIL", "missing required fields at time {}: {}".format(time, sorted(missing)),
                      {"path": "{}/{}".format(time, sorted(missing)[0]), "stage": "fields"})
            uniform = compare_uniform_directory(ta[time] / "uniform", tb[time] / "uniform", atol, rtol, ga)
            report["uniform"][str(time)] = uniform
            for problem in uniform["issues"]:
                path = "{}/{}".format(time, problem["path"])
                issue(problem["status"], path + ": " + problem["message"], {"path": path, "stage": "uniform"})
            report["fields"][str(time)] = {}
            for name in sorted(files_a & files_b):
                path = "{}/{}".format(time, name)
                try:
                    field_report = compare_fields(ta[time] / name, tb[time] / name, ga, atol, rtol)
                    stats = [field_report["internal"]]
                    stats.extend(stat for patch in field_report["patches"].values() for stat in patch["values"].values())
                    passed = all(stat["within_tolerance"] for stat in stats)
                    field_report.update(method="NUMERICAL_SEMANTIC", status="PASS" if passed else "FAIL",
                                        byte_identical=(ta[time] / name).read_bytes() == (tb[time] / name).read_bytes())
                    report["fields"][str(time)][name] = field_report
                    if not passed:
                        fields_valid = False
                        issue("FAIL", "field exceeds tolerance: " + path, {"path": path, "stage": "fields"})
                except ComparisonFailure as exc:
                    fields_valid = False
                    report["fields"][str(time)][name] = {"status": "FAIL", "method": "NUMERICAL_SEMANTIC", "reason": str(exc)}
                    issue("FAIL", path + ": " + str(exc), {"path": path, "stage": "fields"})
                except (ReviewRequired, OSError, ValueError, IndexError, TypeError) as exc:
                    fields_valid = False
                    report["fields"][str(time)][name] = {"status": "REVIEW_REQUIRED", "method": "UNSUPPORTED", "reason": str(exc)}
                    issue("REVIEW_REQUIRED", path + ": " + str(exc), {"path": path, "stage": "fields"})
        report["fields_complete"] = fields_valid
    except ComparisonFailure as exc:
        issue("FAIL", str(exc), exc.context)
    except (ReviewRequired, OSError, UnicodeError, ValueError, IndexError, TypeError) as exc:
        issue("REVIEW_REQUIRED", str(exc))
    report["summary"] = comparison_summary(report)
    return report


def comparison_summary(report):
    """Counts describe completed checks, never infer success from byte counts."""
    fields = [entry for files in report["fields"].values() for entry in files.values()]
    uniform = [entry for result in report["uniform"].values() for entry in result["files"].values()]
    all_files = fields + uniform
    uniform_status = "NOT_CHECKED"
    if report["uniform"]:
        statuses = {result["status"] for result in report["uniform"].values()}
        uniform_status = "FAIL" if "FAIL" in statuses else "REVIEW_REQUIRED" if "REVIEW_REQUIRED" in statuses else "PASS"
    field_status = "NOT_CHECKED"
    if report["output_files"]:
        field_status = "PASS" if report["fields_complete"] else "REVIEW_REQUIRED"
        if any(p.get("stage") == "fields" and p["status"] == "FAIL" for p in report["issues"]):
            field_status = "FAIL"
    return {"simulation_steps": len(report.get("logs", {}).get("times", [])),
            "log_events": report.get("logs", {}).get("compared_events", 0),
            "input_files": report.get("manifests", {}).get("inputs.sha256", {}).get("verified_files"),
            "mesh_files": report.get("manifests", {}).get("mesh.sha256", {}).get("verified_files"),
            "output_times": sorted(report["output_files"], key=float),
            "physical_field_files": sum(len(set(files["A"]) | set(files["B"])) for files in report["output_files"].values()),
            "physical_field_files_compared": sum("internal" in entry for entry in fields),
            "physical_fields_status": field_status, "uniform_status": uniform_status,
            "uniform_files": len(uniform),
            "uniform_directories": sum(len(result["directories"]) for result in report["uniform"].values()),
            "byte_identical_files": sum(entry.get("byte_identical", False) for entry in all_files),
            "byte_only_files": sum(entry.get("method") == "BYTE_IDENTICAL" for entry in all_files),
            "semantic_pass_files": sum(entry.get("method") == "NUMERICAL_SEMANTIC" and entry["status"] == "PASS" for entry in all_files),
            "issue_count": len(report["issues"]),
            "first_issue": report["issues"][0] if report["issues"] else None}


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
    summary = report["summary"]
    lines = ["Status: " + report["status"], "Scope: " + report["scope"],
             "Tolerance: atol={}, rtol={}".format(args.atol, args.rtol), report["conservation_note"]]
    lines.extend([
        "Simulation steps: {}; compared log events: {}".format(summary["simulation_steps"], summary["log_events"]),
        "Inputs/mesh: {} / {} verified matching files (None = not completed)".format(summary["input_files"], summary["mesh_files"]),
        "Output times: {} ({})".format(len(summary["output_times"]), ", ".join(summary["output_times"])),
        "Physical fields: {} / {} compared; numerical status: {}".format(summary["physical_field_files_compared"], summary["physical_field_files"], summary["physical_fields_status"]),
        "Byte-identical files: {}; semantic passes: {}; byte-only passes: {}".format(summary["byte_identical_files"], summary["semantic_pass_files"], summary["byte_only_files"]),
        "Uniform tree: {}; files: {}; nested directories: {}".format(summary["uniform_status"], summary["uniform_files"], summary["uniform_directories"]),
        "Issues: {}".format(summary["issue_count"]),
    ])
    if summary["first_issue"]:
        item = summary["first_issue"]
        lines.append("First issue: {}: {}".format(item["status"], item["message"]))
    lines.append("Detailed internal/patch errors, manifests and log counts: comparison.json")
    (args.run_dir / "comparison.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report["status"])
    return {"PASS": 0, "FAIL": 1, "REVIEW_REQUIRED": 2}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
