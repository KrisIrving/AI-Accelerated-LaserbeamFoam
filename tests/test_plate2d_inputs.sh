#!/usr/bin/env bash
# Input-integrity regression fixtures only; no OpenFOAM command is called.
set -euo pipefail
export LC_ALL=C
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
tmp_base=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
test_tmp=$(mktemp -d "$tmp_base/plate2d-inputs-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        "$tmp_base"/plate2d-inputs-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
script="$repo/scripts/verify_plate2d_inputs.sh"
bash -n "$script"
passed=0
fixture() {
    local name=$1
    case_dir="$test_tmp/$name"
    mkdir -p -- "$case_dir/initial" "$case_dir/constant" "$case_dir/system"
    printf 'laser configuration\n' > "$case_dir/constant/LaserProperties"
    printf 'gravity\n' > "$case_dir/constant/g"
    printf 'magnetic field\n' > "$case_dir/initial/H"
    printf 'temperature\n' > "$case_dir/initial/T"
    printf 'velocity\n' > "$case_dir/initial/U"
    printf 'metal volume fraction\n' > "$case_dir/initial/alpha.metal"
    printf 'dictionary\n' > "$case_dir/system/controlDict"
    printf 'filename with spaces\n' > "$case_dir/system/input with spaces"
    (
        cd -- "$case_dir"
        find initial constant system -type f -print0 | sort -z | xargs -0 sha256sum --text
    ) > "$case_dir/inputs.sha256"
}
pass() {
    passed=$((passed + 1))
    printf 'PASS: %s\n' "$1"
}
expect_success() {
    local name=$1
    shift
    if ! "$@" > "$test_tmp/stdout.txt" 2> "$test_tmp/stderr.txt"; then
        printf 'FAIL: %s\n' "$name" >&2
        cat "$test_tmp/stdout.txt" "$test_tmp/stderr.txt" >&2
        exit 1
    fi
    [[ -f $case_dir/inputs.verify.txt && -f $case_dir/inputs.runtime.diff.txt ]] || {
        printf 'FAIL: %s did not retain integrity reports\n' "$name" >&2; exit 1;
    }
    [[ ! -s $case_dir/inputs.runtime.diff.txt ]] || {
        printf 'FAIL: %s produced an input difference\n' "$name" >&2; exit 1;
    }
    pass "$name"
}
expect_failure() {
    local name=$1 reason=$2
    shift 2
    if "$@" > "$test_tmp/stdout.txt" 2> "$test_tmp/stderr.txt"; then
        printf 'FAIL: %s was accepted\n' "$name" >&2; exit 1
    fi
    grep -Fq 'ERROR [inputs]' "$test_tmp/stderr.txt" || {
        printf 'FAIL: %s omitted the failure stage\n' "$name" >&2
        cat "$test_tmp/stderr.txt" >&2; exit 1;
    }
    grep -Eiq "$reason" "$test_tmp/stderr.txt" || {
        printf 'FAIL: %s omitted a useful reason\n' "$name" >&2
        cat "$test_tmp/stderr.txt" >&2; exit 1;
    }
    pass "$name"
}

fixture 'reordered case'
awk '{lines[NR]=$0} END {for (i=NR; i>0; i--) print lines[i]}' \
    "$case_dir/inputs.sha256" > "$case_dir/reversed.sha256"
mv -- "$case_dir/reversed.sha256" "$case_dir/inputs.sha256"
expect_success 'same path/hash map in reversed record order' \
    bash "$script" --case-dir "$case_dir"

fixture 'locale case'
expect_success 'C locale' env LC_ALL=C bash "$script" --case-dir "$case_dir"
utf8_locale=
for candidate in C.UTF-8 C.utf8; do
    if env LC_ALL="$candidate" locale charmap > "$test_tmp/charmap.txt" 2> "$test_tmp/locale-error.txt" \
        && [[ ! -s $test_tmp/locale-error.txt ]]; then
        utf8_locale=$candidate
        break
    fi
done
if [[ -n $utf8_locale ]]; then
    expect_success "$utf8_locale locale with conflicting LC_COLLATE" \
        env LC_ALL="$utf8_locale" LC_COLLATE=C bash "$script" --case-dir "$case_dir"
else
    printf 'SKIP: C UTF-8 locale is not installed on this test host\n'
fi
for candidate in en_US.UTF-8 en_US.utf8; do
    if env LC_ALL="$candidate" locale charmap > "$test_tmp/charmap.txt" 2> "$test_tmp/locale-error.txt" \
        && [[ ! -s $test_tmp/locale-error.txt ]]; then
        expect_success "$candidate locale" \
            env LC_ALL="$candidate" bash "$script" --case-dir "$case_dir"
        break
    fi
done

fixture changed
printf 'changed temperature\n' >> "$case_dir/initial/T"
expect_failure 'changed file contents' 'checksum|hash|sha256|content|integrity|changed' \
    bash "$script" --case-dir "$case_dir"
grep -Eq 'initial/T: FAILED' "$case_dir/inputs.verify.txt" || {
    printf 'FAIL: changed file did not retain sha256sum failure evidence\n' >&2; exit 1;
}

fixture missing
rm -- "$case_dir/initial/U"
expect_failure 'missing input file' 'missing|no such|open|read|checksum|hash|integrity' \
    bash "$script" --case-dir "$case_dir"

fixture extra
printf 'unexpected input\n' > "$case_dir/constant/unexpectedProperties"
expect_failure 'unexpected extra input file' 'extra|inventory|differ|file set|manifest' \
    bash "$script" --case-dir "$case_dir"

fixture 'renamed path'
mv -- "$case_dir/initial/H" "$case_dir/initial/H-renamed"
expect_failure 'unchanged hash at a different path' 'missing|open|read|checksum|hash|integrity' \
    bash "$script" --case-dir "$case_dir"

fixture 'missing root'
mv -- "$case_dir/initial" "$case_dir/saved-initial"
expect_failure 'missing initial directory' 'initial|missing|directory' \
    bash "$script" --case-dir "$case_dir"

fixture 'missing manifest'
rm -- "$case_dir/inputs.sha256"
expect_failure 'missing input manifest' 'manifest|inputs.sha256|missing' \
    bash "$script" --case-dir "$case_dir"

fixture 'bad manifest'
printf 'not a valid checksum record\n' >> "$case_dir/inputs.sha256"
expect_failure 'malformed input manifest' 'manifest|checksum|format|malformed|invalid' \
    bash "$script" --case-dir "$case_dir"

fixture 'duplicate record'
head -n 1 "$case_dir/inputs.sha256" > "$test_tmp/duplicate.sha256"
cat "$test_tmp/duplicate.sha256" >> "$case_dir/inputs.sha256"
expect_failure 'duplicate manifest path' 'duplicate|manifest|differ|inventory' \
    bash "$script" --case-dir "$case_dir"

fixture 'symlink input'
if ln -s g "$case_dir/constant/gravity-link" 2> "$test_tmp/symlink-error.txt" \
    && [[ -L $case_dir/constant/gravity-link ]]; then
    expect_failure 'symlinked input' 'symlink|symbolic' \
        bash "$script" --case-dir "$case_dir"
else
    printf 'SKIP: symlink creation is not supported on this test host\n'
fi

printf 'PASS: %s Plate2D input-integrity regression cases\n' "$passed"
