# Backlog and project status

Last updated: 2026-09-07.

## Current position

- **Active phase:** P1 — Reference propagation (in progress; P0 gate passed).
- **Completed capability:** planning records, a verified C++20/CMake build scaffold,
  reviewed reference Yee-grid conventions, fixed initial benchmark specifications,
  structurally checked core grid metadata/input/allocation validation, and six
  staggered field arrays with checked indexing, native positions, and wall classification;
  strict CFL selection and source-free reference E/H stepping with structural checks.
- **Validated numerical capability:** equation-level/structural checks only; no physical benchmark passed.
- **Active implementation item:** none.
- **Next ready item:** REF-04 — minimal sources, probes, run configuration, and CLI output.
- **Scheduling rule:** milestone-based, with no assumed dates or durations.
- **Blockers:** none for REF-04. The local compiler requires approved execution
  outside the sandbox; Debug/Release checks pass in that environment.

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
| REF-04 | P1 | Add minimal source, probes, run configuration, and CLI output | REF-03 | Ready | Deterministic end-to-end benchmark command |
| REF-05 | P1 | Measure propagation, impedance, stability, and refinement behavior | REF-04 | Planned | V01–V03 evidence; applicable structural regressions |
| REF-06 | P1 | Review reference-propagation gate | REF-05 | Planned | P1 gate record and supported limits |
| MAT-01 | P2 | Specify PEC, dielectric, conductivity, and spectral conventions | REF-06 | Planned | Method notes and V04–V07 specifications |
| MAT-02 | P2 | Implement and validate explicit PEC boundaries/cavity | MAT-01 | Planned | V04 evidence and existing regressions |
| MAT-03 | P2 | Implement and validate dielectric and conductive updates | MAT-02 | Planned | V05–V06 evidence and existing regressions |
| MAT-04 | P2 | Implement spectral processing and validate sampling/normalization | MAT-03 | Planned | V07 and cavity spectral evidence |
| MAT-05 | P2 | Review materials/closed-domain gate | MAT-04 | Planned | P2 gate record and P3 breakdown |

MAT-02 can use an independently checked analysis script for initial cavity
evidence; MAT-04 subsequently validates the production spectral path against it.

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

Add concise entries for work-item/cycle reviews, gate outcomes, material blockers,
and sequencing changes. Keep detailed measurements in validation reports and link them.
