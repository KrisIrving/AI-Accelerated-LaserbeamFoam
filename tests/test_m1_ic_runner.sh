#!/usr/bin/env bash
# Mock commands only: never invoke installed OpenFOAM utilities.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
mkdir -p "$repo/validation"
test_dir=$(mktemp -d "$repo/validation/ic-runner-test.XXXXXXXX")
test_dir=$(cd -- "$test_dir" && pwd -P)
cleanup() {
    case "$test_dir" in "$repo"/validation/ic-runner-test.*) rm -rf -- "$test_dir" ;; *) exit 98 ;; esac
}
trap cleanup EXIT
fail() {
    printf 'FAIL: %s\n' "$*" >&2
    if [[ -n ${case_dir-} ]]; then cat "$case_dir"/console.*.txt >&2; fi
    exit 1
}
real_git=$(command -v git)
real_python=${M_TEST_PYTHON:-$(command -v python3)}
real_timeout=$(command -v timeout)
commit=$(git -C "$repo" rev-parse HEAD)
mkdir -p "$test_dir/mock-bin" "$test_dir/foam/bin/tools" "$test_dir/build/install/bin" "$test_dir/build/install/lib"
cat > "$test_dir/mock-bin/python3" <<'MOCK'
#!/usr/bin/env bash
if [[ ${1-} == */m1_ic.py && ${2-} == preflight ]]; then
    if [[ ${MOCK_CONDITIONAL_FAIL:-no} == yes ]]; then echo 'ERROR [conditional] M1 fails numerical/budget review' >&2; exit 2; fi
    exit 0
fi
if [[ ${1-} == */m1_ic.py && ${2-} == check ]]; then
    if [[ ${MOCK_CHECK_FAIL:-no} == yes ]]; then exit 1; fi
    exit 0
fi
if [[ ${1-} == */m1_ic.py && ${2-} == initialize ]]; then
    if [[ ${MOCK_INIT_FAIL:-no} == yes ]]; then echo 'ERROR [restriction] source mismatch' >&2; exit 19; fi
    echo 'controlled alpha' > 0/alpha.metal
    echo '{}' > ic-initialization.json
    exit 0
