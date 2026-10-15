#!/usr/bin/env bash
# Fixture-only smoke tests; they do not build OpenFOAM or run a solver.
set -euo pipefail
export LC_ALL=C
test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
audit_script="$test_dir/../scripts/audit_host.sh"
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/audit-host-test.XXXXXXXX")
cleanup() {
    case "$test_tmp" in
        */audit-host-test.*) rm -rf -- "$test_tmp" ;;
        *) printf 'Refusing unexpected test cleanup path.\n' >&2 ;;
    esac
}
trap cleanup EXIT
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "missing expected report text: $2"; }
assert_absent() { ! grep -Fq -- "$2" "$1" || fail "unexpected report text: $2"; }

bash -n "$audit_script"
bash "$audit_script" --help > "$test_tmp/help"
assert_contains "$test_tmp/help" 'read-only host report'
if bash "$audit_script" --repo > /dev/null 2>&1; then fail 'missing PATH accepted'; fi
if bash "$audit_script" --unknown > /dev/null 2>&1; then fail 'unknown option accepted'; fi

real_git=$(type -P git) || fail 'git is needed for fixture tests'
real_awk=$(type -P awk) || fail 'awk is needed for fixture tests'
export HOME="$test_tmp/home/demo_private_user" USER=demo_private_user LOGNAME=demo_private_user
export AUDIT_TEST_MARKER="$test_tmp/forbidden-execution"
export AUDIT_TEST_GPU_CALLS="$test_tmp/gpu-args"
export AUDIT_PRIVATE_TOKEN='sensitive-not-for-report'
export WM_PROJECT_VERSION=v2512 WM_PROJECT_DIR="$HOME/OpenFOAM-v2512"
mkdir -p "$HOME/bin" "$HOME/repository" "$test_tmp/missing-tools"
for tool in laserbeamFoam foamVersion wmake; do
    cat > "$HOME/bin/$tool" <<'EOF'
#!/usr/bin/env bash
printf 'executed\n' > "$AUDIT_TEST_MARKER"
exit 91
EOF
    chmod +x "$HOME/bin/$tool"
done
cat > "$HOME/bin/nvidia-smi" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$AUDIT_TEST_GPU_CALLS"
printf 'Mock GPU, 550.1, 8192 MiB\n'
EOF
cat > "$HOME/bin/lspci" <<'EOF'
#!/usr/bin/env bash
printf '01:00.0 VGA compatible controller: Mock Display [1234:5678]\n'
printf '\tKernel driver in use: mock_display_driver\n'
printf '\tKernel modules: mock_display_module\n'
printf '02:00.0 Ethernet controller: PrivateEthernet\n'
printf '\tKernel driver in use: private_ethernet_driver\n'
EOF
cat > "$HOME/bin/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf '/dev/private-device 1000 400 600 40%% /private-mount\n'
EOF
chmod +x "$HOME/bin/nvidia-smi" "$HOME/bin/lspci" "$HOME/bin/df"
export PATH="$HOME/bin:$PATH"
of2512() { printf 'alias-executed\n' > "$AUDIT_TEST_MARKER"; }
export -f of2512

fixture_repo="$HOME/repository"
"$real_git" init -q "$fixture_repo"
printf 'tracked\n' > "$fixture_repo/input"
"$real_git" -C "$fixture_repo" -c core.autocrlf=false add -- input
"$real_git" -C "$fixture_repo" -c user.name=AuditTest -c user.email=audit@example.invalid commit -qm fixture
expected_head=$("$real_git" -C "$fixture_repo" rev-parse HEAD)
printf 'modified\n' > "$fixture_repo/input"
printf 'untracked\n' > "$fixture_repo/untracked-private-name"
index_before=$(sha256sum < "$fixture_repo/.git/index")
config_before=$(sha256sum < "$fixture_repo/.git/config")
repo_files_before=$(find "$fixture_repo/.git" -type f | sort)

# A foreign inherited GIT_DIR must not redirect the explicitly selected repo.
GIT_DIR="$test_tmp/not-a-repository" bash "$audit_script" \
    --repo "$fixture_repo" --repo "$test_tmp/nonexistent" \
    --disk "$HOME/private-mount" > "$test_tmp/report"

[[ ! -e "$AUDIT_TEST_MARKER" ]] || fail 'solver, alias, or OpenFOAM helper executed'
[[ "$index_before" == "$(sha256sum < "$fixture_repo/.git/index")" ]] || fail 'index changed'
[[ "$config_before" == "$(sha256sum < "$fixture_repo/.git/config")" ]] || fail 'Git config changed'
[[ "$repo_files_before" == "$(find "$fixture_repo/.git" -type f | sort)" ]] || fail 'Git files created/deleted'
assert_contains "$test_tmp/report" 'verification_status: NOT compiled/run verified'
assert_contains "$test_tmp/report" "HEAD: $expected_head"
assert_contains "$test_tmp/report" 'tracked_change_entries: 1'
assert_contains "$test_tmp/report" 'WM_PROJECT_VERSION=v2512'
assert_contains "$test_tmp/report" 'WM_PROJECT_DIR=${HOME}/OpenFOAM-v2512'
assert_contains "$test_tmp/report" 'laserbeamFoam SHA256:'
assert_contains "$test_tmp/report" 'capacity_kib: total=1000 used=400 available=600 used_percent=40%'
assert_absent "$test_tmp/report" 'demo_private_user'
assert_absent "$test_tmp/report" 'sensitive-not-for-report'
assert_absent "$test_tmp/report" 'PrivateEthernet'
assert_contains "$test_tmp/report" 'Kernel driver in use: mock_display_driver'
assert_contains "$test_tmp/report" 'Kernel modules: mock_display_module'
assert_absent "$test_tmp/report" 'private_ethernet_driver'
assert_absent "$test_tmp/report" '/private-mount'
assert_absent "$test_tmp/report" '/dev/private-device'
assert_absent "$test_tmp/report" 'untracked-private-name'
[[ "$(cat "$AUDIT_TEST_GPU_CALLS")" == '--query-gpu=name,driver_version,memory.total --format=csv,noheader' ]] || fail 'GPU query exceeded allowlist'

# Essential Ubuntu awk remains available; all optional inventory tools are absent.
ln -s "$real_awk" "$test_tmp/missing-tools/awk"
PATH="$test_tmp/missing-tools" "$BASH" "$audit_script" > "$test_tmp/missing-report"
assert_contains "$test_tmp/missing-report" 'command missing: lscpu'
assert_contains "$test_tmp/missing-report" 'command missing: nvidia-smi'
assert_contains "$test_tmp/missing-report" 'command missing: gcc'
assert_contains "$test_tmp/missing-report" 'no repository discovery'
printf 'PASS: syntax, arguments, privacy, command allowlists, missing tools, and Git immutability\n'
