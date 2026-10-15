#!/usr/bin/env bash
# Check the prepared path -> SHA256 mapping, independent of manifest row order.
set -Eeuo pipefail
export LC_ALL=C
fail() { printf 'ERROR [inputs] %s\n' "$*" >&2; exit 2; }
trap 'rc=$?; printf "ERROR [inputs] command failed at line %s (exit %s)\n" "$LINENO" "$rc" >&2; exit "$rc"' ERR
[[ $# == 2 && $1 == --case-dir ]] || fail 'Usage: bash scripts/verify_plate2d_inputs.sh --case-dir CASE'
[[ -d $2 ]] || fail "Case directory missing: $2"
cd -- "$2"
[[ -s inputs.sha256 && ! -L inputs.sha256 ]] || fail 'Missing or symlinked inputs.sha256'
for root in initial constant system; do
    [[ -d $root && ! -L $root ]] || fail "Missing or symlinked input directory: $root"
done
[[ -z $(find initial constant system -type l -print -quit) ]] || fail 'Symlinked input is not accepted'
# These manifests are generated from native case paths. Reject unsupported or
# escaping records before sha256sum opens their paths; spaces are supported.
awk '
    length($1) != 64 || $1 ~ /[^[:xdigit:]]/ || substr($0,65,2) != "  " { exit 1 }
    { path=substr($0,67)
      if (path !~ /^(initial|constant|system)\// || path ~ /(^|\/)\.\.?($|\/)/ || path ~ /\\/) exit 1 }
' inputs.sha256 || fail 'Malformed or unsupported relative path in inputs.sha256'
if ! sha256sum -c -- inputs.sha256 > inputs.verify.txt 2>&1; then
    fail 'SHA256 verification failed: changed or missing input; see inputs.verify.txt'
fi
find initial constant system -type f -print0 | sort -z | xargs -0 sha256sum --text > inputs.runtime.sha256
# Canonical records retain both the relative path and its hash. Sorting each
# complete inventory by path accepts reordering, but never drops extra rows,
# missing paths, duplicate records or changed hashes. Keep the original intact.
sort -k2 -- inputs.sha256 > inputs.expected.sorted.sha256
sort -k2 -- inputs.runtime.sha256 > inputs.runtime.sorted.sha256
if ! diff -u inputs.expected.sorted.sha256 inputs.runtime.sorted.sha256 > inputs.runtime.diff.txt; then
    fail 'Input path/SHA256 mapping differs (extra, missing, duplicate or changed input); see inputs.runtime.diff.txt'
fi
echo 'PASS [inputs] paths and SHA256 values match (manifest order ignored)'
