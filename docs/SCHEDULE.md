# Work schedule

Recorded: 2026-09-05. Per the owner's instruction, work is ordered by dependencies
and completion evidence, with **no assumed dates, durations, or weekly capacity**.
Record dates identify history only; they are not delivery targets.

Current position (2026-09-22): C01 is complete following the
[P0 gate pass](validation/FND-05-foundation-gate.md). C02 is complete following
the [REF-03 structural/CFL review](validation/REF-03-reference-updates.md), with
REF-01 grid and REF-02 storage/indexing evidence retained. C03 is complete: the
[REF-05 measured physical report](validation/REF-05-reference-measurements.md)
reproduces all 36 propagation and four stability cases from a clean build. C04
is complete: the [REF-06 gate review](validation/REF-06-reference-propagation-gate.md)
passed P1 with an exact clean-build reproduction of the physical suites and
recorded the supported limits. C05 is in progress: MAT-01 (the P2 method note
and the V04–V07 specifications with fixed, audited tolerances) and MAT-02
(explicit PEC edge masks with passing V04 cavity evidence from a clean
Release build, re-confirmed on 2026-09-22 under specification revisions 1.2
and 1.3 of the V04-C driven acceptance) are complete and MAT-03 (dielectric and
conductive updates, V05/V06) is ready. The P2 and later numerical gates remain open. No
sequencing or duration assumptions changed.

## Sequencing policy

Each cycle is a bounded package of work and can span as many sessions as needed.
Start it when its dependencies are satisfied. Complete it when its evidence is
reviewed. A failed validation remains part of the active cycle.

Every numerical work package includes method design, implementation, validation,
investigation, and documentation. Do not budget away necessary validation. Record
measured computational runtime and memory as engineering evidence, without
turning those measurements into assumed calendar commitments.

## First six planning cycles

The following sequence breaks the early phases into reviewable packages. Cycle 1
has the most detail; refine subsequent packages as evidence becomes available.
Cycle completion does not replace the phase gate.

| Cycle | Start condition | Work focus | Reviewable output |
| --- | --- | --- | --- |
| C01 | Planning baseline recorded | P0: environment inventory, build/test setup, numerical conventions, propagation benchmark specification | Reproducible empty-core build/test; method and acceptance records ready for P1 |
| C02 | P0 gate passes | P1: core types, grid extents, staggered field storage, CFL policy | Reviewed storage/indexing design and passing structural/input checks |
| C03 | C02 structural checks pass | P1: reference updates, simple source, probes, minimal CLI | Reproducible propagation case and first measured numerical report |
| C04 | C03 produces reproducible measurements | P1: investigate dispersion/stability/error, convergence evidence, gate review | Passing P1 evidence package; unresolved failures keep this cycle active |
| C05 | P1 gate passes | P2: PEC/material equations, spectral and cavity specifications; initial implementation | Method notes and focused implementation with initial analytical comparisons |
| C06 | C05 specifications and initial comparisons reviewed | P2: complete conductivity, spectra, cavity/material regression evidence | Passing P2 evidence package and actionable P3 breakdown |

Split a package further if needed to keep it reviewable. Break down P3 and later
at the preceding phase review, recording dependencies, hardware needs, unresolved
risks, and completion evidence without assigning dates or durations.

## Cycle 1 sequence

| Order | Backlog item | Work | Completion evidence |
| --- | --- | --- | --- |
| 1 | FND-01 | Inspect installed compiler, CMake, test runner, Python, hardware, and source-control state | Environment record with exact versions, constraints, and selected toolchain |
| 2 | FND-02 | Set up minimal library, benchmark CLI target, tests, and presets | Clean configure/build/test command transcript or concise reproducible report |
| 3 | FND-03 | Define SI units, coordinates, Yee locations, time staggering, indexing, boundaries, and supported inputs | Numerical conventions/method note with equation references |
| 4 | FND-04 | Specify first independent benchmarks, measurement windows, and tolerances | Reviewed propagation/stability and structural test specifications |
| 5 | FND-05 | Complete Phase 0 review and select the first implementation item | Gate record with evidence links and updated backlog |

Do not install system tools or introduce dependencies merely because they appear
in the long-term vision. Inspect first, then choose the minimum needed.

## Recurring work routines

| When | Routine | Recorded output |
| --- | --- | --- |
| Start of each work session | Read backlog, check current files/changes, select one ready item, identify its validation expectation | Active item and session objective |
| During implementation | Compile after coherent changes; run relevant checks; investigate numerical failures immediately | Test evidence and any issue/decision record |
| End of each work session | Record changes, checks, failures, and exact next action | Backlog handoff note |
| At work-item completion or a material blocker | Review progress, blocked decisions, compute cost, and missing validation | Short entry in the backlog activity log |
| At cycle completion | Compare planned and completed evidence; review the next package and its dependencies | Updated schedule/backlog, with reasons for changes |
| At a phase gate | Review acceptance matrix, independent evidence, regressions, and limitations | Phase review using the workflow template |
| Before a release | Reproduce supported benchmarks from a clean build and inspect project compatibility where applicable | Versioned release evidence and limitations |

These routines are performed during active work sessions. Reminders, CI services,
and scheduled background runs can be configured later when explicitly requested
and when the relevant infrastructure exists.

## Replanning triggers

Replan when a gate fails, a new method is needed, priorities change, reference data
is blocked, or measured memory/runtime makes the proposed approach impractical.
Preserve the reason for the change in the backlog log. After a pause, resume from
the recorded handoff and verify that its prerequisites still hold.
