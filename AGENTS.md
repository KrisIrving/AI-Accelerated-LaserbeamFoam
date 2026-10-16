# Project execution rules

Before a new development task, read `docs/research/RESEARCH_CHARTER.md`,
`docs/research/DEVELOPMENT_PLAN.md`, and relevant entries in
`docs/research/DECISION_LOG.md`. State which approved stage authorizes the task.
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
- The current stage is low-cost 3D case development. MPI matrices are not gates
  to AI research. Validate MPI when an actual change or workload requires it;
  retain known communication/ray-transfer risks.
- Preserve upstream solvers, libraries and tutorials. No AI, physics changes,
  DEM, full powder runs, workstation access, system changes or automatic cleanup
  are authorized in the current implementation round.
- Use new run directories; keep raw data and private paths in ignored runs/ and
  validation/. CI/mock success is not OpenFOAM execution or physical validation.
- Read the charted change process before treating a new chat suggestion as a
  plan amendment. The charter and Git history are the lasting authority;
  AGENTS.md only assists execution.
