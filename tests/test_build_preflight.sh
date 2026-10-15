#!/usr/bin/env bash
# Negative preflight checks only: never enter Allwmake or a solver.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
tmp_base=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
test_tmp=$(mktemp -d "$tmp_base/build-preflight-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        "$tmp_base"/build-preflight-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
script="$repo/scripts/validate_build.sh"
bash -n "$script"
bash "$script" --help > "$test_tmp/help"
check_rejected() {
    local rc
    if env -u WM_PROJECT_VERSION bash "$script" "$@" > "$test_tmp/result" 2>&1; then
        printf 'FAIL: unsafe build preflight was accepted\n' >&2
        exit 1
    else
        rc=$?
    fi
    [[ $rc == 2 ]] || { printf 'FAIL: expected preflight exit 2, got %s\n' "$rc" >&2; exit 1; }
}
check_rejected --report-dir "$test_tmp/must-not-exist" --jobs 8
check_rejected --report-dir "$test_tmp/must-not-exist" --jobs 48
check_rejected --unknown
[[ ! -e $test_tmp/must-not-exist ]] || { echo 'FAIL: preflight wrote output' >&2; exit 1; }
printf 'PASS: build preflight rejects unloaded environment, excessive jobs, and unknown options without writing output\n'
