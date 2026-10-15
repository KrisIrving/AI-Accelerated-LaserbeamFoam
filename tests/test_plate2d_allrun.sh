#!/usr/bin/env bash
# Exercise the generated Allrun with mocks only; no OpenFOAM utility is called.
set -euo pipefail
export LC_ALL=C
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
tmp_base=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
test_tmp=$(mktemp -d "$tmp_base/plate2d-allrun-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        "$tmp_base"/plate2d-allrun-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# Extract exactly the current template, rather than maintaining a test copy.
sed -n "/<<'ALLRUN'/,/^ALLRUN$/p" "$repo/scripts/prepare_plate2d_ab.sh" |
    sed '1d;$d' > "$test_tmp/Allrun.template"
[[ -s $test_tmp/Allrun.template ]] || fail 'Allrun heredoc was not found'
bash -n "$test_tmp/Allrun.template"
mkdir -p "$test_tmp/mock-bin" "$test_tmp/mock-foam/bin/tools"
cat > "$test_tmp/mock-foam/bin/tools/RunFunctions" <<'MOCKRUN'
runApplication() {
    printf '%s\n' "$1" >> "$MOCK_CALLS"
    # Stop before any real mesh or initial-field utility can execute.
    return 97
}
MOCKRUN
cat > "$test_tmp/mock-bin/ldd" <<'MOCKLDD'
#!/usr/bin/env bash
case "${MOCK_LDD_MODE:-normal}" in
    missing)
        printf 'libMTHD.so => not found\n'
        printf 'liblaserHeatSource.so => %s/liblaserHeatSource.so (0x1)\n' "$FOAM_USER_LIBBIN"
        ;;
    wrong-origin)
        printf 'libMTHD.so => /old/install/libMTHD.so (0x1)\n'
        printf 'liblaserHeatSource.so => %s/liblaserHeatSource.so (0x2)\n' "$FOAM_USER_LIBBIN"
        ;;
    *)
        # Deliberately put names in the reverse of their C sorted order.
        printf 'liblaserHeatSource.so => %s/liblaserHeatSource.so (0x2)\n' "$FOAM_USER_LIBBIN"
        printf 'libMTHD.so => %s/libMTHD.so (0x1)\n' "$FOAM_USER_LIBBIN"
        ;;
esac
MOCKLDD
chmod +x "$test_tmp/mock-bin/ldd"
commit=$(git -C "$repo" rev-parse HEAD)

make_case() {
    local name=$1
    case_dir="$test_tmp/$name/case"
    build_dir="$test_tmp/$name/build"
    mkdir -p "$case_dir/initial" "$case_dir/constant" "$case_dir/system" \
        "$build_dir/install/bin" "$build_dir/install/lib"
    cp -- "$test_tmp/Allrun.template" "$case_dir/Allrun"
    printf 'alpha\n' > "$case_dir/initial/alpha.metal"
    printf 'temperature\n' > "$case_dir/initial/T"
    printf 'laser\n' > "$case_dir/constant/LaserProperties"
    printf 'gravity\n' > "$case_dir/constant/g"
    printf 'application laserbeamFoam;\n' > "$case_dir/system/controlDict"
    (cd -- "$case_dir"; find initial constant system -type f -print0 |
        sort -z | xargs -0 sha256sum --text) > "$case_dir/inputs.sha256"
    {
        printf 'AB_REPO=%q\nAB_BUILD=%q\nAB_SOLVER=laserbeamFoam\n' "$repo" "$build_dir"
        printf 'AB_COMMIT=%q\nAB_WM_OPTIONS=mockOptions\n' "$commit"
    } > "$case_dir/.ab-env.sh"
    {
        printf 'export FOAM_USER_APPBIN=%q\n' "$build_dir/install/bin"
        printf 'export FOAM_USER_LIBBIN=%q\n' "$build_dir/install/lib"
        printf 'export PATH=%q:%q:"$PATH"\n' "$build_dir/install/bin" "$test_tmp/mock-bin"
    } > "$build_dir/env.sh"
    printf '#!/usr/bin/env bash\nexit 98\n' > "$build_dir/install/bin/laserbeamFoam"
    chmod +x "$build_dir/install/bin/laserbeamFoam"
    printf 'mock MTHD\n' > "$build_dir/install/lib/libMTHD.so"
    printf 'mock heat source\n' > "$build_dir/install/lib/liblaserHeatSource.so"
    sha256sum "$build_dir/install/bin/laserbeamFoam" > "$build_dir/binary.sha256"
    sha256sum "$build_dir/install/lib/"*.so > "$build_dir/custom-libraries.sha256"
    # Reverse order is intentional: strict provenance must compare mappings.
    printf 'liblaserHeatSource.so\t%s/liblaserHeatSource.so\nlibMTHD.so\t%s/libMTHD.so\n' \
        "$build_dir/install/lib" "$build_dir/install/lib" > "$build_dir/dependencies.laserbeamFoam.tsv"
}

