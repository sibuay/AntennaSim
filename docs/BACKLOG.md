# Backlog and project status

Last updated: 2026-09-25.

## Current position

- **Active phase:** P2 — Materials and closed domains (in progress; P0 and
  P1 gates passed; MAT-01, MAT-02 and MAT-03 complete).
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
  tolerances, backed by a passing standard-library audit registered in CTest;
  the explicit E-edge PEC mask (outer closure plus `pec_box`/`pec_shell`
  primitives) in the reference stepper with the S09 structural test, the
  `closed-v1` cavity/spectrum/pec suites and CLI, the independent fault-checked
  V04 analyzer and oracle, and the measured V04 report; the per-cell
  `MaterialMap`, deduplicated edge-coefficient table and lossy material kernel
  through which every stepper constructor now runs (vacuum bitwise P1), S10–S13,
  the `dielectric`/`interface`/`slab-cavity`/`lossy`/`dissipation` suites, the
  extended analyzer, self-test and material oracle, and the measured V05/V06
  report.
- **Validated numerical capability:** axis-aligned vacuum eigenwave propagation,
  signed impedance, second-order refinement, and closed-grid long-time stability
  within the FND-04 v1 envelope, as bounded in the
  [P1 gate record](validation/REF-06-reference-propagation-gate.md); PEC
  cavity resonance (exact eigenmodes at three resolutions with second-order
  refinement and the magnetic relation), driven-cavity mode identification and
  resolution, and interior shell enforcement within the MAT-01 V04 envelope,
  as measured in the [MAT-02 evidence](validation/MAT-02-pec-cavity.md) and
  re-confirmed on 2026-09-22 under specification revisions 1.2, 1.3 and 1.4 of
  the V04-C driven acceptance and probe-record completeness; homogeneous
  dielectric eigenwaves, the node-averaged planar dielectric interface (TE_1),
  the slab-loaded TE cavity, constant-conductivity decay and phase for
  `x = sigma dt/(2 eps) <= 0.045` and the closed-grid dissipation identity
  within the MAT-01 V05/V06 envelope, as measured in the
  [MAT-03 evidence](validation/MAT-03-dielectric-conductivity.md) (V05-B mode
  purity under specification revision 1.5). No spectral-production,
  open-boundary, oblique/curved-interface, dispersive/magnetic material,
  loss-tangent, port, or antenna capability is validated.
- **Active implementation item:** none.
- **Next ready item:** MAT-04 — production spectral processing validated on
  synthetic signals (V07) and against the independently analysed V04-B cavity
  spectrum, under the fixed MAT-01 specification.
- **Scheduling rule:** milestone-based, with no assumed dates or durations.
- **Blockers:** none for MAT-04. The compiler ran inside the ordinary session
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
| MAT-02 | P2 | Implement and validate explicit PEC boundaries/cavity | MAT-01 | Done | [Contract](methods/MAT-02-pec-mask-contract.md); [S09 209550 checks, V04-A/B/C measured pass, V01–V03 zero-tolerance reproduction, 15/15 CTests, 2026-09-22 addenda: V04-C driven acceptance strengthened to specification revisions 1.2-1.4 and re-analyzed, mode metadata sign corrected, probe records required complete](validation/MAT-02-pec-cavity.md); [compact metrics](validation/MAT-02-analysis-summary.json); D019, D020, D021, D022 |
| MAT-03 | P2 | Implement and validate dielectric and conductive updates | MAT-02 | Done | [Contract](methods/MAT-03-material-update-contract.md); [S10–S13 (9554/1034/19/611 checks), 2654 reduction/oracle checks, V05-A 18/18, V05-B 7/7 under specification revision 1.5 (version-1 purity failure retained), V05-C 18/18, V06-A 26/26, V06-B 2/2, V01–V03 and V04 reproduced at zero tolerance, 20/20 CTests, peak 1.267 GiB, 2026-09-25 review addenda](validation/MAT-03-dielectric-conductivity.md); [compact metrics](validation/MAT-03-analysis-summary.json); D023, D024, D025 |
| MAT-04 | P2 | Implement spectral processing and validate sampling/normalization | MAT-03 | Ready | V07 and cavity spectral evidence |
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

