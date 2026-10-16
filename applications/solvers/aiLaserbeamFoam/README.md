# aiLaserbeamFoam source baseline

This directory forks `applications/solvers/laserbeamFoam` at upstream commit
`3c93f2657e089e22e9a8298648292969e85a4bad` in the same repository.
The original source directory remains unchanged.

The baseline contains the original tracked `.C` and `.H` files, including both
MULES and isoAdvector paths, and the original `Make` descriptions. Its only
intentional source differences are the main file/Application name and a short
source-origin comment. `Make/files` selects the renamed main file and installs
`$(FOAM_USER_APPBIN)/aiLaserbeamFoam`. All headers and `Make/options` retain the
upstream bytes. This includes the original diagnostic filename string in
`createFields.H`. Original copyright, author, and license notices are retained;
the repository's upstream `LICENSE` continues to apply.

There is no AI algorithm or acceleration in this baseline. Source equivalence
does not establish successful compilation, a valid simulation, MPI behavior,
or agreement with the original executable. The static guard can be run without
OpenFOAM from the repository root:

```bash
bash tests/test_ai_solver_source.sh
```

`Make/options` still links the shared upstream `MTHD` and `laserHeatSource`
libraries and uses their upstream include directories. Treat those shared
sources and libraries as read-only while comparing the two executables. Before
introducing any library-side AI change, create isolated source locations and
distinct library names/targets, then update only the AI solver's dependencies.
Renaming this executable alone does not isolate shared-library modifications.
