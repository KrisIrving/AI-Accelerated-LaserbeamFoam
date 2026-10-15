# Upstream baseline and validation status

Recorded: 2026-10-15 (Asia/Shanghai).

| Item | Value |
| --- | --- |
| Upstream | <https://github.com/laserbeamfoam/LaserbeamFoam.git> |
| Upstream branch | `OpenFoam_com_main` |
| Baseline commit | `3c93f2657e089e22e9a8298648292969e85a4bad` |
| Baseline commit date | 2026-09-11 17:59:48 UTC |
| Commit subject | Merge pull request #139 from laserbeamfoam/compressible_reformulation |
| Upstream HEAD at initialization | Same as baseline; verified by `git ls-remote` |
| Project origin | <https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam.git> |
| Initialization | Empty target; `main` starts directly at the upstream commit, preserving ancestry. Project additions are proposed on a separate branch. |
| License | Original `LICENSE`, copyright notices and official documentation retained |

The development checkout used a partial **non-shallow** clone. This preserves commit ancestry; ordinary clones of the published project can obtain the original history. No archive/squash import or rewritten upstream history was used.

Upstream history contains legacy large blobs (including a historical tutorial log). They remain as inherited history to preserve traceability; new reports and simulation outputs are ignored and must not be added. Initial repository transfer can therefore be substantially larger than the current source tree.

## OpenFOAM.com v2512 status

| Evidence level | Status |
| --- | --- |
| Static inspection | Top-level `Allwmake` explicitly lists `v2512`, `v2506`, `v2412`. Official README describes v2506; upstream CI matrix currently tests v2506. |
| Workstation environment | **USER-REPORTED** Ubuntu 22.04.5 / OpenFOAM.com v2512 |
| Original solver compile and link | **USER-REPORTED PASSED** at `98f99de8`; `BUILD_ARTIFACT_CHECKS_PASSED` |
| Original Plate2D serial short run | **USER-REPORTED PASSED**: 3,200 cells, 10 steps to `1e-7 s`, exit 0 |
| Both solver compile and link at fa039e70 | **USER-REPORTED PASSED**; `BUILD_ARTIFACT_CHECKS_PASSED` |
| Serial A/B at fa039e70 | **NOT RUN**; input-manifest ordering guard stopped A before OpenFOAM; B not started |
| Script fix / new solver run / serial equivalence | **UNVERIFIED — WAITING FOR UBUNTU** |
| Official 4/8-rank short runs | **UNVERIFIED** |
| Numerical convergence / experiment agreement | **UNVERIFIED** |
| AI speedup | **NOT IMPLEMENTED / NOT MEASURED** |

No compatibility patch is justified by an observed compile error yet. Initial tests must build the upstream source unchanged using official `Allwmake`.

The original-solver status is based on the user's direct workstation feedback, not execution by Codex or an independently inspected raw log archive. See [recorded results](docs/validation/RESULTS.md). It does not validate the new solver merely because its source is statically equivalent.

## Static compatibility observations, not a compilation result

- The ray tracer uses OpenFOAM Lagrangian `Cloud`/`particle` tracking and processor transfer. Key particle APIs inspected between official v2506/v2512 tags did not reveal a direct signature conflict.
- `Cloud.H` changes the template parameter form of `checkFieldFieldIOobject`; this repository does not call that interface directly. This does not establish that every template instantiation will compile.
- Inspected `pimpleControl` and core thermo headers did not reveal a direct mismatch. Linking, runtime selection, dictionaries and MPI still require workstation tests.
- Official build scripts contain nested `tee` pipelines. An exit code or a success banner alone is insufficient: retain child logs, check expected new artifacts and dynamic dependencies.
- The full official build includes libraries, multiple solvers and utilities. A failure in an optional solver is still recorded as a full-build failure; it must not be hidden by a working old `laserbeamFoam` on PATH.

References: [upstream Allwmake](https://github.com/laserbeamfoam/LaserbeamFoam/blob/3c93f2657e089e22e9a8298648292969e85a4bad/Allwmake), [upstream CI](https://github.com/laserbeamfoam/LaserbeamFoam/blob/3c93f2657e089e22e9a8298648292969e85a4bad/.github/workflows/build.yml), [v2512 release notes](https://www.openfoam.com/news/main-news/openfoam-v2512), [v2512 Cloud.H](https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/lagrangian/basic/Cloud/Cloud.H).

Future evidence updates must include project SHA, upstream SHA, OpenFOAM version, `WM_OPTIONS`, test command, exit status and log identifiers. A successful smoke run does not establish numerical or physical accuracy.
