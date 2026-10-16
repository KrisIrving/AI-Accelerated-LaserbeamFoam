#!/usr/bin/env bash
# Native serial stages. Only user execution starts OpenFOAM; never DEM or cleanup.
set -Eeuo pipefail
export LC_ALL=C
stage=startup
fail() { printf 'ERROR [%s] %s\n' "$stage" "$*" >&2; exit 2; }
trap 'rc=$?; printf "ERROR [%s] exit %s at line %s; retain case/logs\n" "$stage" "$rc" "$LINENO" >&2; exit "$rc"' ERR
[[ $# == 3 && $1 == --case-dir && ( $3 == mesh || $3 == solve ) ]] || fail 'Usage: Allrun mesh | Allrun solve'
cd -- "$2"
action=$3
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
stage=manifest
[[ -f manifest.json && ! -L manifest.json ]] || fail 'Missing or symlinked manifest.json'
sha256sum -c metadata.sha256 > metadata.verify.txt 2>&1 || fail 'Prepared metadata changed'
# Fixed-key NUL records; no eval or sourcing run-directory shell metadata.
mapfile -d '' -t metadata < <(PYTHONIOENCODING=utf-8 python3 - <<'PY'
import json
m = json.load(open('manifest.json', encoding='utf-8'))
for value in (m['build_dir'], m['project_commit'], m['WM_OPTIONS'], m['solver'],
              m['config']['mesh_timeout_seconds'], m['config']['solver_timeout_seconds']):
    print(value, end='\0')
PY
)
[[ ${#metadata[@]} == 6 ]] || fail 'Invalid manifest metadata'
build=${metadata[0]}; commit=${metadata[1]}; options=${metadata[2]}; solver=${metadata[3]}
mesh_timeout=${metadata[4]}; solver_timeout=${metadata[5]}
[[ $solver == laserbeamFoam || $solver == aiLaserbeamFoam ]] || fail 'Unsupported solver'
[[ $mesh_timeout =~ ^[1-9][0-9]*$ && $solver_timeout =~ ^[1-9][0-9]*$ ]] || fail 'Invalid time budget'
stage=environment
[[ ${WM_PROJECT_VERSION-} == v2512 && ${WM_OPTIONS-} == "$options" && -d ${WM_PROJECT_DIR-}/bin/tools ]] || fail 'Load matching of2512 environment first'
for tool in python3 sha256sum ldd timeout blockMesh checkMesh setFields; do command -v "$tool" >/dev/null || fail "Missing tool: $tool"; done
[[ -x /usr/bin/time && -f $build/env.sh ]] || fail 'GNU time or build activation missing'
build=$(realpath -e -- "$build")
[[ $build == "$repo/validation/"* ]] || fail 'Build is outside this checkout/validation'
[[ $(git -C "$repo" rev-parse HEAD) == "$commit" ]] || fail 'Checkout changed since preparation; preserve case and prepare a fresh one'
git -C "$repo" diff --quiet HEAD -- src applications scripts benchmarks || fail 'Uncommitted executable inputs; commit before preparing'
grep -Fxq "project_commit=$commit" "$build/summary.txt" || fail 'Build commit differs'
source "$build/env.sh"
[[ $FOAM_USER_APPBIN == "$build/install/bin" && $FOAM_USER_LIBBIN == "$build/install/lib" ]] || fail 'Unexpected installation paths'
stage=build-integrity
sha256sum -c "$build/binary.sha256" > binaries.verify.txt 2>&1 || fail 'Binary checksum mismatch'
sha256sum -c "$build/custom-libraries.sha256" > libraries.verify.txt 2>&1 || fail 'Library checksum mismatch'
program="$FOAM_USER_APPBIN/$solver"
[[ -x $program ]] || fail 'Selected executable missing'
ldd "$program" > ldd.runtime.txt 2>&1 || fail 'ldd failed'
if grep -q 'not found' ldd.runtime.txt; then fail 'Unresolved library'; fi
awk '$2 == "=>" {print $1 "\t" $3}' ldd.runtime.txt | sort > dependencies.runtime.tsv
sort "$build/dependencies.$solver.tsv" > dependencies.expected.tsv
diff -u dependencies.expected.tsv dependencies.runtime.tsv > dependencies.diff.txt || fail 'Actual library origins differ from build'
awk -v libdir="$FOAM_USER_LIBBIN" '
    $1=="libMTHD.so" || $1=="liblaserHeatSource.so" {seen++; if ($2!=libdir "/" $1) wrong=1}
    END {exit (seen!=2 || wrong)}' dependencies.runtime.tsv || fail 'Custom libraries outside selected installation'
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
stage=fresh-results
for path in ./*; do
    name=${path##*/}
    if [[ -d $path && ( $name == processor* || ( $name != 0 && $name =~ ^[0-9.+-]+([eE][+-]?[0-9]+)?$ ) ) ]]; then
        fail "Existing evolved/parallel directory: $name"
    fi
done
run_step() {
    stage=$1; shift
    local limit=$1 rc; shift
    [[ ! -e log.$stage && ! -L log.$stage ]] || fail 'Refusing to overwrite stage log'
    if /usr/bin/time -v -o "time.$stage.txt" timeout --signal=TERM --kill-after=10s "${limit}s" "$@" > "log.$stage" 2>&1; then rc=0; else rc=$?; fi
    printf '%s\n' "$rc" > "exit.$stage.txt"
    if [[ $stage == "$solver" ]]; then
        cp "exit.$stage.txt" solver.exit.txt
        cp "time.$stage.txt" solver.time.txt
    fi
    ((rc == 0)) || { printf 'ERROR [%s] exit %s; see log.%s and time.%s.txt\n' "$stage" "$rc" "$stage" "$stage" >&2; exit "$rc"; }
}
if [[ $action == mesh ]]; then
    stage=fresh-case
    for path in 0 constant/polyMesh .mesh-started .solve-started; do [[ ! -e $path && ! -L $path ]] || fail "Refusing to overwrite $path"; done
    bash "$repo/scripts/verify_plate2d_inputs.sh" --case-dir "$PWD"
    mkdir .mesh-started
    cp -a initial 0
    run_step blockMesh "$mesh_timeout" blockMesh
    run_step checkMesh "$mesh_timeout" checkMesh
    grep -q 'Mesh OK' log.checkMesh || fail 'Mesh check did not report Mesh OK'
    run_step setFields "$mesh_timeout" setFields
    find constant/polyMesh 0 -type f -print0 | sort -z | xargs -0 sha256sum > initialized.sha256
    touch .mesh-complete
    printf 'MESH_INITIALIZED; no solver run. Next: bash Allrun solve\n'
else
    stage=initialized-inputs
    [[ -f .mesh-complete && ! -e .solve-started && ! -L .solve-started ]] || fail 'Mesh incomplete or solver already attempted; use a fresh case after failure'
    [[ -z $(find initial constant system 0 -type l -print -quit) ]] || fail 'Symlinked input'
    # Mesh generation adds files to constant: verify the immutable input records
    # and the full initialized snapshot separately instead of changing manifests.
    sha256sum -c inputs.sha256 > inputs.solve.verify.txt 2>&1 || fail 'Prepared input modified'
    sha256sum -c initialized.sha256 > initialized.verify.txt 2>&1 || fail 'Initialized mesh/fields modified'
    python3 "$repo/scripts/check_smoke_case.py" --case-dir "$PWD" --inputs-only
    mkdir .solve-started
    printf 'program=%s\nmpi_ranks=1\nthreads=1\nsolver_timeout_seconds=%s\n' "$program" "$solver_timeout" > execution.txt
    run_step "$solver" "$solver_timeout" "$program"
    stage=smoke-check
    python3 "$repo/scripts/check_smoke_case.py" --case-dir "$PWD"
fi
