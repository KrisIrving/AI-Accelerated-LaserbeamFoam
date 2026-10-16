#!/usr/bin/env bash
# Source-only baseline guard. Writes only disposable comparison files in TMPDIR.
set -euo pipefail
export LC_ALL=C
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
readonly baseline='3c93f2657e089e22e9a8298648292969e85a4bad'
readonly original='applications/solvers/laserbeamFoam'
readonly fork='applications/solvers/aiLaserbeamFoam'
tmp_base=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
test_tmp=$(mktemp -d "$tmp_base/ai-solver-source-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        "$tmp_base"/ai-solver-source-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# Explicit root, no index refresh, no fsmonitor hook, and no lazy network fetch.
git_read=(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_COMMON_DIR
    -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_NAMESPACE
    -u GIT_CONFIG_COUNT -u GIT_CONFIG_PARAMETERS -u GIT_PREFIX
    GIT_OPTIONAL_LOCKS=0 GIT_TERMINAL_PROMPT=0 GIT_NO_LAZY_FETCH=1
    git -c protocol.allow=never -c core.fsmonitor=false -c core.untrackedCache=false
    -C "$repo")

"${git_read[@]}" cat-file -e "$baseline^{commit}" || fail 'pinned baseline commit is unavailable locally'
"${git_read[@]}" ls-tree -r --name-only "$baseline" -- "$original" > "$test_tmp/pinned-files"
[[ -s "$test_tmp/pinned-files" ]] || fail 'pinned solver source inventory is empty'
"${git_read[@]}" ls-files -- "$original" > "$test_tmp/current-files"
cmp -s "$test_tmp/pinned-files" "$test_tmp/current-files" || fail 'original tracked inventory changed'
"${git_read[@]}" diff --no-ext-diff --no-textconv --quiet "$baseline" HEAD -- "$original" ||
    fail 'committed original solver differs from the pinned baseline'
"${git_read[@]}" diff --no-ext-diff --no-textconv --cached --quiet "$baseline" -- "$original" ||
    fail 'original solver has staged changes from the pinned baseline'
"${git_read[@]}" diff --no-ext-diff --no-textconv --quiet "$baseline" -- "$original" ||
    fail 'original solver working tree differs from the pinned baseline'

# Compare canonical LF bytes so a Windows CRLF checkout has the same semantics
# as Ubuntu. No other whitespace, spelling, comments, or code is normalized.
canonical_lf() { sed 's/\r$//' "$1"; }
source_count=0
file_count=0
while IFS= read -r original_path; do
    relative=${original_path#"$original/"}
    copy_relative=$relative
    "${git_read[@]}" show "$baseline:$original_path" > "$test_tmp/pinned"
    "${git_read[@]}" show "HEAD:$original_path" > "$test_tmp/original-head"
    cmp -s "$test_tmp/pinned" "$test_tmp/original-head" || fail "original HEAD bytes changed: $relative"

    case "$relative" in
        laserbeamFoam.C)
            copy_relative='aiLaserbeamFoam.C'
            # Build the complete expected main source with exactly two allowed
            # edits. Changes anywhere else (including algorithm comments) fail.
            awk '
                /^Application$/ {
                    print
                    if ((getline) <= 0 || $0 != "    laserbeamFoam") exit 2
                    print "    aiLaserbeamFoam"
                    applications++
                    next
                }
                /^#include "fvCFD.H"$/ {
                    print "// Baseline fork of applications/solvers/laserbeamFoam."
                    print "// Upstream commit: 3c93f2657e089e22e9a8298648292969e85a4bad."
                    print "// Solver algorithm and shared-library dependencies are unchanged."
                    print ""
                    origins++
                }
                {print}
                END {if (applications != 1 || origins != 1) exit 2}
            ' "$test_tmp/pinned" > "$test_tmp/expected" || fail 'unexpected pinned main source format'
            ((source_count += 1))
            ;;
        Make/files)
            # Exact whole-file expectation; additional sources/flags are forbidden.
            printf '%s\n\n%s\n' 'aiLaserbeamFoam.C' \
                'EXE = $(FOAM_USER_APPBIN)/aiLaserbeamFoam' > "$test_tmp/expected"
            ;;
        *.H|Make/options)
            cp -- "$test_tmp/pinned" "$test_tmp/expected"
            [[ "$relative" != *.H ]] || ((source_count += 1))
            ;;
        *) fail "unexpected tracked upstream file: $relative" ;;
    esac

    [[ -f "$repo/$fork/$copy_relative" && ! -L "$repo/$fork/$copy_relative" ]] ||
        fail "missing or symlinked copy: $copy_relative"
    canonical_lf "$repo/$fork/$copy_relative" > "$test_tmp/copied"
    cmp -s "$test_tmp/expected" "$test_tmp/copied" ||
        fail "unexpected canonical byte difference: $copy_relative"
    ((file_count += 1))
done < "$test_tmp/pinned-files"

[[ ! -e "$repo/$fork/laserbeamFoam.C" ]] || fail 'old main filename remains in fork'
actual_source_count=$(find "$repo/$fork" -type f \( -name '*.C' -o -name '*.H' \) | wc -l)
[[ "$actual_source_count" -eq "$source_count" ]] || fail 'unexpected additional .C/.H source in fork'
[[ -f "$repo/$fork/README.md" ]] || fail 'fork provenance README is missing'
printf 'PASS: %d pinned source/Make files match; only the exact main-name/origin and executable-target differences are allowed; original solver is unchanged\n' "$file_count"
