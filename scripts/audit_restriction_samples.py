#!/usr/bin/env python3
"""Final five-parent read-only restriction audit; no CFD or field writes."""
from array import array
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import resource
import signal
import subprocess
import time

import compare_plate2d_ab as native
import compare_m1_m3 as cross
import m1_ic

ROOT = Path(__file__).resolve().parents[1]
KEYS = [(6,6,7), (19,6,7), (33,6,7), (19,5,7), (19,7,7)]


def records(path, expected):
    """Stream the already hash-verified native one-record-per-line mesh lists."""
    with path.open() as stream:
        header = []
        for line in stream:
            if line.strip().isdigit():
                count = int(line)
                break
            header.append(line)
        else:
            raise ValueError("missing native list count")
        text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", "".join(header), flags=re.S)
        p = native.Parser(text)
        h = p.header()
        p.done()
        assert h["class"] == [expected]
        assert stream.readline().strip() == "("
        for _ in range(count):
            yield stream.readline().strip()
        assert stream.readline().strip() in (")", ");")


def sample_geometry(case, shape, keys):
    mesh = case/"constant/polyMesh"
    coords = [array('d'), array('d'), array('d')]
    decimal_tokens = [{}, {}, {}]
    for line in records(mesh/"points", "vectorField"):
        assert line.startswith("(") and line.endswith(")")
        tokens = line[1:-1].split()
        assert len(tokens) == 3
        for a, token in enumerate(tokens):
            value = native.finite_number(token)
            coords[a].append(value)
            decimal_tokens[a].setdefault(value, token)
    scale = max(max(abs(x) for x in axis) for axis in coords)
    tol = 128*math.ulp(scale)
    axes, exact_axes, indices = [], [], []
    for a in range(3):
        groups = []
        for value in sorted(decimal_tokens[a]):
            if not groups or value-groups[-1][0] > tol:
                groups.append([value])
            else:
                groups[-1].append(value)
        axes.append([math.fsum(g)/len(g) for g in groups])
        exact_axes.append([sum((F(decimal_tokens[a][x]) for x in g), F(0))/len(g) for g in groups])
        indices.append({x:i for i,g in enumerate(groups) for x in g})
        assert len(groups) == shape[a]+1
    wanted = {tuple(k+d for k,d in zip(key, offset)) for key in keys
              for offset in itertools.product((0,1), repeat=3)}
    selected = {}
    for i in range(len(coords[0])):
        key = tuple(indices[a][coords[a][i]] for a in range(3))
        if key in wanted:
            assert key not in selected.values()
            selected[i] = key
    assert set(selected.values()) == wanted
    owner = native.label_list(mesh/"owner")
    neighbour = native.label_list(mesh/"neighbour")
    faces_by_cell = {}
    face_count = 0
    for face, line in enumerate(records(mesh/"faces", "faceList")):
        face_count += 1
        assert line.startswith("4(") and line.endswith(")")
        labels = line[2:-1].split()
        if int(labels[0]) not in selected:
            continue
        ids = [int(x) for x in labels]
        if not all(i in selected for i in ids):
            continue
        assert len(ids) == 4
        positions = [selected[i] for i in ids]
        low = tuple(min(p[a] for p in positions) for a in range(3))
        high = tuple(max(p[a] for p in positions) for a in range(3))
        axis = tuple(h-l for l,h in zip(low,high)).index(0)
        for cell in ([owner[face], neighbour[face]] if face < len(neighbour) else [owner[face]]):
            faces_by_cell.setdefault(cell, []).append((axis,low,high))
    assert face_count == len(owner)
    result = {}
    for cell, faces in faces_by_cell.items():
        if len(faces) != 6:
            continue
        lo = tuple(min(f[1][a] for f in faces) for a in range(3))
        hi = tuple(max(f[2][a] for f in faces) for a in range(3))
        if lo not in keys:
            continue
        assert tuple(h-l for l,h in zip(lo,hi)) == (1,1,1)
        assert {(a,l[a]) for a,l,h in faces} == {(a,x) for a in range(3) for x in (lo[a],hi[a])}
        lengths = [axes[a][hi[a]]-axes[a][lo[a]] for a in range(3)]
        exact_lengths = [exact_axes[a][hi[a]]-exact_axes[a][lo[a]] for a in range(3)]
        result[lo] = {"native_cell":cell, "centre":[(axes[a][hi[a]]+axes[a][lo[a]])/2 for a in range(3)],
                      "volume":math.prod(lengths), "lengths":lengths,
                      "exact_ascii_volume":math.prod(exact_lengths),
                      "exact_y_bounds":[str(exact_axes[1][lo[1]]), str(exact_axes[1][hi[1]])]}
    assert set(result) == set(keys)
    return result, {"shape":shape,"bounds":[[a[0],a[-1]] for a in axes],"tolerance":8*tol}


