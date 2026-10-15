#!/usr/bin/env bash
# Prepare native OpenFOAM test copies; never build, run a solver, or clean.
set -Eeuo pipefail
export LC_ALL=C
stage=preparation
trap 'rc=$?; printf "ERROR [%s] command failed at line %s (exit %s)\n" "$stage" "$LINENO" "$rc" >&2; exit "$rc"' ERR
usage() { echo 'Usage: bash scripts/prepare_plate2d_ab.sh --run-dir REPO/runs/NEW --build-dir REPO/validation/ROUND/build'; }
run_arg= build_arg=
while (($#)); do
    case "$1" in
        --run-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; run_arg=$2; shift 2 ;;
        --build-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; build_arg=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
[[ -n $run_arg && -n $build_arg ]] || { usage >&2; exit 2; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
baseline=3c93f2657e089e22e9a8298648292969e85a4bad
source_rel=tutorials/laserbeamFoam/Plate2D
source_dir="$repo/$source_rel"
build=$(realpath -e -- "$build_arg")
out=$(realpath -m -- "$run_arg")
run_root=$(realpath -m -- "$repo/runs")
[[ $out == "$run_root/"* && ! -e $out && ! -L $out ]] || { echo 'Choose a NEW directory inside this checkout/runs; existing data are never cleaned.' >&2; exit 2; }
[[ ${WM_PROJECT_VERSION-} == v2512 && -d ${WM_PROJECT_DIR-}/bin/tools ]] || { echo 'Load of2512 first.' >&2; exit 2; }
for tool in foamDictionary sha256sum ldd timeout; do command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }; done
[[ -x /usr/bin/time ]] || { echo 'GNU /usr/bin/time required.' >&2; exit 2; }
[[ -s $build/summary.txt && -f $build/env.sh ]] || { echo 'Build report missing.' >&2; exit 2; }
grep -q '^status=BUILD_ARTIFACT_CHECKS_PASSED;' "$build/summary.txt" || { echo 'Build has not passed artifact checks.' >&2; exit 2; }
commit=$(git -C "$repo" rev-parse HEAD)
grep -Fxq "project_commit=$commit" "$build/summary.txt" || { echo 'Build report is from another project commit; build both targets together first.' >&2; exit 2; }
grep -Fxq "WM_OPTIONS=${WM_OPTIONS-}" "$build/summary.txt" || { echo 'WM_OPTIONS differs from build.' >&2; exit 2; }
git -C "$repo" diff --quiet "$baseline" -- "$source_rel" || { echo 'Official source case differs from pinned baseline.' >&2; exit 2; }
git -C "$repo" diff --quiet HEAD -- src applications || { echo 'Uncommitted source changes: establish a recorded build first.' >&2; exit 2; }
[[ ! -e $source_dir/0 && ! -e $source_dir/constant/polyMesh ]] || { echo 'Official tutorial has generated data; do not clean it automatically. Use a fresh checkout.' >&2; exit 2; }
expected_inputs=$(git -C "$repo" ls-tree -r --name-only "$baseline" -- "$source_rel/initial" "$source_rel/constant" "$source_rel/system" | sed "s#^$source_rel/##" | sort)
actual_inputs=$(cd -- "$source_dir"; find initial constant system -type f | sort)
[[ -n $expected_inputs && $actual_inputs == "$expected_inputs" ]] || { echo 'Official case has missing or extra input files, including ignored/untracked inputs.' >&2; exit 2; }
[[ -z $(find "$source_dir/initial" "$source_dir/constant" "$source_dir/system" -type l -print -quit) ]] || { echo 'Symlinked source inputs are not accepted by this fixture.' >&2; exit 2; }
for entry in "$source_dir"/*; do
    name=${entry##*/}
    if [[ -d $entry && ( $name == processor* || $name =~ ^[0-9.+-]+([eE][+-]?[0-9]+)?$ ) ]]; then
        echo 'Official tutorial contains evolved/decomposed directories; use a fresh checkout.' >&2; exit 2
    fi
done
# Load only our generated build activation, never a user shell profile.
source "$build/env.sh"
[[ $FOAM_USER_APPBIN == "$build/install/bin" && $FOAM_USER_LIBBIN == "$build/install/lib" ]] || { echo 'Unexpected install paths in build activation.' >&2; exit 2; }
stage=build-integrity
sha256sum -c "$build/binary.sha256" >/dev/null || { echo 'ERROR [build-integrity] Binary checksum failed.' >&2; exit 2; }
sha256sum -c "$build/custom-libraries.sha256" >/dev/null || { echo 'ERROR [build-integrity] Library checksum failed.' >&2; exit 2; }
diff -q "$build/dependencies.laserbeamFoam.tsv" "$build/dependencies.aiLaserbeamFoam.tsv" || { echo 'ERROR [build-integrity] A/B dependency origins differ.' >&2; exit 2; }
mkdir -p -- "$out"
{
    echo 'schema=plate2d-ab-v1'
    printf 'project_commit=%s\nupstream_baseline=%s\nbuild_dir=%s\n' "$commit" "$baseline" "$build"
    printf 'WM_PROJECT_VERSION=%s\nWM_OPTIONS=%s\nmpi_ranks=1\n' "$WM_PROJECT_VERSION" "$WM_OPTIONS"
    echo 'expected_steps=10; expected_final_time=1e-7; numerical_accuracy=UNVERIFIED'
    echo 'Both programs use the same unchanged project libraries; no AI is implemented.'
    cat "$build/binary.sha256" "$build/custom-libraries.sha256"
} > "$out/manifest.txt"
for variant in A B; do
    stage="prepare-$variant"
    solver=laserbeamFoam
    [[ $variant == A ]] || solver=aiLaserbeamFoam
    case_dir="$out/$variant"
    mkdir -- "$case_dir"
    cp -a -- "$source_dir/." "$case_dir/"
    mkdir -- "$case_dir/preparation"
    set_control() {
        foamDictionary "$case_dir/system/controlDict" -entry "$1" -set "$2" > "$case_dir/preparation/control-$1.txt" 2>&1
    }
    set_control application "$solver"
    set_control startFrom startTime
    set_control startTime 0
    set_control stopAt endTime
    set_control deltaT 1e-8
    set_control maxDeltaT 1e-8
    set_control adjustTimeStep no
    set_control endTime 1e-7
    set_control writeControl timeStep
    set_control writeInterval 10
    set_control writeFormat ascii
    set_control writeCompression off
    set_control writePrecision 17
    set_control timePrecision 12
    set_control runTimeModifiable no
    (cd -- "$case_dir"; find initial constant system -type f -print0 | sort -z | xargs -0 sha256sum --text) > "$case_dir/inputs.sha256"
    {
        printf 'AB_REPO=%q\nAB_BUILD=%q\nAB_SOLVER=%q\nAB_COMMIT=%q\nAB_WM_OPTIONS=%q\n' "$repo" "$build" "$solver" "$commit" "$WM_OPTIONS"
    } > "$case_dir/.ab-env.sh"
    cat > "$case_dir/Allrun" <<'ALLRUN'
#!/usr/bin/env bash
# Native case steps with bounded serial execution; no restart or cleanup.
set -Eeo pipefail
export LC_ALL=C
stage=startup
fail() { printf 'ERROR [%s] %s\n' "$stage" "$*" >&2; exit 2; }
trap 'rc=$?; printf "ERROR [%s] command failed at line %s (exit %s); retain this case and its logs\n" "$stage" "$LINENO" "$rc" >&2; exit "$rc"' ERR
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
strict=no
if [[ $# == 1 && $1 == --strict ]]; then strict=yes; shift; fi
[[ $# == 0 ]] || fail 'Usage: ./Allrun [--strict] (serial only)'
stage=environment
[[ -f .ab-env.sh ]] || fail 'Missing .ab-env.sh; prepare a new pair.'
. ./.ab-env.sh
[[ ${WM_PROJECT_VERSION-} == v2512 && ${WM_OPTIONS-} == "$AB_WM_OPTIONS" ]] || fail 'Load the matching of2512 environment.'
[[ -f $AB_BUILD/env.sh ]] || fail 'Build activation env.sh is missing.'
. "$AB_BUILD/env.sh"
[[ $FOAM_USER_APPBIN == "$AB_BUILD/install/bin" && $FOAM_USER_LIBBIN == "$AB_BUILD/install/lib" ]] || fail 'Build activation selected unexpected install paths.'
stage=fresh-case
for path in 0 constant/polyMesh solver.exit.txt solver.time.txt execution.txt log.blockMesh log.checkMesh log.setFields "log.$AB_SOLVER"; do
    [[ ! -e $path && ! -L $path ]] || fail "Refusing to overwrite $path; prepare a new A/B pair."
done
stage=inputs
bash "$AB_REPO/scripts/verify_plate2d_inputs.sh" --case-dir "$PWD"
stage=executable
[[ -x $FOAM_USER_APPBIN/$AB_SOLVER ]] || fail 'Selected solver executable is missing.'
[[ $(command -v "$AB_SOLVER") == "$FOAM_USER_APPBIN/$AB_SOLVER" ]] || fail 'Wrong solver executable on PATH.'
stage=dependencies
ldd "$FOAM_USER_APPBIN/$AB_SOLVER" > ldd.runtime.txt 2>&1 || fail 'ldd failed; see ldd.runtime.txt'
if grep -q 'not found' ldd.runtime.txt; then fail 'Unresolved dynamic library; see ldd.runtime.txt'; fi
awk '$2 == "=>" && $3 != "not" { print $1 "\t" $3 }' ldd.runtime.txt | sort > dependencies.runtime.tsv
awk -v libdir="$FOAM_USER_LIBBIN" '
    $1 == "libMTHD.so" || $1 == "liblaserHeatSource.so" {
        seen++; if ($2 != libdir "/" $1) wrong=1
    }
    END { exit (seen != 2 || wrong) }
' dependencies.runtime.tsv || fail 'Custom libraries did not resolve to this build; see dependencies.runtime.tsv'
# Formal A/B checks are opt-in. Preparation already verifies the build/commit;
# daily execution still checks inputs, executable selection and library loading.
if [[ $strict == yes ]]; then
    stage=strict-provenance
    [[ $(git -C "$AB_REPO" rev-parse HEAD) == "$AB_COMMIT" ]] || fail 'Project commit changed since preparation.'
    git -C "$AB_REPO" diff --quiet HEAD -- src applications || fail 'Uncommitted solver/library source changes.'
    sha256sum -c "$AB_BUILD/binary.sha256" > binaries.verify.txt 2>&1 || fail 'Binary checksum failed; see binaries.verify.txt'
    sha256sum -c "$AB_BUILD/custom-libraries.sha256" > libraries.verify.txt 2>&1 || fail 'Library checksum failed; see libraries.verify.txt'
    sort -- "$AB_BUILD/dependencies.$AB_SOLVER.tsv" > dependencies.expected.sorted.tsv
    diff -u dependencies.expected.sorted.tsv dependencies.runtime.tsv > dependencies.runtime.diff.txt || fail 'Dependency origins changed; see dependencies.runtime.diff.txt'
fi
stage=initialization
. "${WM_PROJECT_DIR:?}/bin/tools/RunFunctions"
cp -a -- initial 0
stage=blockMesh
runApplication blockMesh
stage=checkMesh
runApplication checkMesh
grep -q 'Mesh OK' log.checkMesh || fail 'Mesh check did not report Mesh OK; see log.checkMesh'
stage=setFields
runApplication setFields
(find constant/polyMesh -type f -print0 | sort -z | xargs -0 sha256sum) > mesh.sha256
printf 'program=%s\nmpi_ranks=1\nWM_OPTIONS=%s\nstrict_validation=%s\n' "$FOAM_USER_APPBIN/$AB_SOLVER" "$WM_OPTIONS" "$strict" > execution.txt
date -u '+started_utc=%Y-%m-%dT%H:%M:%SZ' >> execution.txt
stage=solver
if /usr/bin/time -v -o solver.time.txt timeout --signal=TERM --kill-after=10s 120s "$FOAM_USER_APPBIN/$AB_SOLVER" > "log.$AB_SOLVER" 2>&1; then
    rc=0
else
    rc=$?
fi
printf '%s\n' "$rc" > solver.exit.txt
date -u '+finished_utc=%Y-%m-%dT%H:%M:%SZ' >> execution.txt
awk '/^Time = / { n++ } END { print "observed_steps=" n+0 }' "log.$AB_SOLVER" > observed-steps.txt
if ((rc != 0)); then printf 'ERROR [solver] exit %s; see log.%s and solver.time.txt\n' "$rc" "$AB_SOLVER" >&2; fi
exit "$rc"
ALLRUN
    cat > "$case_dir/Allclean" <<'ALLCLEAN'
#!/usr/bin/env bash
echo 'Automatic cleaning is disabled for this recorded A/B fixture.' >&2
echo 'Keep this run and prepare a new pair with a new name.' >&2
exit 2
ALLCLEAN
    chmod +x "$case_dir/Allrun" "$case_dir/Allclean"
done
echo "Prepared $out/A and $out/B. No mesh, initial-field utility, or solver has run."
echo 'For formal A/B run ./Allrun --strict in A then B; default Allrun retains essential checks.'
