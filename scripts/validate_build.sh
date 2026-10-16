#!/usr/bin/env bash
# Calls unchanged upstream Allwmake; never cleans or installs into old user bins.
set -euo pipefail
export LC_ALL=C

usage() {
    printf 'Usage: bash scripts/validate_build.sh --report-dir REPO/validation/NEW_DIR [--jobs 8|12]\n'
}
jobs=8
report_arg=
while (($#)); do
    case "$1" in
        --jobs) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; jobs=$2; shift 2 ;;
        --report-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; report_arg=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
[[ $jobs == 8 || $jobs == 12 ]] || { echo 'First validation permits only 8 or 12 jobs.' >&2; exit 2; }
[[ -n $report_arg ]] || { usage >&2; exit 2; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ ${WM_PROJECT_VERSION-} == v2512 ]] || { echo 'Load of2512 in your terminal first; expected WM_PROJECT_VERSION=v2512.' >&2; exit 2; }
[[ -d ${WM_PROJECT_DIR-}/wmake ]] || { echo 'WM_PROJECT_DIR/wmake missing.' >&2; exit 2; }
command -v wmake >/dev/null || { echo 'wmake is not on PATH.' >&2; exit 2; }
[[ -x /usr/bin/time ]] || { echo 'GNU /usr/bin/time is required; no packages are installed automatically.' >&2; exit 2; }
out=$(realpath -m -- "$report_arg")
validation_root=$(realpath -m -- "$repo/validation")
[[ $out == "$validation_root/"* ]] || { echo 'Report directory must be inside this checkout/validation/.' >&2; exit 2; }
[[ ! -e $out && ! -L $out ]] || { echo 'Report directory already exists; choose a new name. Nothing was cleaned.' >&2; exit 2; }
mkdir -p -- "$out/install/bin" "$out/install/lib"
export FOAM_USER_APPBIN="$out/install/bin"
export FOAM_USER_LIBBIN="$out/install/lib"
export PATH="$FOAM_USER_APPBIN:$PATH"
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:${LD_LIBRARY_PATH-}"
export WM_NCOMPPROCS=$jobs
{
    printf '# Source AFTER loading of2512; only this validation install is selected.\n'
    printf 'export FOAM_USER_APPBIN=%q\n' "$FOAM_USER_APPBIN"
    printf 'export FOAM_USER_LIBBIN=%q\n' "$FOAM_USER_LIBBIN"
    printf 'export PATH=%q:"$PATH"\n' "$FOAM_USER_APPBIN"
    printf 'export LD_LIBRARY_PATH=%q:"${LD_LIBRARY_PATH-}"\n' "$FOAM_USER_LIBBIN"
} > "$out/env.sh"
cd -- "$repo"
{
    echo 'schema=ai-laserbeamfoam-build-v1'
    printf 'project_commit=%s\n' "$(git rev-parse HEAD)"
    printf 'openfoam_version=%s\nWM_OPTIONS=%s\njobs=%s\n' "$WM_PROJECT_VERSION" "${WM_OPTIONS-UNSET}" "$jobs"
    printf 'started_utc=%s\n' "$(date -u +%FT%TZ)"
    echo 'command=./Allwmake -j N (unchanged upstream entry point)'
    echo 'existing_installation_modified=no; source-tree build logs/objects may be written'
} > "$out/summary.txt"
printf 'Building with %s jobs. Log: %s/build.stdout-stderr.txt\n' "$jobs" "$out"
set +e
/usr/bin/time -v -o "$out/time.Allwmake.txt" ./Allwmake -j "$jobs" > "$out/build.stdout-stderr.txt" 2>&1
build_rc=$?
set -e
printf 'upstream_exit_code=%s\nfinished_utc=%s\n' "$build_rc" "$(date -u +%FT%TZ)" >> "$out/summary.txt"
while IFS= read -r -d '' file; do
    mkdir -p -- "$out/source-logs/$(dirname -- "$file")"
    # Upstream searches the whole checkout for exact name log.Allwmake.
    # Never create archived files of that name inside validation/.
    cp -- "$file" "$out/source-logs/$file.txt"
