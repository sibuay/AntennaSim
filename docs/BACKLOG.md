# Backlog and project status

Last updated: 2026-09-18.

## Current position

- **Active phase:** P2 — Materials and closed domains (in progress; P0 and
  P1 gates passed; MAT-01 complete).
- **Completed capability:** planning records, a verified C++20/CMake build scaffold,
  reviewed reference Yee-grid conventions, fixed initial benchmark specifications,
  structurally checked core grid metadata/input/allocation validation, and six
  staggered field arrays with checked indexing, native positions, and wall classification;
  strict CFL selection and reference E/H stepping, impressed currents, native
  probes, fixed benchmark fixtures and CLI raw output with structural/smoke checks;
  an independent analyzer with validated reductions, the measured V01–V03
  physical report (36 propagation and four 20,000-step stability cases), and the
  P1 gate record with a clean-build exact reproduction of those measurements;
  the P2 method note (PEC edge masks, isotropic dielectric/conductivity update,
  spectral conventions) and the V04–V07/S09–S14 specifications with fixed
  tolerances, backed by a passing standard-library audit registered in CTest.
- **Validated numerical capability:** axis-aligned vacuum eigenwave propagation,
  signed impedance, second-order refinement, and closed-grid long-time stability
  within the FND-04 v1 envelope, as bounded in the
  [P1 gate record](validation/REF-06-reference-propagation-gate.md). No
  PEC-resonance, material, open-boundary, oblique/broadband, port, or antenna
  capability is validated.
- **Active implementation item:** none.
- **Next ready item:** MAT-02 — explicit PEC edge masks and V04 cavity evidence
  under the fixed MAT-01 specification.
- **Scheduling rule:** milestone-based, with no assumed dates or durations.
- **Blockers:** none for MAT-02. The compiler ran inside the ordinary session
  sandbox on 2026-09-16 through 2026-09-18; standalone Windows CLI runs still
  need the compiler runtime directory on the process PATH. Commits after
  `b98bc4c` are local until the owner pushes `main`, so their hosted CI result
  is pending.

Status vocabulary: **Ready**, **Planned**, **In progress**, **Blocked**, **Done**.
Ready means prerequisites are satisfied. Done requires linked evidence, not just
an implementation. Keep at most one primary implementation item in progress;
necessary validation and documentation belong to that item.

## Foundation and reference-kernel backlog

Default execution follows the table order. Dependencies express the minimum
prerequisites; the chosen sequence may be stricter to keep work focused.

