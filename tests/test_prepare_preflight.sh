#!/usr/bin/env bash
# Guard tests only. No OpenFOAM utility, mesh generation, or solver execution.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
tmp_base=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
test_tmp=$(mktemp -d "$tmp_base/prepare-ab-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        "$tmp_base"/prepare-ab-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
script="$repo/scripts/prepare_plate2d_ab.sh"
bash -n "$script"
bash "$script" --help > "$test_tmp/help"
if env -u WM_PROJECT_VERSION bash "$script" --run-dir "$repo/runs/test-must-not-be-created" --build-dir "$test_tmp" > "$test_tmp/result" 2>&1; then
    echo 'FAIL: preparation accepted unloaded environment' >&2; exit 1
else
    [[ $? == 2 ]] || { echo 'FAIL: unexpected preflight status' >&2; exit 1; }
fi
[[ ! -e $repo/runs/test-must-not-be-created ]] || { echo 'FAIL: preparation wrote a case' >&2; exit 1; }
echo 'PASS: preparation rejects missing OpenFOAM environment before creating a case'