done < <(find src applications -type f -name log.Allwmake -print0)
failed=0
((build_rc == 0)) || failed=1
: > "$out/binary.sha256"
: > "$out/custom-libraries.sha256"
for app in laserbeamFoam aiLaserbeamFoam laserMeltFoam compressibleLaserbeamFoam microstructureFoam setSolidFraction TesselateFoam; do
    if [[ -x $FOAM_USER_APPBIN/$app ]]; then
        printf 'artifact_%s=present_in_new_install\n' "$app" >> "$out/summary.txt"
        sha256sum "$FOAM_USER_APPBIN/$app" >> "$out/binary.sha256"
        if ! ldd "$FOAM_USER_APPBIN/$app" > "$out/ldd.$app.txt" 2>&1 || grep -q 'not found' "$out/ldd.$app.txt"; then
            printf 'dependencies_%s=REVIEW_REQUIRED\n' "$app" >> "$out/summary.txt"
            failed=1
        fi
        awk '$2 == "=>" && $3 != "not" { print $1 "\t" $3 }' "$out/ldd.$app.txt" |
            sort > "$out/dependencies.$app.tsv"
        if [[ $app == laserbeamFoam || $app == aiLaserbeamFoam ]]; then
            # LD_LIBRARY_PATH can otherwise silently select an old same-name library.
            if ! awk -v libdir="$FOAM_USER_LIBBIN" '
                $1 == "libMTHD.so" || $1 == "liblaserHeatSource.so" {
                    seen++; if ($2 != libdir "/" $1) wrong=1
                }
                END { exit (seen != 2 || wrong) }
            ' "$out/dependencies.$app.tsv"; then
                printf 'project_library_origin_%s=REVIEW_REQUIRED\n' "$app" >> "$out/summary.txt"
                failed=1
            fi
        fi
    else
        printf 'artifact_%s=MISSING\n' "$app" >> "$out/summary.txt"
        failed=1
    fi
done
for lib in geometricVoFLMFOAM laserHeatSource MTHD laserbeamFoamFunctionObjects incompressibleTransportModelsLMFOAM incompressibleTurbulenceModelLMFOAM multiphaseVapMixtureThermo; do
    if [[ ! -f $FOAM_USER_LIBBIN/lib$lib.so ]]; then
        printf 'library_%s=MISSING\n' "$lib" >> "$out/summary.txt"
        failed=1
    else
        sha256sum "$FOAM_USER_LIBBIN/lib$lib.so" >> "$out/custom-libraries.sha256"
    fi
done
if [[ -s $out/dependencies.laserbeamFoam.tsv && -s $out/dependencies.aiLaserbeamFoam.tsv ]]; then
    if ! diff -u "$out/dependencies.laserbeamFoam.tsv" "$out/dependencies.aiLaserbeamFoam.tsv" > "$out/dependencies.ab.diff.txt"; then
        echo 'AB_dynamic_dependency_origins=DIFFERENT_REVIEW_REQUIRED' >> "$out/summary.txt"
        failed=1
    fi
fi
if grep -En 'fatal error:|undefined reference to|\*\*\*.*(Error|Stop)|\*\* BUILD ERROR \*\*' "$out/build.stdout-stderr.txt" > "$out/build-error-matches.txt"; then
    failed=1
fi
if ((failed)); then
    echo 'status=BUILD_REVIEW_REQUIRED; runtime_and_accuracy=UNVERIFIED' >> "$out/summary.txt"
    cat "$out/summary.txt"
    exit 1
fi
echo 'status=BUILD_ARTIFACT_CHECKS_PASSED; runtime_and_accuracy=UNVERIFIED' >> "$out/summary.txt"
cat "$out/summary.txt"
echo 'Review logs before running a case. This is not runtime or accuracy validation.'