| ID | Phase | Item | Depends on | Status | Completion evidence |
| --- | --- | --- | --- | --- | --- |
| PLN-01 | P0 | Record roadmap, schedule, routines, and validation policy | — | Done | Project records linked from README; this planning baseline |
| FND-01 | P0 | Inventory environment and choose minimum toolchain | — | Done | [Environment record](ENVIRONMENT.md) |
| FND-02 | P0 | Scaffold C++20/CMake library, CLI target, tests, presets | FND-01 | Done | [Debug/Release build evidence](validation/FND-02-build.md) |
| FND-03 | P0 | Document units, staggering, indexing, time convention, and boundary policy | FND-01 | Done | [Method/conventions](methods/FND-03-yee-conventions.md); [review and checks](validation/FND-03-review.md) |
| FND-04 | P0 | Specify initial benchmarks and justify tolerances | FND-03 | Done | [Version-1 specifications](validation/FND-04-reference-benchmarks.md); [review/calculations](validation/FND-04-review.md) |
| FND-05 | P0 | Review foundation gate | FND-02, FND-04 | Done | [P0 gate: pass](validation/FND-05-foundation-gate.md) |
| REF-01 | P1 | Implement core types, grid extents, and input validation | FND-05 | Done | [API/acceptance contract](methods/REF-01-core-grid-contract.md); [136 structural checks / build evidence](validation/REF-01-core-grid.md) |
| REF-02 | P1 | Implement staggered field storage and component indexing | REF-01 | Done | [Storage/access contract](methods/REF-02-field-storage-contract.md); [23838 checks / 1976 stencil reads / build evidence](validation/REF-02-field-storage.md) |
| REF-03 | P1 | Implement time-step selection and reference E/H updates | REF-02 | Done | [CFL/update contract](methods/REF-03-reference-update-contract.md); [27013 checks / exact-rational half-stage evidence](validation/REF-03-reference-updates.md) |
| REF-04 | P1 | Add minimal source, probes, run configuration, and CLI output | REF-03 | Done | [Source/run contract](methods/REF-04-run-contract.md); [3337 checks, S07/S08 and deterministic CLI evidence](validation/REF-04-reference-runs.md) |
| MNT-01 | P1 support | Harden validation, source-control traceability, CI, and durable evidence | REF-04 | Done | [Maintenance evidence](validation/MNT-01-repository-hardening.md); commits `5930643`/`3043b39`/`b342821` on `origin/main`; hosted Debug/Release runs passed 2026-09-16; D016 |
| REF-05 | P1 | Measure propagation, impedance, stability, and refinement behavior | REF-04 | Done | [Measurement contract](methods/REF-05-measurement-contract.md); [36/36 propagation, 4/4 stability, refinement/enlarged evidence](validation/REF-05-reference-measurements.md); [compact metrics](validation/REF-05-analysis-summary.json); D017 |
| REF-06 | P1 | Review reference-propagation gate | REF-05 | Done | [P1 gate: pass; supported limits; clean-build exact reproduction](validation/REF-06-reference-propagation-gate.md) |
| MAT-01 | P2 | Specify PEC, dielectric, conductivity, and spectral conventions | REF-06 | Done | [Method note](methods/MAT-01-closed-domain-conventions.md); [V04–V07/S09–S14 specification](validation/MAT-01-closed-domain-benchmarks.md); [audit/review evidence, 13/13 CTests](validation/MAT-01-review.md); D018 |
| MAT-02 | P2 | Implement and validate explicit PEC boundaries/cavity | MAT-01 | Ready | V04 evidence and existing regressions |
| MAT-03 | P2 | Implement and validate dielectric and conductive updates | MAT-02 | Planned | V05–V06 evidence and existing regressions |
| MAT-04 | P2 | Implement spectral processing and validate sampling/normalization | MAT-03 | Planned | V07 and cavity spectral evidence |
| MAT-05 | P2 | Review materials/closed-domain gate | MAT-04 | Planned | P2 gate record and P3 breakdown |

MAT-02 can use an independently checked analysis script for initial cavity
evidence; MAT-04 subsequently validates the production spectral path against it.
The [P1 gate record](validation/REF-06-reference-propagation-gate.md) expands each
P2 item with its scope, completion test, and evidence location.

## Later work queue

Expand a phase into actionable items at the preceding gate. Each new item needs
an ID, dependencies, a completion test, and an evidence location before starting.

| Phase | Queued scope | Status |
| --- | --- | --- |
| P3 | Absorbing boundary method, implementation, reflection and late-time tests | Planned |
| P4 | Lumped port, sampling, impedance and S11 reference comparisons | Planned |
| P5 | NF2FF, radiation/power metrics, dipole validation | Planned |
| P6 | Patch benchmark, persistence, parameterization, initial setup audit | Planned |
| P7 | Nonuniform meshing, refinement, automatic convergence | Planned |
| P8 | Profiling and CPU parallelization | Planned |
| P9 | CUDA backend and CPU/GPU consistency | Planned |
| P10 | Desktop CAD and expert simulation workflow | Planned |
| P11 | Professional visualization and result comparison | Planned |
| P12 | Sweeps, optimization, guided AI workflow | Planned |
| P13 | Justified MoM scope and multi-solver support | Planned |

## Session handoff

**2026-09-18 — MAT-01 P2 conventions and V04–V07 specifications complete**

- Wrote the [P2 method note](methods/MAT-01-closed-domain-conventions.md):
  per-cell isotropic `eps_r>=1`, `sigma>=0`, `mu=mu0`; four-cell arithmetic
  edge averaging; Schneider's time-centred conductivity coefficients in a form
  that reproduces the vacuum kernel bitwise; the eps-weighted dissipation
  identity `Q_(n+1)=Q_n-D_n` that keeps the vacuum CFL policy valid for every
  allowed material; E-edge PEC masks with the outer closure as a special case;
  `exp(-i omega t)*dt` transforms with rectangular/Hann windows; closed-form
  discrete references (cavity modes and line strengths, reduced TE interface
  `R_d`, slab-cavity roots, lossy growth factor). Sources rechecked from the
  extracted text of Schneider chapters 3, 7, and 9 with section/equation/page
  references.