fi
if [[ ${1-} == */m1_ic.py && ${2-} == attempt ]]; then exit 0; fi
exec "$REAL_M_PYTHON" "$@"
MOCK
cat > "$test_dir/mock-bin/timeout" <<'MOCK'
#!/usr/bin/env bash
args=("$@")
if [[ ${MOCK_SOLVER_TIMEOUT:-no} == yes && ${args[*]} == *laserbeamFoam* ]]; then
    for ((i=0; i<${#args[@]}; i++)); do
        if [[ ${args[i]} == 600s ]]; then args[i]=0.2s; fi
    done
fi
exec "$REAL_M_TIMEOUT" "${args[@]}"
MOCK
cat > "$test_dir/mock-bin/git" <<'MOCK'
#!/usr/bin/env bash
if [[ " $* " == *' diff '* ]]; then exit 0; fi
exec "$REAL_GIT" "$@"
MOCK
cat > "$test_dir/mock-bin/ldd" <<'MOCK'
#!/usr/bin/env bash
if [[ ${MOCK_BAD_LIBS:-no} == yes ]]; then echo 'libMTHD.so => not found'; exit 0; fi
printf 'libMTHD.so => %s/libMTHD.so (0x1)\n' "$FOAM_USER_LIBBIN"
printf 'liblaserHeatSource.so => %s/liblaserHeatSource.so (0x2)\n' "$FOAM_USER_LIBBIN"
MOCK
cat > "$test_dir/mock-bin/blockMesh" <<'MOCK'
#!/usr/bin/env bash
if [[ ${MOCK_MESH_FAIL:-no} == yes ]]; then exit 17; fi
mkdir -p constant/polyMesh
echo 'mock geometry' > constant/polyMesh/owner
MOCK
printf '#!/usr/bin/env bash\necho "Mesh OK"\n' > "$test_dir/mock-bin/checkMesh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$test_dir/mock-bin/setFields"
printf '#!/usr/bin/env bash\nif [[ ${MOCK_SOLVER_TIMEOUT:-no} == yes ]]; then sleep 5; fi\nexit 23\n' > "$test_dir/build/install/bin/laserbeamFoam"
chmod +x "$test_dir/mock-bin/"* "$test_dir/build/install/bin/laserbeamFoam"
printf 'mock\n' > "$test_dir/build/install/lib/libMTHD.so"
printf 'mock\n' > "$test_dir/build/install/lib/liblaserHeatSource.so"
build="$test_dir/build"
printf 'project_commit=%s\n' "$commit" > "$build/summary.txt"
printf 'export FOAM_USER_APPBIN=%q\nexport FOAM_USER_LIBBIN=%q\n' "$build/install/bin" "$build/install/lib" > "$build/env.sh"
sha256sum "$build/install/bin/laserbeamFoam" > "$build/binary.sha256"
sha256sum "$build/install/lib/"*.so > "$build/custom-libraries.sha256"
printf 'libMTHD.so\t%s/libMTHD.so\nliblaserHeatSource.so\t%s/liblaserHeatSource.so\n' \
    "$build/install/lib" "$build/install/lib" | sort > "$build/dependencies.laserbeamFoam.tsv"
export PATH="$test_dir/mock-bin:$PATH" REAL_GIT="$real_git" REAL_M_PYTHON="$real_python" REAL_M_TIMEOUT="$real_timeout"
export WM_PROJECT_VERSION=v2512 WM_OPTIONS=mockOptions WM_PROJECT_DIR="$test_dir/foam"
make_case() {
    case_dir="$test_dir/$1"
    mkdir -p "$case_dir/initial" "$case_dir/constant" "$case_dir/system"
    printf 'initial\n' > "$case_dir/initial/T"
    printf 'constant\n' > "$case_dir/constant/properties"
    printf 'system\n' > "$case_dir/system/controlDict"
    printf '{"build_dir":"%s","project_commit":"%s","WM_OPTIONS":"mockOptions","solver":"laserbeamFoam","config":{"mesh_timeout_seconds":10,"solver_timeout_seconds":600}}\n' \
        "$build" "$commit" > "$case_dir/manifest.json"
    (cd "$case_dir"; sha256sum manifest.json > metadata.sha256
     find initial constant system -type f -print0 | sort -z | xargs -0 sha256sum > inputs.sha256)
}
run_case() {
    if bash "$repo/scripts/run_m1_ic_case.sh" --case-dir "$case_dir" "$1" > "$case_dir/console.$1.txt" 2>&1; then rc=0; else rc=$?; fi
}
make_case environment
export WM_PROJECT_VERSION=wrong
run_case mesh
[[ $rc != 0 && ! -e $case_dir/0 ]] || fail 'wrong environment initialized fields'
grep -q 'ERROR \[environment\]' "$case_dir/console.mesh.txt" || fail 'missing environment stage'
export WM_PROJECT_VERSION=v2512
make_case mpilaunch
export OMPI_COMM_WORLD_SIZE=4
run_case mesh
[[ $rc != 0 && ! -e $case_dir/0 ]] || fail 'MPI launch initialized fields'
grep -q 'must be launched directly in serial' "$case_dir/console.mesh.txt" || fail 'MPI guard did not explain reason'
unset OMPI_COMM_WORLD_SIZE
if [[ ! -x /usr/bin/time ]]; then
    printf 'PASS: environment-stage guard; SKIP remaining runner mocks (GNU time unavailable on this host)\n'
    exit 0
fi
make_case conditional
export MOCK_CONDITIONAL_FAIL=yes
run_case mesh
[[ $rc != 0 && ! -e $case_dir/0 ]] || fail 'failed conditional M1 review started mesh'
grep -q 'ERROR \[controlled-preflight\]' "$case_dir/console.mesh.txt" || fail 'missing conditional failure stage'
unset MOCK_CONDITIONAL_FAIL
make_case badlib
export MOCK_BAD_LIBS=yes
run_case mesh
[[ $rc != 0 && ! -e $case_dir/0 ]] || fail 'bad library initialized fields'
unset MOCK_BAD_LIBS
make_case meshfail
export MOCK_MESH_FAIL=yes
run_case mesh
[[ $rc == 17 && $(cat "$case_dir/exit.blockMesh.txt") == 17 ]] || fail 'mesh failure lost'
[[ ! -e $case_dir/log.setFields ]] || fail 'failure continued'
unset MOCK_MESH_FAIL
make_case initfail
export MOCK_INIT_FAIL=yes
run_case mesh
[[ $rc == 19 && ! -e $case_dir/.mesh-complete ]] || fail 'failed alpha restriction registered mesh success'
[[ $(cat "$case_dir/exit.restrictAlpha.txt") == 19 ]] || fail 'initialization failure evidence lost'
unset MOCK_INIT_FAIL
make_case solverfail
run_case mesh
[[ $rc == 0 && -f $case_dir/.mesh-complete && -f $case_dir/ic-initialization.json ]] || fail 'mock mesh sequence failed'
run_case mesh
[[ $rc != 0 ]] || fail 'mesh overwritten'
run_case solve
[[ $rc == 23 && $(cat "$case_dir/exit.laserbeamFoam.txt") == 23 ]] || fail 'solver failure lost'
[[ $(cat "$case_dir/solver.exit.txt") == 23 && -s $case_dir/solver.time.txt ]] || fail 'canonical failure feedback missing'
run_case solve
[[ $rc != 0 ]] || fail 'failed solver silently retried'
make_case timeout
run_case mesh
[[ $rc == 0 ]] || fail 'timeout fixture mesh failed'
export MOCK_SOLVER_TIMEOUT=yes
run_case solve
[[ $rc == 124 && $(cat "$case_dir/solver.exit.txt") == 124 ]] || fail 'timeout exit not preserved'
[[ -s $case_dir/solver.time.txt && -d $case_dir/.solve-started ]] || fail 'timeout evidence missing'
grep -q 'resource_policy=MONITORED_ONLY' "$case_dir/execution.txt" || fail 'resource policy not explicit'
unset MOCK_SOLVER_TIMEOUT
run_case solve
[[ $rc != 0 ]] || fail 'timed-out solve silently retried'
make_case meshcheck
export MOCK_CHECK_FAIL=yes
run_case mesh
[[ $rc != 0 && ! -e $case_dir/.mesh-complete ]] || fail 'failed mesh check registered success'
unset MOCK_CHECK_FAIL
printf 'PASS: M1-IC runner environment/conditional/library/mesh/solver/timeout/no-overwrite guards (mocks only)\n'
