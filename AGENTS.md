# AntennaSim working instructions

Read `VISION.md`, `docs/BACKLOG.md`, and the applicable parts of
`docs/PROJECT_PLAN.md` before implementation. Follow `docs/WORKFLOW.md` and
`docs/VALIDATION.md` for numerical work.

- Treat the roadmap as a sequence of evidence-based gates. Do not mark a phase
  complete because code exists or a planning cycle has ended.
- Start with the first ready backlog item unless the user directs otherwise.
  Keep the active implementation scope focused.
- Before implementing an electromagnetic method, document equations, sources,
  conventions, assumptions, stability constraints, and an independent validation
  specification. Proposed validation thresholds are not established accuracy.
- Preserve a clear CPU reference implementation. Validate numerical changes
  before optimizing them; investigate failures rather than loosening tolerances
  to make a test pass.
- Numerical outputs must come from the solver or explicitly identified
  deterministic calculations. Distinguish simulation results, calculations,
  engineering inferences, and AI hypotheses.
- Keep solver logic independent of UI and AI code. Avoid speculative frameworks
  for capabilities that have not reached their planned phase.
- Run applicable build and validation checks. Report checks that could not run.
- Update the backlog, evidence links, and handoff note after meaningful work.
  Record significant architecture or numerical decisions in the decision log.
- Work follows dependencies and evidence, without assumed dates or durations.
  The schedules are not authorization for unrelated scope, scheduled
  automations, external messages, or publication.

The user's current instructions take precedence over these repository routines.