- Wrote the [V04–V07 specification](validation/MAT-01-closed-domain-benchmarks.md):
  V04-A eigenmodes (30 cases, caps 0.0052/0.0013/0.000325), V04-B driven spectrum
  (8 required lines, 0.25-bin identification, two record lengths), V04-C interior
  PEC enforcement (exact zeros, bitwise equivalence), V05-A dielectric eigenwave,
  V05-B TE-mode interface (7 cases, closed-form discrete `R_d`, caps
  0.06/0.0135/0.0034), V05-C slab-loaded cavity (18 cases), V06-A lossy eigenwave
  (26 cases, decay/phase caps), V06-B dissipation identity, V06-C zero-conductivity
  bitwise regression, V07 synthetic spectra, S09–S14, analyzer/oracle coverage
  extensions, CLI/analysis contract, and a calculated 5.36e9 cell-step budget.
- Added `scripts/check_material_benchmarks.py` (standard library; CTest
  `reference.material_specification`, about 14.5 s) computing every prediction
  and cap, checking the estimators and fault detection on synthetic data, and
  verifying the V05-B gating/isolation against a pure-Python reduced-TE oracle
  (agreement 1.3e-5 with the closed form). Two fixture defects were found and
  fixed during the audit: a near-degenerate cavity line pair inside the spectral
  cutoff, and interface pulse content near the guide cutoff that leaked across
  the time gate (fixed by a taller guide and re-derived layout; two rejected
  layouts admitted wall echoes). No solver, fixture, tolerance, test, or analyzer
  of P1 changed.
- Fresh `build/MAT-01-release` and `build/MAT-01-debug` trees configured, built
  without warnings, and pass 13/13 CTests; see the
  [review](validation/MAT-01-review.md). Records updated: backlog, project plan,
  schedule, validation plan, README, decision log (D018).
- Next exact action: MAT-02. Implement the E-edge PEC mask (outer closure plus
  grid-aligned boxes) in the reference kernel with its contract note, the S09
  structural test, the `closed-v1` `cavity`/`cavity-spectrum`/`pec` suites and
  their fixtures (exact discrete eigenmodes, antisymmetric pulse, exterior and
  surface maxima), the independent analyzer with the V04 reductions and the
  synthetic fault-injection coverage listed in the specification, then run V04
  from a clean Release build. Preserve all thirteen CTests and the V01–V03
  suites; the vacuum path must stay bitwise identical.

### Previous handoff (historical)

**2026-09-17 — REF-06 P1 gate review complete**

- Reviewed the Phase 1 deliverables and exit criteria against the REF-01–REF-05
  evidence in a [gate record](validation/REF-06-reference-propagation-gate.md):
  every criterion has linked passing measurements; decision **PASS** within the
  declared envelope (axis-aligned vacuum eigenwaves, reflecting box, declared
  grids/durations). The supported and unvalidated limits are listed there.
- Fresh `build/REF-06-release` and `build/REF-06-debug` trees configured, built
  without warnings, and passed 12/12 CTests (Release 14.37 s; Debug
  28.04 s). The Release fingerprint equals REF-05's
  `f9ddf4f2…`; all 35 REF-05 manifest entries matched before edits.
- The full 36-case propagation and 4-case stability suites were re-run from the
  fresh Release executable and re-analyzed; the new
  `scripts/compare_reference_analysis.py` (standard library, fault-checked
  before use) found all 1211 compared values (40 cases, 823 floating-point) identical
  at zero tolerance. Resources: propagation 596.61 s / 1.03 GB peak working
  set, stability 174.07 s / 5.2 MB, within the 2 GiB budget.
- No solver, fixture, tolerance, test, or analyzer changed. Records updated:
  backlog, project plan, schedule, validation plan, README, decision-log note.