**2026-09-25 — MAT-03 second review (owner-requested, before the first commit)**

- Three reviewers (separate sessions of the same assistant, not an independent
  human) read the solver, benchmark library and analysis scripts. Two of them
  planted bugs in scratch copies to test the checks. No defect lets a recorded
  V05/V06 result pass wrongly. MAT-03 remains Done.
- Fresh `build/MAT-03-indep-review-{debug,release}` trees: 0 warnings, 20/20,
  source snapshot `1621d840…` (unchanged, because no solver or benchmark source
  changed).
- Corrected, in the analysis and tests only:
  - V06-B monotonicity now applies at every state, not only where `Q_n > 0`.
  - Case-level maxima and limits are NaN-safe.
  - The V06-A H floor is the V01 `0.5 A/eta`; the smallest measured value is
    `0.760`.
  - Faults were added for six enforced checks that nothing exercised; a
    mutation run of 11 mutants detected all 11.
  - S10 adds maps whose `sigma` does not follow `eps_r`, and a transcribed P1
    driven step compared bit for bit. S10 now has 9554 checks.
  - The golden generator no longer relies on `assert`.
  - The contract text now matches the code.
  - `reference.closed_analysis` now has 2654 checks. The retained run
    re-analyses to the tracked summary.
- Recorded, not changed: fixture checks that don't apply to a case are written
  as 0, and the divergence fixture check cannot fail on the version-1
  fixtures. See the
  [second addendum](validation/MAT-03-dielectric-conductivity.md#second-review-addendum-2026-09-25).
- Still local and uncommitted, awaiting the owner. Hosted CI is pending.
- **Next exact action:** unchanged, MAT-04.

**2026-09-25 — MAT-03 completion review (before the first commit)**

- Same-author review with three read-only code passes. The work was
  re-verified with fresh `build/MAT-03-audit-{debug,release}` trees: 0
  warnings, 20/20 CTests, and a source snapshot identical to the evidence build
  (`1621d840…`). The retained material run re-analyses to the tracked summary.
  No defect lets a V05/V06 limit pass wrongly. MAT-03 remains Done.
- Corrected:
  - The V05-B purity-floor scope. The floor covers about 42% of states and is
    up to about 450 times looser than version 1 between `2.2e-7` and `1e-4` of
    the peak. The specification, D025, the contract, the evidence and the
    failure-handling rule are updated. The pass stands.
  - A NaN that vanished from the purity maximum.
  - A defaulting `fixture_max_plateau_error` read in the audit.
  - The S10/S12 by-construction wording.
  - `reference.closed_analysis` goes from 2636 to 2641 checks. The affected
    CTests pass in both trees.
- Minor gaps recorded but not changed (smoke `--steps` limit, metadata `phi`,
  `omega_d`, V04 `diagnostic_bytes`, the duplicate map, the `dt` binding): see
  the [review addendum](validation/MAT-03-dielectric-conductivity.md#review-addendum-2026-09-25).
- Still local and uncommitted at the time of writing, awaiting the owner. The
  hosted CI result is pending.
- **Next exact action:** unchanged, MAT-04.

**2026-09-23 — MAT-03 dielectric and conductive updates complete**

- The [MAT-03 contract](methods/MAT-03-material-update-contract.md) was written
  before any code. It covers the API, errors, D023 storage, fixtures, metadata
  (material summary and coefficient provenance) and the analysis contract.
- Library:
  - `MaterialMap`: per-cell finite `eps_r >= 1` and `sigma >= 0`, exact shape,
    validated before storage; `uniform` validates before it allocates.
  - `EdgeCoefficients`: the four-cell relative mean times `epsilon0`, the
    MAT-01 `Ca`/`Cb`, a deduplicated table with a `uint32` index, and
    finite/`Cb > 0` checks before any field copy.
  - Every `ReferenceStepper` constructor runs the material kernel, with the
    vacuum table as the default. The source term is `E - Cb (amplitude J)`.
    The E screening is `div(eps_r,e E) = 0`. The vacuum CFL policy is
    unchanged. `-ffp-contract=off` holds on every target.
- Tests: S10–S13 as four CTests plus an exact-rational golden generator, for
  20 CTests. Suites: `dielectric`, `interface`, `slab-cavity`, `lossy`,
  `dissipation` and a nine-case smoke. The analyzer, self-test and oracle were
  extended: 726 checks become 2636, and the oracle reproduces every material
  smoke probe/`U`/`Q`/`D`/maximum within `1e-12`.
- Measured from fresh Release (`1621d840…`; fresh Debug likewise, 20/20, no
  warnings):
  - V05-A, V05-C and V06-A equal their exact discrete predictions at nine
    digits, with orders of about 2.0.
  - V05-B `abs(R)` errors equal the specification predictions, discrete
    `R`/`T` agree within `1.3e-5`, the `b` planes are bitwise equal and the
    orientations bitwise identical.
  - V06-B balances to `6.5e-16`.
  - V01–V03 (1211 values) and V04 (1021 values) reproduce at zero tolerance,
    and the smoke CSVs are byte-identical.
  - Peak memory is 1.267 GiB against 2 GiB.
  - See the [evidence](validation/MAT-03-dielectric-conductivity.md).
- One criterion failed as written: the V05-B version-1 purity rule
  (1.5e-9/5.1e-8/1.3e-7 against 1e-9). It failed only at carrier zero
  crossings, below `1e-6` of the peak, where the residual is roundoff
  (at most `1.7e-15` of the peak).
  - The owner delegated the fix on condition of no quality loss.
  - Revision 1.5 normalizes by `max(abs(a_n), 1e-4 peak)`. The limit is
    unchanged at states with `abs(a_n) >= 1e-4 peak` (about 58%). The rest
    are bounded by `1e-13` of the peak, which is looser than version 1 by up
    to about 450 times between `2.2e-7` and `1e-4` of the peak (scope
    corrected in the 2026-09-25 review). Faults at `2e-9 a_n`/`3e-13 peak`
    are detected.
  - It passes at `1.58e-11`. The failing analysis is retained.
  - D025, and a general rule in the validation plan's failure handling.
- Errata recorded before the runs: the V05-C spacing (audit `2`, not `1.5`),
  the V05-B line recorded every state, and the S10 clipping. The MAT-01 budget
  was corrected for coefficients and the map (D023). Decisions D023/D024/D025.
- Not done: hosted CI (GCC has not built this code), a second machine,
  sanitizers.
- MAT-03 is Done within its envelope. P2 remains open. Commits after `b98bc4c`,
  plus this item, are local and unpushed.
- **Next exact action:** MAT-04. Write the production spectral contract (the
  `exp(-i omega t) dt` direct sum at requested frequencies with E/H native
  times, rectangular/Hann windows, the S14 running DFT), implement it, validate
  on the V07 synthetic items, and reproduce the independent V04-B peaks within
  `1e-6` bin and `1e-9` height and the V04-B/V05-B direct sums within `1e-12`
  of the peak. Preserve all twenty CTests.

### Previous handoff (historical)

**2026-09-22 — MAT-02 completion re-review passed**

- No new actionable finding in the PEC implementation, acceptance checks or
  evidence. Earlier R1/R2/R3 fixes verified. See the third completion review in
  [the review record](validation/MAT-02-review-2026-09-22.md).
- Fresh Clang 20.1.7 Debug/Release builds have no warnings; approved CTest runs
  pass 15/15 each (137.78/135.79 s), including 209550 PEC and 726
  reduction/oracle checks. Sandbox compiler/startup failures and successful
  final runs are retained in `build/MAT-02-final-review-*` logs.
- Retained V04 re-analysis reproduces the tracked summary byte for byte.
  A fresh deletion of both driven cases' secondary probes is rejected by the
  audit and reduction. Retained V01–V03 re-analysis passes and reproduces all
  1,211 compared values; the comparator flags only the documented fingerprint
  change. All 59 manifest entries matched before documentation updates.
- Changed only the review record, this handoff and their manifest hashes.
  Full physical solver runs, hosted CI, sanitizers and another machine were
  not repeated. No new numerical or architecture decision was needed.
- MAT-02 remains Done within its stated PEC-cavity scope. P2 remains open.
  Next exact action: MAT-03; no schedule or implementation scope change.

### Previous handoff (historical)

**2026-09-22 — MAT-02 review finding R3 resolved (revision 1.4)**

- R3 is fixed. The structural audit compared probe *rows per state*, which a
  probe absent from every state satisfies, and `source_probe_checks` read the
  prescribed samples through a defaulting lookup, so the absent samples were
  read as the expected zeros. Reproduced independently before fixing: deleting
  all 4,097 second-probe samples from copies of both driven cases (8,194 rows
  to 4,097) left the audit and the full PEC analysis passing with empty failure
  lists.
- MAT-01 carries specification revision 1.4 in two layers. The audit compares
  the recorded `(component, index)` key set — identical at every state and, for
  a source case, exactly the `Ez` edges the artifact declares — through the
  pure `probe_coverage` rule. Because that compares an artifact with itself,
  the V04-C reduction uses the fixture instead: the specification audit derives
  the C2/C3 probe pairs `(10,12,16)`/`(8,10,12)` and `(1,1,1)`/`(9,11,13)`,
  confirms both interior edges are strictly inside the shell and unmasked, and
  the reduction requires the declared and recorded sets to equal them and every
  sample it reads to be present. D022.
- `reference.closed_analysis` grows from 709 to 726 checks, the last two
  covering a short declared probe set and a duplicated sample standing in for a
  missing one. The review's own
  `recheck-probe-completeness.py` now stops at the audit, and the reduction
  reports 4097 of 8194 prescribed samples with both absent states named. That
  re-run regenerated `signoff-missing-probe/result.json` with the post-fix
  result; the pre-fix `pass` survives in the review report and in
  `review-missing-probe/`.
- Re-analysis of the retained raw run passes all four suites and reproduces the
  tracked summary byte for byte. Fresh Debug and Release
  (`build/MAT-02-r14-{debug,release}`) configure, build without warnings and
  pass 15/15 CTests; no C++ or CMake input changed, so the fingerprint stays
  `706af2e4…`.
- Not repeated: a full physical re-run of V01–V04, hosted CI, and validation on
  a second machine. MAT-02 stays Done; P2 remains open. Next exact action:
  MAT-03.

**2026-09-22 — MAT-02 second completion review: R3 open**

- Reviewed `cc74055` plus the existing revision-1.3 changes; R1/R2 are fixed.
  The [review report](validation/MAT-02-review-2026-09-22.md) records one new
  acceptance defect: deleting all secondary-probe samples from C2/C3 still
  passes the artifact audit and the complete PEC reduction, because absent
  required zero-valued samples default to zero and the audit checks only a
  constant row count. No incorrect solver field was found.
- Fresh Debug and Release each passed 15/15 CTests; re-analysis of the original V04 evidence
  reproduces the tracked summary exactly; all 59 manifest entries matched at
  review start. The report contains the reproduction, logs and checks not
  repeated. Existing implementation changes and original evidence are intact.
- The historical Done decision above is preserved; unqualified sign-off now
  awaits R3. Next exact action: require the complete prescribed C2/C3 probe
  set at every state and add missing-record fault coverage before MAT-03.
  P2 remains open; no phase or implementation item was advanced.

**2026-09-22 — MAT-02 review follow-up resolved (revision 1.3 and the metadata sign)**

- Both findings of the [review report](validation/MAT-02-review-2026-09-22.md)
  are fixed. R1: the V04-C first-deposit check compared the largest of the
  three electric region maxima with the closed-form deposit, so a deposit in
  `Ex` or `Ey` passed the requirement for the fixed `J_z` source, and no
  requirement referred to the driven edge. R2: every mode case emitted an
  `initialization` description with the opposite initial-H sign (the amplitude
  `H_s` in place of its value at `-dt/2`); the initializer, the specification
  and the independent oracle were always positive, so no computed field was
  affected.
- MAT-01 carries specification revision 1.3: the `Ez` region maximum at state 1
  equals the closed-form deposit with every other component zero in the driven
  region and over the whole domain, and the native `Ez` sample of the
  prescribed source edge equals the signed `-(dt/eps0) J0 g_0` =
  -7.2292736715001706e-08 V/m while the other prescribed probes stay zero at
  states 0 and 1. The structural audit now also pins the emitted
  `initialization` description, admitting the historical mode string only with
  the source snapshot `f02fbe47…` that emitted it, so retained raw evidence
  stays auditable without being rewritten. D021.
- `benchmarks/closed.cpp` emits the corrected description; the source
  fingerprint moves from `f02fbe47…` to `706af2e4…`. No solver, fixture,
  geometry or limit changed. `reference.closed_analysis` grows from 684 to 709
  checks, including the exact mutation the review used: an `Ex` deposit with
  the `Ez` source record zeroed now fails three requirements in both driven
  cases, where before it passed the audit and the full reduction.
- Re-analyzed the retained `build/evidence/MAT-02/run1` without re-running the
  solver: all four suites pass, every previously tracked value is bit-identical,
  and the summary gains only the two source-probe metrics per driven case and
  the rule version. Fresh Debug and Release (`build/MAT-02-r13-{debug,release}`)
  configure, build without warnings and pass 15/15 CTests.
- Records updated: MAT-01 specification (revision 1.3), MAT-02 contract and
  evidence addendum, the review report's resolution section, VALIDATION,
  DECISIONS (D021), README, SCHEDULE and the source manifest, which gains the
  review report and now has 59 entries, all verified.
- Not repeated: a full physical re-run of V01–V04 under the new fingerprint,
  hosted CI, and validation on a second machine. MAT-02 stays Done; P2 remains
  open. Next exact action: MAT-03.

**2026-09-22 — MAT-02 completion review follow-up**

- Reviewed `cc74055` and the existing uncommitted revision-1.2 correction;
  preserved those changes and the original evidence. The
  [review report](validation/MAT-02-review-2026-09-22.md) records two open
  findings: the C2/C3 first-deposit check accepts the wrong electric component,
  and mode metadata describes the initial H field with the opposite sign.
- Fresh Debug and Release each pass all 15 CTests; re-analysis reproduces the tracked V04
  summary exactly and all 58 source-manifest entries matched at review start.
  Build-environment failures, Debug results, and checks not repeated are
  recorded in the report. No solver or analyzer fix was made during review.
- The historical MAT-02 completion remains recorded above; an unqualified
  sign-off awaits R1/R2. Next exact action: resolve those findings and refresh
  affected validation/evidence before starting MAT-03. P2 remains open.

**2026-09-22 — MAT-02 review: V04-C driven acceptance strengthened (revision 1.2)**

- Reviewed the closed MAT-02 item against its evidence. Confirmed the S09
  count (209550), the reduction/oracle test, the 58-entry source manifest, the
  tracked V04-A/B/C results and provenance, and a clean worktree. Found one
  real defect: the version-1 V04-C acceptance for the driven cases
  `pec-c2-inside` and `pec-c3-outside` required only that the driven side stay
  *finite*, which an identically-zero region satisfies. A synthetic C2/C3
  record with every region maximum, `U` and `Q` set to zero passed the
  analyzer with an empty failure list. No measured result was wrong; the
  criterion could not have failed on a dead run.
- MAT-01 carries specification revision 1.2 of the C2/C3 acceptance: the
  largest electric region maximum at state 1 equals the closed-form deposit
  `(dt/eps0) abs(g_0)` = 7.2292736715001706e-08 V/m within 1e-12 relative with
  every other component of that region exactly zero; the driven peak reaches
  at least 0.1 of the largest single-step deposit (0.17344677198144254 V/m);
  `Q` is zero at state 0, positive after the 53-sample pulse and constant to
  1e-12 relative thereafter; `dt` matches the v1 cavity definition. The
  predictions come from `pulse_drive` in the specification audit and use no
  solver output. The revision only adds requirements.
- `scripts/analyze_closed_benchmarks.py` enforces them (new
  `excitation_checks`, new metrics and report table, thresholds recorded in
  the summary); `scripts/check_closed_analysis.py` gained a `driven_rows`
  fixture and eight fault injections per driven case, including the
  identically-zero record, which now fails three separate requirements.
  `reference.closed_analysis` grows from 665 to 684 checks.
- Re-analyzed the retained `build/evidence/MAT-02/run1` without re-running the
  solver (`ANTENNASIM_SOURCE_SNAPSHOT` covers only C++/CMake inputs, none of
  which changed; both fresh builds reproduce `f02fbe47…`). All four suites
  pass: deposit error 6.77e-15 against 1e-12, driven peaks 1.033x and 1.116x
  the largest deposit against a floor of 0.1, invariant drift 4.11e-16 and
  3.74e-16 against 1e-12. Every previously recorded value in the tracked
  summary is unchanged; the diff is purely additive.
- Checks: fresh `build/MAT-02-r12-release` and `build/MAT-02-r12-debug`
  configured from absent directories, built without warnings, 15/15 CTests
  (107.26 s and 118.55 s), `reference.pec` 209550 and
  `reference.closed_analysis` 684 in both. Not re-run: the manual V04/V01–V03
  physical suites, which need no re-run because no solver input changed.
- Records updated: MAT-01 specification (revision 1.2), MAT-02 evidence
  (addendum, V04-C excitation table, regression matrix), tracked summary,
  validation plan, backlog, schedule, decision log (D020), source manifest.
- Next exact action: unchanged — MAT-03, as in the previous handoff.

### Previous handoff (historical)

**2026-09-18 — MAT-02 explicit PEC edges and V04 cavity evidence complete**

- Implemented `PecMask` (`include/antennasim/pec.hpp`, `src/pec.cpp`): one byte
  per E sample, `pec_box`/`pec_shell` primitives by exact index arithmetic,
  the outer closure as the always-present whole-domain shell, `masked`/
  `enclosed` queries and per-component counts. `ReferenceStepper` gains a
  mask constructor (the two-argument form delegates with the closure-only
  mask); initial screening rejects nonzero masked E and enclosed H samples and
  skips divergence nodes with a masked neighbour; the E loop skips masked
  samples with unchanged ranges; a current on a masked edge is a terminal
  step error. The closure-only path is bitwise identical to P1: kernel and
  stepper checks in S09, byte-identical reference-v1 smoke CSVs, and the full
  V01–V03 suites reproduced against the tracked REF-05 summary at zero
  tolerance from the clean build.
- Added `benchmarks/common.hpp` (helpers moved verbatim out of `reference.cpp`),
  `benchmarks/closed.{hpp,cpp}` and `--benchmark closed-v1` with the `cavity`
  (30), `cavity-spectrum` (1), `pec` (5) and `smoke` (4) suites: exact discrete
  standing modes with the `C*C E=|K|^2 E` fixture identity, the antisymmetric
  pulse, native lines, per-state `U/Q`, component and region maxima, schema
  `closed-v1-raw-1` with primitives and masked-edge counts.
- Added `tests/pec_check.cpp` (CTest `reference.pec`, 209550 S09 checks),
  `scripts/analyze_closed_benchmarks.py` (imports the MAT-01 audit's
  closed-form predictions; structural audit, V04-A/B/C reductions, refinement,
  `metrics.json`/traces/report) and `scripts/check_closed_analysis.py`
  (CTest `reference.closed_analysis`, 665 checks: synthetic fault injection
  for every V04 observable and a pure-Python oracle with an independently
  enumerated mask reproducing the four-step smoke suite within 1e-12, the
  shell case bitwise equal to the open cavity). The runner gains
  `--benchmark closed-v1`; CI retains `mat02-audits`.
- Measured from a fresh `build/MAT-02-release` (15/15 CTests, no warnings;
  fresh Debug likewise): V04-A 30/30 with continuum errors equal to the exact
  discrete predictions at nine digits, orders 2.0003–2.0159, implementation
  errors <= 1.1e-12; V04-B all eight lines within 0.0004 bin and 0.0024
  relative height on both records, no spurious peak, post-pulse `Q` constant
  to 6.2e-16; V04-C shell modes bitwise equal to the open cavity (all samples),
  silent regions exactly zero for the shifted modes and both pulses. See the
  [evidence](validation/MAT-02-pec-cavity.md).
- One criterion failed as written: the V04-B growth rule had no absolute floor
  and `Hz`, analytically zero for the z-directed source, grew from 5.4e-19 to
  1.4e-18 A/m by roundoff (other H components 3e-4 A/m). The failing analysis
  is retained; the specification carries revision 1.1 (floor `1e-9` of the
  family maximum, null components must stay below it) with the reason; no cap,
  fixture or solver changed. Two test-construction defects (S09 pulse pairing,
  two synthetic fault magnitudes) and one smoke-audit label check were fixed
  before the physical runs; none was a solver finding.
- Records updated: backlog, project plan, schedule, validation plan, README,
  MAT-01 specification (revision 1.1), decision log (D019), CI workflow.
- Next exact action: MAT-03. Implement the per-cell `eps_r`/`sigma` material
  map with four-cell edge averaging and the time-centred coefficients of the
  MAT-01 note (vacuum bitwise, S10–S13), the `dielectric`, `interface`,
  `slab-cavity`, `lossy` and `dissipation` suites and their exact fixtures
  (lossy eigenwave initialized from `z`), extend the analyzer/oracle with the
  V05/V06 reductions and fault coverage, then run V05/V06 and re-run V01–V04
  from a clean Release build (V06-C at zero tolerance). Preserve all fifteen
  CTests.

### Previous handoff (historical)

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
- A post-audit read-through found two specification contradictions, both
  corrected and now covered by the audit: V04-C had placed a cavity mode and a
  source inside a solid PEC box (fixed by adding the hollow `pec_shell`
  primitive, of which the outer closure is the whole-domain instance, and
  enumerating the 3,008-edge V04-C mask), and V06-A had initialized the
  lossless eigenwave while requiring the lossy growth factor at every step
  (fixed by initializing the exact lossy mode; the audit's modal recursion
  shows the lossless start deviates by 4.6e-2 at the first step). No cap or
  prediction changed.
- Fresh `build/MAT-01-release` and `build/MAT-01-debug` trees configured, built
  without warnings, and pass 13/13 CTests before and after the corrections; see
  the [review](validation/MAT-01-review.md). Records updated: backlog, project
  plan, schedule, validation plan, README, decision log (D018).
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
| 2026-09-18 | MAT-01 review correction | Two fixture contradictions (V04-C solid box, V06-A lossless start) found in review and fixed; `pec_shell` primitive added; audit extended to enumerate the V04-C mask and the lossy modal recursion; 13/13 CTests still pass; MAT-01 remains Done, MAT-02 ready |
| 2026-09-18 | MAT-02 complete | Explicit E-edge PEC mask, S09, closed-v1 suites and independent analyzer; V04-A/B/C pass from a clean Release build with V01–V03 reproduced at zero tolerance; fresh Debug/Release 15/15 without warnings; V04-B growth rule revised to 1.1 with the failing v1 analysis retained; D019; MAT-03 ready; P2 open |
| 2026-09-22 | MAT-02 review correction | Review found the V04-C driven acceptance could not fail on a dead run (finiteness only); specification revision 1.2 adds the closed-form deposit, the excitation floor and the post-pulse invariant; analyzer and reduction test enforce them (665 to 684 checks); retained runs re-analyzed without a solver re-run and pass with 10x–2400x margins; fresh Debug/Release 15/15 without warnings; D020; MAT-02 remains Done; MAT-03 still the next action |
| 2026-09-22 | MAT-02 review follow-up resolved | Review findings R1/R2 fixed: specification revision 1.3 names the driven component and checks the prescribed source edge's signed native sample, and the audit pins the emitted initial-condition description after the mode metadata sign was corrected in `benchmarks/closed.cpp` (fingerprint `f02fbe47…` to `706af2e4…`, no computed field affected); 684 to 709 checks including the mutation that previously passed; retained runs re-analyzed without a solver re-run, all tracked values bit-identical; fresh Debug/Release 15/15 without warnings; D021; MAT-02 remains Done; MAT-03 still the next action |
| 2026-09-22 | MAT-02 review: probe completeness | Second completion review found a prescribed probe absent from every state passing both the audit (uniform row count) and the reduction (defaulting lookup); specification revision 1.4 requires the recorded key set to match the declaration at every state and pins the C2/C3 sets to the fixture-derived pairs, with every read sample required present; 709 to 726 checks including the deletion that previously passed; retained runs re-analyzed without a solver re-run, summary reproduced byte for byte; fresh Debug/Release 15/15 without warnings; D022; MAT-02 remains Done; MAT-03 still the next action |
| 2026-09-23 | MAT-03 complete | Material map, D023 coefficient table and lossy kernel behind every stepper (vacuum bitwise); S10–S13 and golden states; V05-A/C and V06-A/B pass at their exact discrete predictions; V05-B passes under specification revision 1.5 after the version-1 purity rule failed on roundoff at carrier zero crossings (failure retained, D025, general failure-handling rule); V01–V04 reproduced at zero tolerance; fresh Debug/Release 20/20 without warnings; peak 1.267 GiB; D023–D025; MAT-04 ready; P2 open |
| 2026-09-25 | MAT-03 completion review | Fresh Debug/Release 20/20 without warnings from the evidence source snapshot; retained material run re-analysed to the tracked summary; V05-B purity-floor scope corrected in the specification, D025 and the records (about 42% of states under the floor; the pass stands); a NaN hidden by the purity maximum and a defaulting plateau-report read fixed with new faults (2636 to 2641 checks); minor gaps recorded; MAT-03 remains Done; MAT-04 next |
| 2026-09-25 | MAT-03 second review | Owner-requested review with planted-bug checks; fresh Debug/Release 20/20 without warnings, snapshot unchanged; V06-B monotonicity applied at every state, NaN-safe maxima/limits, V06-A H floor 0.5 A/eta, faults for six unexercised checks (11/11 mutants detected), S10 sigma-independent maps and transcribed P1 driven step (3022 to 9554 checks), 2641 to 2654 reduction checks; retained run re-analyses to the tracked summary; no recorded result changes; MAT-03 remains Done; MAT-04 next |

Add concise entries for work-item/cycle reviews, gate outcomes, material blockers,
and sequencing changes. Keep detailed measurements in validation reports and link them.
