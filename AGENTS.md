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
- DEC-021 permits only read-only closure, PR history/CI/data review and at most
  one direction proposal. EXP-017 retains pressure-initial-guess NO_GO and marks
  the T/phase fixed-point candidate NOT_READY. No CFD, builds, replay, AI or new
  numerical standards; no restored quotas. Keep PR #5 Draft and unmerged.
- DEC-022 permits only T/phase mathematical/source/literature review and one
  proposed next experiment. EXP-018 remains NOT_READY; new residual contracts
  and the non-CFD manufactured-state gate are drafts, not execution permission.
  No CFD, build, collector/replay implementation, algorithm or AI; PR #5 Draft.
- DEC-023 authorizes one preregistered non-CFD manufactured thermal gate.
  EXP-019 passed with one native build, no S/M1 or time advancement; its quota
  is consumed. Only eligibility to request a separate real-state observation
  is established. No further build/replay/CFD, collector, acceleration or AI
  is authorized; retain all risks and PR #5 Draft/unmerged.
- DEC-024 is a fresh explicitly approved thermal observation batch: one isolated
  build, non-equilibrium manufactured G roundtrip first, then one S and at most
  one frozen M1 collecting only step738 and its original thermal chain. Exact
  output/event/protection gates and a 1200 s deadline apply; failure stops with
  no retry. No convergence continuation, numerical changes, acceleration or AI.
  EXP-020 stopped at its sole build (header dependency order); zero CFD/G.
  This quota is consumed; no repair/rebuild or restored CFD is authorized.
  PR #5 remains Draft/unmerged; prior allowances remain consumed.
- DEC-025 explicitly approves a fresh non-CFD header-dependency repair gate:
  one isolated native single-G build, unchanged manufactured inputs/budgets and
  non-equilibrium direct/snapshot parity/residual tests, 300 s hard deadline.
  Zero S/M1, real capture, time advance, acceleration or AI. Failure stops; old
  EXP-020 artifacts stay read-only. Passing grants request eligibility only.
  EXP-021 passed all four non-CFD gates with one build and zero S/M1. This
  quota is consumed; only eligibility to request new controlled collection is
  established, not permission for further builds/replay/CFD/reference or AI.
  Keep PR #5 Draft and unmerged; earlier quotas remain consumed.
- DEC-026 is a fresh autonomous staged grant: at most three pre-CFD engineering
  build/repair cycles, then one S and one frozen M1 only after preceding gates.
  Capture only step738 first TEqn and its original 21-G chain. Exact output,
  event, replay, residual arithmetic and protection gates apply; failed CFD
  gates stop without reruns. After all real-chain gates pass, one copied frozen
  context may continue at most 64 G / 120 s, under a 1200 s batch deadline. No Time
  advance, numerical/physics changes or AI. Nonconvergence is separate from
  replay failure. Conditional PR5 Ready/Merge Commit is explicitly authorized
  after all actual technical/safety gates, final CI and review pass; retain all
  negative history and risks. EXP-022 stopped at the S signed-zero snapshot
  byte gate: one build and S, zero M1/continuation; two permitted non-CFD text
  format diagnostics also failed. This quota is consumed. PR5 remains Draft
  and unmerged because a core format gate failed. No further execution is
  authorized by these results. Earlier quotas remain consumed.
- DEC-027 is a fresh staged grant after stopped EXP-022: at most three isolated
  pre-CFD engineering cycles, restore every captured binary64 bit directly, reuse
  old S snapshots and parity if the online observer is unchanged. All format,
  native G, independent arithmetic/provenance gates must pass before one frozen
  M1 step738 capture and original 21-G replay. No extra G/continuation, algorithms,
  AI or changed physics/numerics. 1200 s hard batch deadline; no failed CFD rerun.
  Preserve signs of zero and exact comparisons. PR5 stays Draft/unmerged,
  overriding DEC-026's historical conditional merge. Older quotas remain closed.
  EXP-023 restored real S bits and ran one parity-exact M1; round2 prevIter
  timeIndex mismatch stopped full-chain validation. This quota is consumed;
  no extra repair/G/CFD/reference/AI is authorized. Preserve raw captures and
  both controller-error histories. Only propose a fresh zero-CFD lifecycle fix.