- Next exact action: MAT-01. Write the P2 method notes and V04–V07
  specifications (explicit PEC surfaces and their relation to the current
  closure; isotropic dielectric and constant-conductivity updates with stability
  and frequency scope; spectral processing conventions) with fixed, justified
  tolerances, resource budgets, and the required S01–S08/analyzer coverage
  extensions, before any P2 solver code. Preserve all twelve CTests and the
  V01–V03 suites as permanent regressions.

### Previous handoff (historical)

**2026-09-16 — REF-05 physical measurements complete**

- Added `scripts/analyze_reference_benchmarks.py` (independent V01–V03 analysis
  of the raw artifacts against the fixed v1 limits, exits nonzero on failure while
  retaining outputs), `scripts/check_reference_analysis.py` (97 synthetic
  pass/fault-detection checks plus a pure-Python transcription of the update
  equations, V03 fixture and weighted U/Q diagnostic compared with production
  smoke output within 1e-12; CTest `reference.analysis_reductions`), and
  `scripts/run_reference_benchmarks.py` (serial suite runner with elapsed/peak
  working-set measurement). No solver, fixture, or tolerance changed.
- Clean Release and Debug builds pass 12/12 CTests without warnings (13.39 s /
  23.81 s). Full suites from the clean Release build: 36/36 propagation cases,
  six refinement sequences (orders 2.0039/2.0010), six enlarged comparisons
  (max difference 2.8e-14), and 4/4 stability cases (invariant drift <= 1.3e-15
  over 20,000 source-free steps) pass. Propagation took 606.45 s with a 1.03 GB
  peak working set; stability 158.58 s. See the
  [evidence](validation/REF-05-reference-measurements.md).
- Three analysis/self-test construction defects were fixed before the physical
  runs; none was a solver finding. A post-run review found three evidence
  acceptance gaps in the analyzer (unchecked probe-line indices, unenforced
  2 GiB budget, crash on corrupt metadata); revision 2 fixes them with
  fault-injection checks, and run1 was re-analyzed with identical numerical
  results. The CMake source fingerprint is the SHA-256 of the LF-normalized
  snapshot text (Windows writes CRLF); documented.
- Next exact action: REF-06 gate review. Review the P1 exit criteria against
  REF-01–REF-05 evidence, record the supported limits (axis-aligned vacuum,
  reflecting box, declared durations), decide pass/continue, and expand the P2
  breakdown only after the gate record exists. No new solver scope.

### Previous handoff (historical)

**2026-09-15 — Review, push, and MNT-01 status correction**

- Independent read-through of the core library, benchmark library, tests, audit
  scripts, build files, and workflow found no numerical or structural defect.
  Kernel stencils, update ordering, wall handling, impressed-current sign, and the
  discrete energy diagnostic were checked against the FND-03/FND-04 conventions.
- Clean Debug and Release configure/build/CTest from empty directories pass 11/11
  with no compiler warnings (12.79 s / 4.50 s). Pinned action majors v7 exist.
- `main` had been two commits ahead of `origin/main`; `5930643` and `3043b39` are
  now pushed, so the REF-04 evidence maps to a hosted revision. MNT-01 is moved
  back to In progress until the first hosted Ubuntu/GCC result is recorded: no
  compiler other than Clang 20 has built this code yet.
- Removed an unused `<numeric>` include from the benchmark library and documented
  the pip launcher shim under `.tools/cmake/bin/`. No numerical change.
- 2026-09-16 update: the owner reported both hosted Debug/Release runs passed;
  MNT-01 is Done. Next exact action: begin REF-05 as previously specified. Observation for REF-05 planning: the checked-access reference kernel
  and per-state diagnostics make the 20,000-step stability cases minutes-scale.

### Previous handoff (historical)

**2026-09-11 — MNT-01 validation and repository hardening complete**

- Preserved the reviewed REF-04 implementation as commit `5930643`, after the
  redundant worktree and branch were removed. The exact historical SHA-256
  manifest remains unchanged and now maps to a durable Git revision.
- Made Python mandatory for validation builds and registered the three independent
  convention/specification/golden-state scripts in CTest. Validation now fails
  during configuration rather than silently passing a reduced suite. Debug and
  Release pass 11/11 CTests in 13.59/4.48 s without compiler warnings; the
  AddressSanitizer/UndefinedBehaviorSanitizer suite passes 11/11 in 54.53 s.
