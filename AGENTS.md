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
- The current stage is limited Stage 2 performance analysis. MPI matrices are not gates
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
