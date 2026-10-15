#!/usr/bin/env bash
# Read-only Ubuntu 22.04 host inventory. Never source this script.
set -u
set -o pipefail
export LC_ALL=C

readonly AUDIT_SCHEMA='ai-laserbeamfoam-host-audit/v1'
readonly AUDIT_REVISION='2026-10-15'
declare -a audit_repos=() audit_disks=()

usage() {
    cat <<'EOF'
Usage: bash scripts/audit_host.sh [--repo PATH]... [--disk PATH] [--help]

Print a read-only host report to stdout. Redirect it yourself to a private
validation directory if desired. --repo audits only explicitly named local
repositories; --disk reports capacity for that target (default: /).

No user configuration is sourced. No alias, build, simulation, installation,
network operation, Git configuration change, or report-file creation is used.
Git remotes, all-environment dumps, GPU UUIDs/serials/processes, disk device
names, and mount-point listings are excluded. HOME and username path segments
are masked; repository commit and executable SHA-256 hashes remain exact.
An inventory does not verify compilation or a successful simulation.
EOF
}

while (($#)); do
    case "$1" in
        --repo|--disk)
            if (($# < 2)) || [[ -z "$2" ]]; then
                printf 'Error: %s requires a nonempty PATH.\n' "$1" >&2
                exit 2
            fi
            if [[ "$1" == --repo ]]; then
                audit_repos+=("$2")
            else
                audit_disks+=("$2")
            fi
            shift 2
            ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Error: unknown argument; use --help.\n' >&2; exit 2 ;;
    esac
done
((${#audit_disks[@]})) || audit_disks=('/')

mask_paths() {
    local value="$1" user_name
    if [[ -n "${HOME:-}" && "${HOME:-}" != / ]]; then
        value=${value//"$HOME"/'${HOME}'}
    fi
    for user_name in "${USER:-}" "${LOGNAME:-}"; do
        if [[ -n "$user_name" ]]; then
            value=${value//"/$user_name/"/'/[USER]/'}
            if [[ "$value" == *"/$user_name" ]]; then
                value="${value%"/$user_name"}/[USER]"
            fi
        fi
    done
    printf '%s\n' "$value"
}

line() { mask_paths "$*"; }
section() { printf '\n[%s]\n' "$1"; }
exe_path() { type -P -- "$1" 2>/dev/null; }

version_probe() {
    local label="$1" tool="$2" limit="$3" executable output result entry timeout_tool count=0
    shift 3
    executable=$(exe_path "$tool") || {
        line "$label: unavailable (command missing: $tool)"
        return
    }
    line "$label executable: $executable"
    if timeout_tool=$(exe_path timeout); then
        output=$("$timeout_tool" 10 "$executable" "$@" 2>&1)
    else
        output=$("$executable" "$@" 2>&1)
    fi
    result=$?
    line "$label version command exit: $result"
    while IFS= read -r entry; do
        ((count += 1))
        ((count > limit)) && break
        line "  $entry"
    done <<< "$output"
}

line "schema: $AUDIT_SCHEMA"
line "script_revision: $AUDIT_REVISION"
line 'verification_status: NOT compiled/run verified'
line 'scope: read-only inventory; no build or solver execution'
if exe_path date >/dev/null; then
    line "audit_utc: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
fi

section 'OS and kernel'
if [[ -r /etc/os-release ]]; then
    while IFS= read -r entry; do line "$entry"; done < <(
        awk -F= '$1 == "PRETTY_NAME" || $1 == "ID" || $1 == "VERSION_ID" {print}' /etc/os-release
    )
else
    line 'OS release: unavailable (/etc/os-release not readable)'
fi
if exe_path uname >/dev/null; then
    line "kernel: $(uname -srmo 2>/dev/null)"
else
    line 'kernel: unavailable (command missing: uname)'
fi

section 'CPU, NUMA, and caches'
if exe_path lscpu >/dev/null; then
    lscpu_output=$(lscpu 2>/dev/null)
    if [[ -n "$lscpu_output" ]]; then
        while IFS= read -r entry; do line "$entry"; done < <(
            printf '%s\n' "$lscpu_output" | awk -F: '
                { key=$1; sub(/^[[:space:]]+/, "", key) }
                key ~ /^(Architecture|CPU\(s\)|On-line CPU\(s\) list|Model name|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|NUMA node\(s\)|L1d cache|L1i cache|L2 cache|L3 cache)$/ {print}'
        )
        topology=$(lscpu -p=SOCKET,CORE,ONLINE 2>/dev/null)
        if [[ -n "$topology" ]]; then
            printf '%s\n' "$topology" | awk -F, '
                !/^#/ && ($3 == "Y" || $3 == "yes") {
                    logical++; sockets[$1]=1; cores[$1 ":" $2]=1
                }
                END {
                    if (logical) printf "online_topology: sockets=%d physical_cores=%d logical_cpus=%d\n", length(sockets), length(cores), logical;
                    else print "online_topology: unavailable (lscpu ONLINE data not usable)"
                }'
        else
            line 'online_topology: unavailable (lscpu topology query failed)'
        fi
    else
        line 'CPU details: unavailable (lscpu failed)'
    fi
else
    line 'CPU topology/cache details: unavailable (command missing: lscpu)'
    if [[ -r /proc/cpuinfo ]]; then
        while IFS= read -r entry; do line "$entry"; done < <(
            awk -F: '/^model name/ {print "CPU model:" $2; exit}' /proc/cpuinfo
        )
    fi
fi
if [[ -r /sys/devices/system/node/online ]]; then
    IFS= read -r numa_online < /sys/devices/system/node/online || true
    line "NUMA online node IDs: ${numa_online:-unavailable}"
fi

section 'Memory'
if [[ -r /proc/meminfo ]]; then
    awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {
        printf "%s %.3f GiB (%s kB)\n", $1, $2/1048576, $2
    }' /proc/meminfo
else
    line 'RAM: unavailable (/proc/meminfo not readable)'
fi

section 'Selected filesystem capacity'
disk_index=0
for disk_target in "${audit_disks[@]}"; do
    ((disk_index += 1))
    line "selected_target: $disk_index (path/device/mount name omitted)"
    if exe_path df >/dev/null; then
        disk_output=$(df -Pk -- "$disk_target" 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            printf '%s\n' "$disk_output" | awk 'NR == 2 {
                printf "capacity_kib: total=%s used=%s available=%s used_percent=%s\n", $2, $3, $4, $5
            }'
        else
            line 'capacity: unavailable (df could not read selected target)'
        fi
    else
        line 'capacity: unavailable (command missing: df)'
    fi
done

section 'GPU display devices'
if exe_path lspci >/dev/null; then
    gpu_devices=$(lspci -nnk 2>/dev/null | awk '
        /^[^[:space:]]/ {
            display=($0 ~ /VGA compatible controller|3D controller|Display controller/)
            if (display) print
            next
        }
        display && /^[[:space:]]+Kernel (driver in use|modules):/ {print}')
    if [[ -n "$gpu_devices" ]]; then
        while IFS= read -r entry; do line "$entry"; done <<< "$gpu_devices"
    else
        line 'display PCI devices: none reported or lspci access unavailable'
    fi
else
    line 'display PCI devices: unavailable (command missing: lspci)'
fi
if nvidia_tool=$(exe_path nvidia-smi); then
    if timeout_tool=$(exe_path timeout); then
        gpu_output=$("$timeout_tool" 10 "$nvidia_tool" --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null)
    else
        gpu_output=$("$nvidia_tool" --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null)
    fi
    if [[ $? -eq 0 && -n "$gpu_output" ]]; then
        line 'NVIDIA fields: name, driver_version, memory.total'
        while IFS= read -r entry; do line "$entry"; done <<< "$gpu_output"
    else
        line 'NVIDIA query: unavailable (driver/query failed or timed out)'
    fi
else
    line 'NVIDIA query: unavailable (command missing: nvidia-smi)'
fi

section 'Compiler, Git, and MPI versions'
version_probe gcc gcc 1 --version
version_probe g++ g++ 1 --version
version_probe Git git 1 --version
version_probe mpirun mpirun 4 --version
version_probe mpiexec mpiexec 4 --version

section 'OpenFOAM inherited environment (explicit allowlist)'
for env_key in WM_PROJECT WM_PROJECT_VERSION WM_PROJECT_DIR WM_PROJECT_USER_DIR \
    WM_PROJECT_INST_DIR WM_DIR WM_OPTIONS WM_ARCH WM_ARCH_OPTION WM_COMPILER \
    WM_COMPILER_TYPE WM_COMPILE_OPTION WM_PRECISION_OPTION WM_LABEL_SIZE WM_MPLIB \
    FOAM_API FOAM_MPI FOAM_ETC FOAM_APPBIN FOAM_LIBBIN FOAM_USER_APPBIN \
    FOAM_USER_LIBBIN FOAM_SITE_APPBIN FOAM_SITE_LIBBIN MPI_ARCH_PATH; do
    if [[ -v "$env_key" ]]; then
        line "$env_key=${!env_key}"
    else
        line "$env_key=<unset>"
    fi
done
line 'OpenFOAM version evidence: inherited variables only; no configuration sourced'
for tool in wmake foamVersion laserbeamFoam; do
    if resolved_tool=$(exe_path "$tool"); then
        line "$tool PATH executable: $resolved_tool"
        if [[ "$tool" == laserbeamFoam ]]; then
            if exe_path readlink >/dev/null; then
                resolved_real=$(readlink -f -- "$resolved_tool" 2>/dev/null)
                [[ -z "$resolved_real" ]] || line "laserbeamFoam resolved file: $resolved_real"
            fi
            if exe_path file >/dev/null; then
                line "laserbeamFoam file type: $(file -b -- "$resolved_tool" 2>/dev/null)"
            else
                line 'laserbeamFoam file type: unavailable (command missing: file)'
            fi
            if exe_path sha256sum >/dev/null; then
                binary_hash=$(sha256sum 2>/dev/null < "$resolved_tool")
                if [[ $? -eq 0 ]]; then
                    line "laserbeamFoam SHA256: ${binary_hash%% *}"
                else
                    line 'laserbeamFoam SHA256: unavailable (file not readable)'
                fi
            else
                line 'laserbeamFoam SHA256: unavailable (command missing: sha256sum)'
            fi
        fi
    else
        line "$tool PATH executable: unavailable (aliases/functions are not executed)"
    fi
done
line 'Executable presence/hash does not establish compilation or simulation validity.'

section 'Explicit local repositories'
if ((${#audit_repos[@]} == 0)); then
    line 'not requested; no repository discovery or remote inspection performed'
elif git_tool=$(exe_path git); then
    for repo_target in "${audit_repos[@]}"; do
        line "requested_repo: $repo_target"
        if [[ ! -d "$repo_target" ]]; then
            line 'repository: unavailable (directory not found)'
            continue
        fi
        # Optional locks prevent status from refreshing the index on disk.
        # Disable fsmonitor hooks and submodule inspection; never add safe.directory.
        git_read=(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_COMMON_DIR
            -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_NAMESPACE
            -u GIT_CONFIG_COUNT -u GIT_CONFIG_PARAMETERS -u GIT_PREFIX
            GIT_OPTIONAL_LOCKS=0 GIT_TERMINAL_PROMPT=0 GIT_NO_LAZY_FETCH=1 "$git_tool"
            -c protocol.allow=never -c core.fsmonitor=false -c core.untrackedCache=false -C "$repo_target")
        repo_root=$("${git_read[@]}" rev-parse --show-toplevel 2>/dev/null)
        if [[ $? -ne 0 ]]; then
            line 'repository: unavailable (not a trusted accessible worktree; no trust/config changes made)'
            continue
        fi
        line "worktree_root: $repo_root"
        commit_hash=$("${git_read[@]}" rev-parse --verify HEAD 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            line "HEAD: $commit_hash"
            commit_date=$("${git_read[@]}" log -1 --format=%cI HEAD 2>/dev/null)
            line "HEAD_committer_date: $commit_date"
        else
            line 'HEAD: unavailable (unborn branch or unreadable commit)'
        fi
        branch_name=$("${git_read[@]}" symbolic-ref --quiet --short HEAD 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            line "branch: $branch_name"
        else
            line 'branch: detached HEAD or unavailable'
        fi
        tracked_status=$("${git_read[@]}" status --porcelain=v1 --untracked-files=no --ignore-submodules=all 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            tracked_count=0
            while IFS= read -r entry; do
                [[ -z "$entry" ]] || ((tracked_count += 1))
            done <<< "$tracked_status"
            line "tracked_change_entries: $tracked_count"
            line 'untracked files and submodule changes: not inspected'
        else
            line 'tracked status: unavailable (read-only status query failed)'
        fi
        line 'remotes: omitted (no remote URL queried; no network operation)'
    done
else
    line 'repository audit: unavailable (command missing: git)'
fi