def restriction_numbers(alpha, volumes, ascii_volumes):
    # Match m1_ic.volume_restriction: rounded products, fsum, rounded division.
    numerator = math.fsum(a*v for a,v in zip(alpha,volumes))
    denominator = math.fsum(volumes)
    actual = numerator/denominator
    exact_v = sum((F(a)*F(v) for a,v in zip(alpha,volumes)),F(0))/sum(map(F,volumes),F(0))
    exact_ascii = sum((F(a)*v for a,v in zip(alpha,ascii_volumes)),F(0))/sum(ascii_volumes,F(0))
    before = math.fsum((a>=0.5)*v for a,v in zip(alpha,volumes))/denominator
    return {"actual_numerator":numerator,"actual_denominator":denominator,"actual_restricted_alpha":actual,
            "binary_volume_exact_mean":str(exact_v),"binary_volume_exact_minus_half":str(exact_v-F(1,2)),
            "binary_volume_exact_minus_half_float":float(exact_v-F(1,2)),
            "ascii_coordinate_exact_mean":str(exact_ascii),"ascii_coordinate_exact_minus_half_float":float(exact_ascii-F(1,2)),
            "final_reduction_rounding_error_float":float(F(actual)-exact_v),
            "rounding_crosses_binary_volume_exact_gate":(actual>=0.5)!=(exact_v>=F(1,2)),
            "rounding_crosses_ascii_coordinate_exact_gate":(actual>=0.5)!=(exact_ascii>=F(1,2)),
            "threshold_then_restrict":before,"restrict_then_threshold":int(actual>=0.5),
            "commutator_actual":int(actual>=0.5)-before,
            "exact_binary_commutator":str(int(exact_v>=F(1,2))-exact_v),
            "ideal_equal_volume_alpha":sum(alpha)/8,
            "ideal_equal_volume_threshold_then_restrict":sum(a>=0.5 for a in alpha)/8,
            "ideal_equal_volume_restrict_then_threshold":int(sum(map(F,alpha),F(0))/8>=F(1,2))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-repo",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    source=args.source_repo.resolve(strict=True); out=args.out.resolve()
    assert out.is_relative_to(ROOT/"validation") and not out.exists() and not out.is_relative_to(source)
    out.mkdir(parents=True)
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    def stop(*_):
        raise TimeoutError("8.5-second analysis deadline; reserve final hashes")
    signal.signal(signal.SIGALRM,stop); signal.signal(signal.SIGTERM,stop); signal.setitimer(signal.ITIMER_REAL,8.5)
    report={"status":"INCONCLUSIVE","tool_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
            "parents":[],"sources_sha256":{},"sha_unchanged":False,
            "scope":"Five initial parent cells and forty children only; no CFD or alpha modification"}
    files={}
    try:
        cases={label:source/"runs"/f"threeD-{label}-001" for label in ("M1-IC","M3")}
        for label,case in cases.items():
            for rel in ("0/alpha.metal","manifest.json",*("constant/polyMesh/"+n for n in ("points","faces","owner","neighbour","boundary"))):
                files[label+"/"+rel]=case/rel
        files["M1-IC/reference.json"]=cases["M1-IC"]/m1_ic.REFERENCE
        for rel in ("scripts/m1_ic.py","scripts/check_m_case.py","scripts/compare_m1_m3.py","scripts/compare_plate2d_ab.py","scripts/audit_restriction_samples.py","docs/validation/optical-threshold-20261017.json"):
            files["tool/"+rel]=ROOT/rel
        for path in files.values():
            assert path.is_file() and not any(x.is_symlink() for x in (path,*path.parents))
        report["sources_sha256"]={name:cross.digest(path) for name,path in files.items()}
        previous=json.loads(files["tool/docs/validation/optical-threshold-20261017.json"].read_text())
        assert all(previous["sources_sha256"][name]==h for name,h in report["sources_sha256"].items()
                   if "/constant/polyMesh/" in name or name.endswith("/0/alpha.metal"))
        manifest=json.loads((cases["M1-IC"]/"manifest.json").read_text())
        assert report["sources_sha256"]["M1-IC/reference.json"]==manifest["reference_sha256"]
        ref=json.loads(files["M1-IC/reference.json"].read_text())
        fine_keys=[tuple(2*k+d for k,d in zip(key,offset)) for key in KEYS for offset in itertools.product((0,1),repeat=3)]
        coarse,cg=sample_geometry(cases["M1-IC"],[40,20,40],KEYS)
        fine,fg=sample_geometry(cases["M3"],[80,40,80],fine_keys)
        initial={label:native.expand_field(native.parse_field(case/"0/alpha.metal")["internal"],math.prod([40,20,40] if label=="M1-IC" else [80,40,80]),1,"scalar") for label,case in cases.items()}
        cg.update(lookup={k:i for i,k in enumerate(KEYS)},centres=[coarse[k]["centre"] for k in KEYS],volumes=[coarse[k]["volume"] for k in KEYS])
        fg.update(lookup={k:i for i,k in enumerate(fine_keys)},centres=[fine[k]["centre"] for k in fine_keys],volumes=[fine[k]["volume"] for k in fine_keys])
        alphas=[initial["M3"][fine[k]["native_cell"]] for k in fine_keys]
        reproduced,_=m1_ic.volume_restriction(cg,fg,alphas)
        ref_lookup={tuple(round((x-ref["mesh"]["bounds_m"][a][0])/((ref["mesh"]["bounds_m"][a][1]-ref["mesh"]["bounds_m"][a][0])/ref["shape"][a])-0.5) for a,x in enumerate(c)):i for i,c in enumerate(ref["centres"])}
        for parent,key in enumerate(KEYS):
            children=[tuple(2*k+d for k,d in zip(key,offset)) for offset in itertools.product((0,1),repeat=3)]
            aa=[initial["M3"][fine[k]["native_cell"]] for k in children]
            vv=[fine[k]["volume"] for k in children]
            av=[fine[k]["exact_ascii_volume"] for k in children]
            numbers=restriction_numbers(aa,vv,av)
            original=initial["M1-IC"][coarse[key]["native_cell"]]
            assert numbers["actual_restricted_alpha"]==reproduced[parent]==original==ref["alpha"][ref_lookup[key]]
            assert coarse[key]["volume"]==ref["volumes"][ref_lookup[key]]
            row={"key":key,"native_parent_cell":coarse[key]["native_cell"],"centre_m":coarse[key]["centre"],
                 "parent_volume":coarse[key]["volume"],"saved_alpha":original,**numbers,"children":[]}
            for ck,a,v,ve in zip(children,aa,vv,av):
                row["children"].append({"key":ck,"native_cell":fine[ck]["native_cell"],"alpha":a,"volume":v,
                    "lengths":fine[ck]["lengths"],"exact_ascii_y_bounds":fine[ck]["exact_y_bounds"],
                    "exact_ascii_volume":str(ve),"actual_product":a*v,"weight_float":v/numbers["actual_denominator"]})
            report["parents"].append(row)
        historical=subprocess.check_output(["git","show",manifest["project_commit"]+":scripts/m1_ic.py"],cwd=ROOT)
        assert historical==(ROOT/"scripts/m1_ic.py").read_bytes()
        report["restriction_runtime_commit"]=manifest["project_commit"]
        report["status"]="SAMPLED_RESTRICTION_DIAGNOSIS_COMPLETED"
    except (MemoryError,TimeoutError,AssertionError,ValueError,OSError,native.ReviewRequired,native.ComparisonFailure) as exc:
        report["error"]=type(exc).__name__+": "+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        changed=[n for n,h in report["sources_sha256"].items() if cross.digest(files[n])!=h]
        report["sha_unchanged"]=bool(report["sources_sha256"]) and not changed
        report["changed_sources"]=changed
        report["wall_seconds"]=time.monotonic()-start
        report["max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if changed or report["wall_seconds"]>10 or report["max_rss_kib"]>262144:
            report["status"]="INCONCLUSIVE"
        (out/"diagnosis.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report["status"],report["wall_seconds"],"s",report["max_rss_kib"],"KiB",report.get("error",""))
    return 0 if report["status"]=="SAMPLED_RESTRICTION_DIAGNOSIS_COMPLETED" and report["sha_unchanged"] else 2


if __name__=="__main__":
    raise SystemExit(main())