- DEC-028 explicitly grants a fresh non-CFD batch: at most three isolated
  build/debug cycles, native lifecycle proof and round1/round2 single-G plus
  continuous-two gates, then one original 21-G replay and no-solve independent
  residuals only after exact parity. Never force prevIter timeIndex or weaken
  metadata/byte checks. 600 s hard deadline; 8 GiB/3 GiB MONITORED_ONLY warnings.
  No S/M1/Time advance/22nd G/continuation/accelerator/AI. PR5 stays Draft,
  unmerged. Passing establishes reference-design request eligibility only.
  EXP-024 passed lifecycle/local/21-round exact replay and all independent
  residual arithmetic with one build/two debug cycles, zero CFD/Time advance.
  Native endpoint remains NONCONVERGED_OBSERVED. This quota is consumed; only
  request eligibility for reference design is established, no further G,
  continuation, algorithm or AI work. Preserve all old failures and PR5 Draft.
- DEC-029 authorizes only mathematical/algorithm/protocol design using EXP-024
  evidence: zero CFD, G/residual evaluations, numerical solves, builds or AI/
  algorithm implementation. Do not promote old observational residual drafts
  to truth criteria. Specify native patch semantics, two distinct routes,
  preregistered calibration/crosschecks and bounded future costs; all future
  execution remains PROPOSED. PR5 stays Draft/unmerged; old risks remain.
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

DEC-030 grants one fresh offline reference-feasibility batch, superseding DEC-029's
historical design-only scope for this batch alone. Preregister before one isolated
native build; calibration must pass before damped native G and complete reduced
semismooth Newton, each from entry/end21 seeds. Hard 600 s and global G52/R400/
Jv510/preparation24 ceilings; calibration R24/Jv6 included. No threshold changes,
new CFD/Time advance/production changes/AI. Stop at failed technical/calibration
gates. Four independently verified roots and endpoint G/crosschecks are required
for a frozen-C reference candidate; no physical/uniqueness claims. Raw tools/data
stay local, PR #5 Draft/unmerged; all historical failures and risks remain.
EXP-026 consumed DEC-030: one build and calibration passed, damped branches
stopped at preregistered line-search rejection, Newton branches stopped before
Krylov because a sufficient conditioning certificate was not established.
INCONCLUSIVE, no verified root or four-way comparison; not proof of no root or
Newton failure. G9/R46/Jv6/preparation2, zero CFD/Time/AI. No remaining execution
permission; keep PR #5 Draft and all risks/failed evidence.
DEC-031 permits only read-only source/metric/mathematical review. EXP-027 confirms
the pointwise inverse sufficient bound is mathematically correct under its
explicit assumptions but provably conservative; nonlinear root/error certification
remains unverified. No G/R/Jv/solve/build/implementation/AI is permitted. The
proposed direction-only test and posterior root certification need fresh approval;
EXP-026 remains INCONCLUSIVE, PR #5 Draft/unmerged, all historical risks retained.
DEC-032 separately authorizes one bounded offline direction-only batch: reuse the
existing native binary/Jv/GMRES, calibrate six manufactured/clip-side directions
first, then at most one 20-step linear direction from each original T seed.
No G, CFD/Time advance, accepted nonlinear state/root search, build/new native
interface or AI. Caps R24/Jv48/preparation2, 120 s, CPU0/thread1; RSS1 GiB/data
200 MiB MONITORED_ONLY. Keep old guards/results read-only; certify only fixed-RHS
true linear residual plus roundoff <1e-9 and preregistered directional checks.
PR #5 Draft/unmerged; subsequent root certification needs fresh authorization.
EXP-028 consumed DEC-032: calibration/provenance passed; one entry direction was
certified. Both native fixed-RHS direct linear checks passed, but end21 failed
the preregistered independent face-RHS check at the same fixed norm; no end21
step diagnostics followed. Overall INCONCLUSIVE, G0/R22/Jv20/preparation2. Zero
CFD/build/G/accepted nonlinear state/AI. Only request eligibility for subsequent
root-existence/posterior-error design, no further numerical permission; PR5 Draft.