run_case() {
    local environment_version=$1 mode=$2 requested_locale=$3
    shift 3
    if env WM_PROJECT_VERSION="$environment_version" WM_OPTIONS=mockOptions \
        WM_PROJECT_DIR="$test_tmp/mock-foam" MOCK_LDD_MODE="$mode" \
        MOCK_CALLS="$case_dir/mock.calls" LC_ALL="$requested_locale" \
        bash "$case_dir/Allrun" "$@" > "$case_dir/console.txt" 2>&1; then
        run_rc=0
    else
        run_rc=$?
    fi
}

assert_stopped_before_mesh() {
    [[ ! -e $case_dir/mock.calls ]] || fail 'a preflight failure reached mock mesh execution'
    [[ ! -e $case_dir/0 ]] || fail 'a preflight failure initialized fields'
}

make_case bad-environment
run_case wrong-version normal C
[[ $run_rc == 2 ]] || fail 'wrong environment was accepted'
grep -Fq 'ERROR [environment] Load the matching of2512 environment.' "$case_dir/console.txt" ||
    fail 'environment failure has no stage/reason'
assert_stopped_before_mesh

make_case changed-input
printf 'changed\n' >> "$case_dir/initial/T"
run_case v2512 normal C
[[ $run_rc != 0 ]] || fail 'changed input was accepted'
grep -Fq 'ERROR [inputs] SHA256 verification failed' "$case_dir/console.txt" ||
    fail 'input failure has no stage/reason'
assert_stopped_before_mesh

for mode in missing wrong-origin; do
    make_case "dependencies-$mode"
    run_case v2512 "$mode" C
    [[ $run_rc == 2 ]] || fail "bad dependency mode $mode was accepted"
    grep -Fq 'ERROR [dependencies]' "$case_dir/console.txt" || fail 'dependency failure has no stage'
    if [[ $mode == missing ]]; then
        grep -Fq 'Unresolved dynamic library' "$case_dir/console.txt" || fail 'missing-library reason absent'
    else
        grep -Fq 'Custom libraries did not resolve to this build' "$case_dir/console.txt" ||
            fail 'wrong-library-origin reason absent'
    fi
    assert_stopped_before_mesh
done

# Both commonly available locales are exercised when installed. Every case
# reverses the manifest rows; the generated Allrun must not depend on either.
locales=(C)
if locale -a 2>/dev/null | grep -Eiq '^C[.](utf8|UTF-8)$'; then
    locales+=(C.UTF-8)
else
    printf 'NOTE: C.UTF-8 is unavailable; reordered-manifest case still tested under C.\n'
fi
number=0
for requested_locale in "${locales[@]}"; do
    for strict_flag in default strict; do
        number=$((number + 1))
        make_case "reordered-$number"
        sort -r -- "$case_dir/inputs.sha256" > "$case_dir/inputs.reversed"
        mv -- "$case_dir/inputs.reversed" "$case_dir/inputs.sha256"
        if [[ $strict_flag == strict ]]; then
            run_case v2512 normal "$requested_locale" --strict
        else
            run_case v2512 normal "$requested_locale"
        fi
        [[ $run_rc == 97 ]] || {
            cat "$case_dir/console.txt" >&2
            fail "reordered input did not reach mock blockMesh ($requested_locale/$strict_flag)"
        }
        [[ $(cat "$case_dir/mock.calls") == blockMesh ]] || fail 'unexpected mocked utility call'
        grep -Fq 'ERROR [blockMesh]' "$case_dir/console.txt" || fail 'utility failure has no stage'
        grep -Fq 'exit 97' "$case_dir/console.txt" || fail 'utility failure has no exit reason'
    done
done
printf 'PASS: generated Allrun reports staged failures; reordered manifests/locales and strict dependency mapping pass preflight (mock utilities only)\n'
