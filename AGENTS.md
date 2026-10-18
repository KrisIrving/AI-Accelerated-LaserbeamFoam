# Project execution rules

Before a new task, read this file, [PROJECT_HUB](docs/PROJECT_HUB.md),
`docs/research/RESEARCH_CHARTER.md`, `docs/research/DEVELOPMENT_PLAN.md`, and
relevant entries in `docs/research/DECISION_LOG.md`, then task-specific sources
and detailed docs. State which approved stage or explicit owner instruction
authorizes the task. The hub is a navigation summary, not plan or raw evidence.
Also follow the existing `.agents/skills/laserbeamfoam/SKILL.md` conventions.

- Approved goals, stage priorities, acceptance thresholds and benchmark
  definitions are controlled. Discussion and model suggestions are proposals,
  not authorization. Explicit owner approval specifying the change is required
  before updating these decisions. Report conflicts; retain the approved plan.
- Ordinary implementation and experiment records within approved scope can
  proceed. Append evidence to EXPERIMENT_LOG; mark unmeasured results UNVERIFIED.
  Candidate configurations stay PROPOSED until explicitly approved as benchmarks.
- Every approved plan change appends a dated decision with old/new scope,
  rationale, approval evidence and Git traceability. Never erase historical
  decisions or lower accuracy requirements to make a failed test pass.
- DEC-017 closes the bounded Stage 2 study and authorizes PR #4 review, Ready
  transition and Merge Commit only after review/checks pass. Earlier Draft-only
  decisions remain historical; completed experiment allowances are exhausted.
  MAG caching is closed NO_BENEFIT. The next AI candidate is PROPOSED only;
  no AI implementation, new CFD or changed numerical standards are authorized.
  MPI matrices are not gates
  to AI research. Validate MPI when an actual change or workload requires it;
  retain known communication/ray-transfer risks.
- Preserve upstream solvers, libraries and tutorials. DEC-011 explicitly
  authorizes local Ubuntu execution of three fresh native M1 performance runs
  and at most one conditional external sampling run within its guards.
  DEC-012 additionally authorizes one isolated switchable coarse-timing S gate
  and at most one frozen M1 observation run; original sources/results stay read-only.
  No AI, physics changes, DEM, full powder runs, system changes or automatic
  cleanup are authorized; earlier experiments and raw data remain protected.
- DEC-013 authorizes only read-only T/p source/log analysis and one future
  PROPOSED experiment plan; no new CFD. Completed DEC-011/012 runs are not renewed.
- DEC-014 subsequently authorizes the single seven-site internal observation:
  one S gate then at most one frozen M1; exact outputs/events and timer closure
  required, batch deadline 20 minutes. No AI/physics/tolerance changes.
- DEC-015 permits only read-only dependency audit and a single proposed candidate/
  protocol; no new CFD, optimization implementation, AI or numerical changes.
- DEC-016 authorizes only T_LOCAL_NATIVE_MAG_GRADALPHA native-field tests first;
  stop without CFD if its conservative cost screen rejects a 2% solver gain.
  Only otherwise one S and one M1 OFF/ON pair, with unchanged exact checks.
- DEC-018 subsequently authorizes pressure-system collection/replay only: non-CFD
  tests, at most one S and one fixed M1, exact field/event equivalence, 1200 s
  batch deadline. No AI training/integration; report via a new PR, merge only
  after all numerical/protection/CI gates pass. EXP-014 stopped at the pre-CFD
  replay build gate: zero CFD, INCONCLUSIVE, no retry; its PR stays Draft because
  numerical gates did not pass. This batch allowance is consumed. Earlier
  allowances stay closed.
- DEC-019 is a fresh, non-CFD-only authorization after EXP-014: one isolated
  native replay build, then synthetic format/boundary/reference/residual/PCG
  tests if build passes, 300 s deadline, no rebuild after failure. No S/M1,
  real-system collection or AI. EXP-015 passed all four synthetic gates with
  one build; that quota is consumed. Only eligibility to request future CFD
  is established, not execution permission. Keep PR #5 Draft; do not merge.
- DEC-020 is a fresh controlled real pressure-system batch: reuse verified
  replay tools, one S gate then at most one frozen M1, exact outputs/events and
  baseline replay required, 1200 s deadline. No retry/resume or AI; older quotas
  stay closed. EXP-016 passed collection/replay with one S and one M1; its quota
  is consumed. Current research recommendation is NO_GO for approving AI
  initial-guess development, not a permanent route change. No further work is
  authorized by those results. Keep PR #5 Draft; do not merge.
- Use new run directories; keep raw data and private paths in ignored runs/ and
  validation/. CI/mock success is not OpenFOAM execution or physical validation.
- Check PROJECT_HUB at new PRs, major feature completion, registered workstation
  results, approved decisions, benchmark validation and confirmed/resolved key
  bugs. Update material status changes with evidence in the corresponding PR;
  do not create a documentation commit for every chat. Check navigation links
  when adding or moving docs. This does not authorize controlled plan changes.
- Read the charted change process before treating a new chat suggestion as a
  plan amendment. The charter and Git history are the lasting authority;
  AGENTS.md only assists execution.