- Added read-only GitHub Actions Debug/Release validation for `main` pushes and
  pull requests, with Python 3.13 and 90-day CTest/source/smoke artifact retention.
  The workflow is locally reviewed; its first hosted execution awaits a push.
- Added a tracked compact REF-04 audit summary and stopped treating ignored local
  build logs as durable repository evidence. Licensing/public distribution remains
  open under O005; source-control and CI selection are resolved by D016.
- Numerical implementation and acceptance thresholds are unchanged. REF-05 remains
  the next ready item, and no physical propagation, impedance, or stability pass
  is claimed.

### Previous handoff (historical)

**2026-09-10 — REF-04 reference run facilities complete**

- Added validated sparse impressed E-edge currents and half-time amplitudes,
  preserving rho=0 initial screening and defining later charge by continuity.
  Added native probes, strict step parsing, separate benchmark library, all 36
  propagation/four stability configurations, independent compact-curl fixtures,
  streamed raw CSV/metadata and an exclusive fresh-directory completion marker.
- Debug/Release pass 8/8 CTests without warnings (12.48/3.88 s). The retained six
  tests pass; `reference.run` adds 3337 source/probe/input/failure checks and
  S08 fixture checks. Worst normalized divergence 1.96348e-16, plateau error
  7.54952e-15. S07 independent synthetic complex ratio error 2.6666e-16.
  All three prior Python audits pass. No numerical threshold changed.
- End-to-end smoke outputs repeat byte-for-byte for both CSV files per case;
  metadata/coordinates/timestamps, invalid arguments, overwrite refusal, and
  incomplete-artifact rejection pass an independent reader. Final measured
  Release smoke: 0.5339/0.5362 s, peak working sets 20,070,400/20,078,592 bytes.
  See [evidence](validation/REF-04-reference-runs.md), the
  [durable audit summary](validation/REF-04-audit-summary.json), and D015.
- Addressed the known compiler sandbox restriction via approved execution. One
  compiler signedness warning was fixed. An incorrect oracle `--check` argument
  was corrected to no arguments. A standalone CLI missing runtime PATH stalled
  at startup and was stopped; the corrected command passes. These were tooling
  issues, not numerical test failures. No clean-build/sanitizer/platform claim.
- Next exact action: REF-05. Implement `scripts/analyze_reference_benchmarks.py`
  using the independently tested `reference_measurements.py`, with strict raw
  artifact completeness/native sample checks and fixed v1 acceptance tables.
  Execute all 36 propagation cases and four 20,000-source-free-step stability
  cases, record measured resource use and all failures, and build the physical
  report/refinement/domain/long-time traces. Validate diagnostic/measurement
  reductions independently before accepting their physical results. Preserve
  all eleven CTests; repeat physical suites from a clean
  Release build as specified. Source cutoff is state 8 for driven stability.
- Full propagation/enlarged/refinement and long-time suites have not run. C03
  remains in progress until the first measured report; P1 remains open. Larger
  fixture identities and peak memory are checked during those full runs, not
  inferred from smoke. No physical propagation/impedance/stability pass claimed.

### Previous handoff (historical)

**2026-09-07 — REF-03 reference updates complete**

- Implemented pinned vacuum constants, `VacuumTimeStep` strict CFL/coefficient/
  native-time checks, and owned `ReferenceStepper` with initial finiteness/wall/
  divergence screening, all-H-before-E updates, and terminal failure diagnostics.
  Local detail kernels serve independent structural harnesses. See the
  [contract](methods/REF-03-reference-update-contract.md) and
  [evidence](validation/REF-03-reference-updates.md).
- Debug and Release pass 6/6 tests without warnings. `reference.vacuum` runs
  27013 checks; worst normalized two-step golden error 1.3323e-15 (limit 1e-13),
  adjoint residual 7.6635e-17 (limit 1e-12), exact affine and div-curl checks.
  Final CTest totals: 0.55/0.44 s. Prior grid/field/foundation regressions pass.
  CLI help now accurately states simulation commands are unavailable.
- Both prior analytical audits and the new exact-rational golden reproduction
  check pass. Generator write initially needed a Python 3.9 compatibility fix;
  no numerical test failed or tolerance changed. Logs under `build/REF-03-*`.
  D014 records API/failure/initial-condition decisions. Incremental approved
  Windows x64 builds; no new clean-build, sanitizer, or cross-platform claim.
- Next exact action: REF-04. Specify minimal J coupling and charge interpretation,
  run configuration/step-count parsing, native probes and timestamp output, and
  reference benchmark CLI/artifacts. Complete S06 source sign and S07/S08 fixture
  obligations; retain all six CTests and three Python audit/oracle checks.
  Public stepping currently supports source-free rho=0 initialization; broaden
  source handling explicitly without relaxing current initial checks by accident.
- C02 is complete by reviewed storage/indexing/CFL evidence. C03 is in progress;
  P1 remains open. No physical propagation/impedance/long-time benchmark passed.
  REF-04 must account for transient initial-field copying in the 2 GiB budget;
  REF-05 performs measured physical validation. No durations are assumed.

## Activity log

| Date | Record | Outcome / schedule effect |
| --- | --- | --- |
| 2026-09-05 | Initial planning | Baseline created; C01 is the first work package; all implementation remains pending |
| 2026-09-05 | Scheduling preference | Removed calendar windows and capacity assumptions per owner instruction |
| 2026-09-05 | FND-01 / FND-02 complete | Portable toolchain and Debug/Release build verified; FND-03 ready; P0 remains open |
| 2026-09-05 | FND-03 complete | Yee conventions and exact-arithmetic audit reviewed; O002 resolved; FND-04 ready; P0 remains open |
| 2026-09-05 | FND-04 complete | V01–V03/S01–S08 specifications and analytical budgets reviewed; O003 resolved; FND-05 ready; P0 remains open |
| 2026-09-06 | FND-05 / P0 gate passed | Clean approved Debug/Release builds pass 3/3 each; specifications/audits reviewed; C01 complete; REF-01 and C02 ready; no validated physics |
| 2026-09-06 | REF-01 complete | Core grid and allocation/input checks pass; Debug/Release 4/4 each with 136 grid assertions; REF-02 ready; P1/C02 remain open |
| 2026-09-07 | REF-02 complete | Six field arrays and checked positions/indexing/wall geometry pass; Debug/Release 5/5 each, 23838 field checks and 1976 stencil reads; REF-03 ready; P1/C02 remain open |
| 2026-09-07 | REF-03 complete / C02 reviewed | Strict CFL and source-free E/H updates pass 27013 kernel checks; Debug/Release 6/6; exact-rational two-step comparisons pass; C02 complete, C03 in progress, REF-04 ready, P1 open |
| 2026-09-10 | REF-04 complete | Impressed currents, native probes, fixed fixtures/CLI raw artifacts pass 3337 additional checks and independent artifact/S07 audits; Debug/Release 8/8; REF-05 ready; full physical measurements pending, C03/P1 open |
| 2026-09-15 | Review and push | Clean Debug/Release 11/11 without warnings; `main` pushed to `origin`; MNT-01 returned to In progress pending the first hosted CI result; REF-05 still next |
| 2026-09-16 | MNT-01 complete | First hosted Ubuntu Debug/Release runs passed for `3043b39` and `b342821`; MNT-01 Done; REF-05 ready and next |
| 2026-09-16 | REF-05 complete | Validated reductions; 36/36 propagation, 4/4 stability, refinement and enlarged checks pass v1 limits from a clean Release build; Debug/Release 12/12; C03 measured report exists, C04 begins; REF-06 ready; P1 open pending gate review |
| 2026-09-17 | REF-06 / P1 gate passed | Acceptance matrix complete; fresh Debug/Release 12/12 without warnings; full V01–V03 suites reproduced exactly from the clean Release build; supported limits recorded; C04 complete, C05 ready; MAT-01 ready; P2 open |
| 2026-09-18 | MAT-01 complete | P2 method note and V04–V07/S09–S14 specifications fixed with audited caps; new analytical audit registered; fresh Debug/Release 13/13 without warnings; D018; C05 in progress; MAT-02 ready; no P2 physics validated |

Add concise entries for work-item/cycle reviews, gate outcomes, material blockers,
and sequencing changes. Keep detailed measurements in validation reports and link them.
