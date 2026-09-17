# REF-06 — Reference-propagation gate review (Phase 1)

Date: 2026-09-17. Decision: **PASS for P1 within the declared envelope; MAT-01
ready.** Phase 2 implementation and its numerical gate remain pending.

Reviewer: the same implementation collaborator responsible for REF-01 through
REF-05 and their records. No independent human or second-agent review occurred.
The independent analytical comparators, the separately transcribed oracle, and
the fault-injected analyzer are independent of the solver; they do not make the
reviewer independent. This limitation is carried into the P2 breakdown below.

Code revision: `d736c92` (`Complete REF-05 physical validation`, `main`). Before
any status record was edited, all 35 entries of the
[REF-05 source manifest](REF-05-source-sha256.txt) matched the working tree, and
the fresh Release configuration below reproduced the REF-05 source-content
fingerprint `f9ddf4f296e7858c33974167579f8423db73d51e36601589e2f58f26bc222f5c`
(SHA-256 of the LF-normalized `source-snapshot.txt`). No C++ source, build
configuration, test, fixture, tolerance, method note, or analyzer changed for
this gate. The only new code is `scripts/compare_reference_analysis.py`, a
standard-library reader that compares two analyzer summaries; it evaluates no
physics. The [REF-06 manifest](REF-06-source-sha256.txt) identifies the reviewed
inputs and the final records; like the earlier manifests it hashes the
working-tree bytes (`sha256sum -c` on this Windows checkout), not the
LF-normalized text used for the CMake fingerprint.

## Gate acceptance matrix

The required criteria are the Phase 1 deliverables and exit conditions in the
[project plan](../PROJECT_PLAN.md) ("Free-space propagation and stability checks
meet recorded criteria; component/indexing and invalid-input tests pass;
reproduce a run from a clean build"), the plan's requirement that P1 document
its provisional outer boundary and isolate measurements from boundary returns,
and the C04 cycle output in the [schedule](../SCHEDULE.md) (dispersion,
stability, error and convergence evidence). The recorded criteria are the
unchanged [FND-04 version-1 limits](FND-04-reference-benchmarks.md).

| Required criterion | Reviewed or measured result | Evidence | Verdict |
| --- | --- | --- | --- |
| Deliverable: grid and staggered field storage | Validated integral counts, unequal spacings, six exact Yee extents, checked allocation arithmetic and limits (136 checks); six binary64 arrays with native positions, contiguous checked indexing, wall classification and 1976 test-harness stencil reads (23838 checks); S01/S02 storage subsets | [REF-01](REF-01-core-grid.md), [REF-02](REF-02-field-storage.md), D012/D013 | Pass |
| Deliverable: CFL handling | Strict `0<q<1` and `dt<dt_max` with rejection of equality/next-above, default 0.99 and 0.5 within 5e-15 of the independent unequal-spacing formula on cubic and unequal grids; coefficient/half-step/timestamp representability checks | [REF-03](REF-03-reference-updates.md), FND-03 stability section | Pass |
| Deliverable: reference update loop | All-H-then-E vacuum updates on exact extents, zero tangential E walls, terminal nonfinite failure with state/component/index; S03 twelve signed derivative terms (error 0), S04 zero-curl/div-curl (0), S05 weighted adjoint residual 7.66e-17, exact-rational two-step golden comparison 1.33e-15 on 513 samples (27013 checks) | [REF-03](REF-03-reference-updates.md), [contract](../methods/REF-03-reference-update-contract.md), D014 | Pass |
| Deliverable: simple excitation | Validated sparse impressed E-edge current with half-time amplitude; S06 coupling `E=-dt J/epsilon0`, `H=0` and discrete continuity within 1e-13 for all three components and both signs; the V03 solenoidal eight-step pulse drives two stability cases | [REF-04](REF-04-reference-runs.md), [contract](../methods/REF-04-run-contract.md), D015 | Pass (impressed current only; no port) |
| Deliverable: probe output | Native probes with component, integer index, SI coordinate, state, actual E/H time (H from -dt/2) and signed value; S07 label/time/coordinate checks within the 5e-15 budget; no interpolation | [REF-04](REF-04-reference-runs.md) | Pass |
| Deliverable: minimal CLI | `--benchmark reference-v1 --suite propagation/stability/smoke --output DIR` with strict step parsing, metadata JSON, streamed CSV, exclusive completion marker, refusal of existing directories, bad-argument and incomplete-artifact rejection; help/version/unsupported-request contract | [REF-04](REF-04-reference-runs.md), `foundation.cli_*`, `reference.run_artifacts` | Pass |
| Exit: free-space propagation meets recorded criteria | 36/36 V01 cases pass: continuum phase-speed errors 0.00120829246 / 0.000301257334 / 0.0000752634590 against caps 0.0015 / 0.000375 / 0.00009375; discrete, amplitude, residual, inactive-line errors ≤ 6.4e-14 against 1e-9; q=0.5 and cubic sensitivity 0.00243512004 / 0.00192599561 against 0.003; six refinement orders 2.00390143 / 2.00097486 inside [1.8, 2.2]; six enlarged-domain comparisons 2.82e-14 against 1e-10 with the dependency guard passed | [REF-05](REF-05-reference-measurements.md), [metrics](REF-05-analysis-summary.json) | Pass |
| Exit: signed impedance meets recorded criteria | 36/36 V02 cases: complex relative error ≤ 1.65e-15 against 1e-8, sign `s` correct for all six orderings, imaginary part ≤ 2.1e-13 ohm | [REF-05](REF-05-reference-measurements.md) | Pass |
| Exit: stability meets recorded criteria | 4/4 V03 cases over 20,000 source-free steps at q=0.5 and 0.99, initial-field and driven: invariant drift ≤ 1.29e-15 against 1e-8, no `(1±q)` bound violation, no nonfinite sample, no secular growth across 20 blocks | [REF-05](REF-05-reference-measurements.md) | Pass |
| Exit: component/indexing tests pass | `reference.grid`, `reference.fields`, `reference.vacuum`, `reference.run` pass in fresh Debug and Release trees at this gate | Clean-build matrix below | Pass |
| Exit: invalid-input tests pass | V03 CFL/spacing/count/step/probe/source/wall/nonfinite/overflow matrix in the four structural tests; malformed CLI arguments, overwrite refusal and incomplete artifacts in `reference.run_artifacts` | [REF-01](REF-01-core-grid.md)–[REF-04](REF-04-reference-runs.md), clean-build matrix below | Pass |
| Exit: reproduce a run from a clean build | Fresh Release tree; full 36-case propagation and 4-case stability suites re-run and re-analyzed; all 1211 compared values of the tracked REF-05 summary reproduced with zero difference | Reproduction section below | Pass |
| Plan: provisional boundary documented; measurements isolated from boundary returns | `zero_tangential_e` reflecting closure specified with its PEC-validation deferral; V01/V02 use the `p-0.5 > 2N+6` all-face dependency guard enforced before allocation, and the enlarged-domain comparison confirms it on every ordering | [FND-03](../methods/FND-03-yee-conventions.md), [FND-04](FND-04-reference-benchmarks.md), [REF-05](REF-05-reference-measurements.md) | Pass |
| C04: dispersion, error and convergence investigated | Measured continuum error equals the analytical Yee dispersion prediction to nine digits at three resolutions and two sensitivity variants; observed orders match the exact predictions 2.003901430 / 2.000974863; error mechanisms identified as spatial dispersion, not implementation error | [REF-05](REF-05-reference-measurements.md), [FND-04 review](FND-04-review.md) | Pass |
| Reductions validated before physical acceptance | 97 synthetic pass/fault-detection checks, pure-Python oracle agreement within 1e-12 for `U`, `Q`, maxima and probes on both q=0.99 smoke stability cases (initial-field and driven), resource/provenance failure retention; registered as `reference.analysis_reductions` | [REF-05 contract](../methods/REF-05-measurement-contract.md), D017 | Pass |
| Single source snapshot for all P1 evidence | Manifest and fingerprint match; hosted Ubuntu/GCC Debug and Release CTest runs passed for the preceding commits `3043b39` and `b342821` (owner report); `b98bc4c` is on `origin/main` without a result recorded here | [MNT-01](MNT-01-repository-hardening.md), identity above | Pass; see limits for the unpushed REF-05 commit |
| No open decision blocks P2 | O005 (license) is due before distribution; O006 before P4/P6; O007 (absorbing boundary) before P3; O008 by P6; O009 P10/P11; O010 P8/P9 | [Decision log](../DECISIONS.md) | Pass |

Every required criterion has passing evidence with linked measurements; none is
satisfied by code presence or elapsed time. The gate therefore passes **for the
declared envelope only**, which is stated next.

## Supported limits after Phase 1

Validated capability (V01–V03 version 1, measured 2026-09-16 and reproduced
2026-09-17):

- Uniform Cartesian three-dimensional Yee grid, homogeneous lossless vacuum,
  independent per-axis spacings, binary64 scalar CPU reference kernel with
  checked access; H at half times, E at integer times; strict CFL fraction
  below 1.
- Closed `zero_tangential_e` reflecting box. It makes the stencil well-defined
  and is stable at the declared settings; **physical PEC/cavity behavior is not
  validated** (MAT-02/V04).
- Axis-aligned single-frequency discrete eigenwave propagation for all six
  axis/polarization orderings at lambda/24, lambda/48 and lambda/96 with
  spacing ratios (1, 1.5, 2), plus q=0.5 and cubic-spacing variants: continuum
  phase-speed error within the h^2 caps, second-order refinement, amplitude and
  isolation within 1e-9, signed vacuum impedance within 1e-8 at native events.
- Long-time closed-grid stability on the (12,14,16) grid with spacings
  (0.01, 0.015, 0.02) m for 20,000 source-free steps at q=0.5 and q=0.99, with
  an initial solenoidal field or an eight-step solenoidal impressed current.
- Deterministic raw artifacts (byte-identical repeated CSV output in REF-04;
  exact metric reproduction from a separate clean build here).

Not validated, and not to be presented as validated:

- Oblique or off-axis propagation, broadband or pulsed launches, and the
  accuracy of waves generated by a source rather than by an initial eigenwave;
  the fixture is the discrete eigenwave, so V01 measures dispersion of the
  scheme, not general excitation accuracy.
- PEC resonances, interior conductors, dielectric or conductive materials,
  interfaces, loss, dispersion models, absorbing or periodic boundaries, ports,
  impedance/S-parameters of any feed, near-to-far-field transformation,
  radiation metrics, or any antenna result.
- Stability for other grids, materials, boundaries, durations beyond 20,000
  steps, arbitrary forcing, or Courant fractions nearer 1 than 0.99 (a single
  finite step at q=1-2^-20 is a smoke check only).
- Performance: the checked-access reference kernel took 606 s for the 36
  propagation cases with a 1.03 GB peak working set (REF-05); no throughput,
  threading, or GPU claim exists.
- Platforms: physical suites ran only on Windows x64 with LLVM-MinGW Clang
  20.1.7. Hosted Ubuntu/GCC runs execute the twelve-test CTest suite, which
  includes smoke-length reductions and the oracle comparison, not the full
  physical suites.
- Review: same-author implementation, analysis, and review throughout P1.

## Clean-build and regression matrix

Environment: Windows 10 x64 (build 19045), AMD Ryzen 5 3600, project-local
LLVM-MinGW 20250613 UCRT / Clang 20.1.7, CMake/CTest 3.31.10, Ninja
1.11.1.git.kitware.jobserver-1. CTest discovered Python 3.10.2 for the five
Python-driven tests; the manual runner/analyzer/comparison used Anaconda Python
3.9.7 with psutil 5.8.0. The compiler, CTest, and the suites ran inside the
ordinary session sandbox without approval, as on 2026-09-16. Verbose build logs
show `-std=c++20`, `-Wall -Wextra -Wpedantic -Wconversion -Wshadow`,
`-fno-fast-math` and `-ffp-contract=off` on every compiled target, `-O3` for
Release, and no compiler warnings.

| Run | Configure | Build | CTest | Measured CTest time |
| --- | --- | --- | --- | --- |
| Fresh `build/REF-06-release` | Pass | Pass, no warnings | 12/12 pass | 14.37 s |
| Fresh `build/REF-06-debug` | Pass | Pass, no warnings | 12/12 pass | 28.04 s |

The twelve tests are `foundation.toolchain`, `foundation.cli_help`,
`foundation.cli_contract`, `reference.grid`, `reference.fields`,
`reference.vacuum`, `reference.run`, `reference.yee_conventions`,
`reference.benchmark_specification`, `reference.golden_steps`,
`reference.run_artifacts`, and `reference.analysis_reductions`. Both build
directories were absent before configuration. Commands from the project root,
with `release` and `debug` in turn (the Release tree was built first so that the
physical suites ran without a concurrent build):

```bash
B=build/REF-06-release   # then build/REF-06-debug
test ! -e "$B"
./.tools/cmake/cmake/data/bin/cmake.exe --preset windows-local-release -B "$B"
./.tools/cmake/cmake/data/bin/cmake.exe --build "$B" --verbose
./.tools/cmake/cmake/data/bin/ctest.exe --preset windows-local-release --test-dir "$B"
```

Retained ignored local logs: `build/REF-06-{release,debug}-{configure,build,test}.log`,
`build/REF-06-run1.log`, `build/REF-06-analysis.log`, and
`build/REF-06-compare.log`. As documented at FND-05, the preset/`--test-dir`
combination writes `LastTest.log` under the preset's original build directory;
the captured `-test.log` files are the gate's test transcripts.

## Reproduction of the physical suites from the clean build

The full propagation and stability suites were re-run serially from the fresh
Release executable and re-analyzed into fresh directories, then compared with
the tracked REF-05 summary:

```bash
python scripts/run_reference_benchmarks.py --app build/REF-06-release/antennasim.exe --output build/evidence/REF-06/run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_reference_benchmarks.py --input build/evidence/REF-06/run1 --output build/evidence/REF-06/analysis
python scripts/compare_reference_analysis.py --reference docs/validation/REF-05-analysis-summary.json --candidate build/evidence/REF-06/analysis/metrics.json
```

| Check | Result |
| --- | --- |
| Runner status (propagation / stability) | 0 / 0; every case wrote its `COMPLETE.json` |
| Analyzer status | `pass` for the propagation, stability and resources suites; no provenance failure; single source snapshot `f9ddf4f2…` |
| Comparison with the tracked REF-05 summary | 40 cases, 1211 compared leaves (823 floating-point), maximum absolute difference 0; no mismatch at zero tolerance |
| Propagation elapsed / peak working set | 596.61 s / 1,030,615,040 bytes (REF-05: 606.45 s / 1,031,151,616 bytes); budget 2,147,483,648 bytes |
| Stability elapsed / peak working set | 174.07 s / 5,156,864 bytes (REF-05: 158.58 s / 5,152,768 bytes) |
| Per-case elapsed | p=24 primary 0.56–0.61 s; q=0.5 0.81–0.96 s; cubic 1.90–2.08 s; enlarged 6.06–6.43 s; p=48 6.22–6.93 s; p=96 81.69–85.76 s; stability 43.2–43.8 s |

The reproduced values are therefore the ones tabulated in the REF-05 evidence:
continuum errors 0.00120829246 / 0.000301257334 / 0.0000752634590 on the
primary sequence, orders 2.00390143 / 2.00097486, enlarged difference 2.82e-14,
invariant drifts 4.92e-16 / 5.86e-16 / 1.21e-15 / 1.29e-15 at states
2842 / 8623 / 1283 / 2905, and the same per-component field maxima. The
executable differs from REF-05's build only in its build directory (binary
SHA-256 `056d1148…` versus `8915afbc…`); its source fingerprint is identical.
Elapsed times differ by a few percent between the two runs and are
observations, not acceptance quantities. The re-run's raw artifacts and analysis
remain under the ignored `build/evidence/REF-06/` tree; the tracked compact
record stays the REF-05 summary, which this run reproduces exactly.

The comparison script ignores only the measured timing/resource observations
(`elapsed_seconds`, `resources`, paths, analysis environment); it compares every
other value, including thresholds, source snapshot, statuses, all 36 per-case
propagation metrics, six refinement and six enlarged records, and all four
stability records, at zero tolerance. Its fault sensitivity was checked before
use: a 1e-12 relative perturbation of one continuum error, a one-state shift of
an invariant-error state, a changed threshold, and a `fail` status are each
reported with a nonzero exit, while the tracked summary compared with itself and
with the retained REF-05 re-analysis reports no mismatch.

This establishes that the Phase 1 physical evidence is reproducible by command
from a clean build on the recorded environment. It does not add accuracy beyond
the REF-05 result, since the same source and compiler produce the same
arithmetic; cross-platform numerical agreement remains unmeasured.

## Risk register review at phase exit

| Risk | Status after P1 |
| --- | --- |
| Incorrect staggering, signs, or indexing | Detected by S01–S08 structural checks, the exact-rational golden states, and the signed impedance/direction checks on all six orderings; no defect found in the solver. Residual: oblique/mixed-derivative behavior is checked structurally (S03/S04), not physically. |
| Unstable or inaccurate boundaries/ports | Only the reflecting closure exists; its stability is measured for the declared cases. PEC validation is P2, absorbing boundaries P3, ports P4. |
| Mesh-driven cost exceeds memory | The finest v1 case peaked at 1.03 GB against the enforced 2 GiB budget; the runner aborts over-budget suites. Larger P2 cavity/material meshes must be budgeted in MAT-01. |
| Reference data unavailable or ambiguous | Not exercised in P1 (analytical comparators only). O006 stays open for P4/P6. |
| Same author and reviewer miss a numerical error | Mitigated by three separately written operator forms (solver, permutation-difference fixtures, transcribed oracle) and fault-injected analysis; the limitation is recorded, not removed. |
| Work advances without adequate evidence | This gate compares each P1 criterion with linked measurements; P2 items below each name their completion test and evidence location before starting. |

Three defects were found and fixed during P1 outside the solver: the REF-01
tautological-compare test warning, the REF-03 Python 3.9 header-write
incompatibility, and the REF-05 analyzer/self-test construction errors and
evidence-acceptance gaps. Each is recorded in its item's evidence with the
retained failing output; none changed a tolerance or a solver equation.

## Decision and Phase 2 breakdown

**Decision: PASS.** Phase 1 (reference propagation, vision milestone M1) is
complete within the supported limits above. Cycle C04 is complete and C05 is
ready. The reference-kernel checkpoint (Phases 0–2) remains open until the
Phase 2 gate passes.

The backlog's P2 items are expanded here so each has an ID, dependencies, a
completion test, and an evidence location before it starts. No P2 method,
equation, or tolerance is fixed by this record; MAT-01 must do that in method
notes and V04–V07 specifications before any P2 solver code exists.

| ID | Depends on | Scope | Completion test | Evidence location |
| --- | --- | --- | --- | --- |
| MAT-01 | REF-06 | Method notes for explicit PEC surfaces (interior and outer), the isotropic dielectric and constant-conductivity update with its supported frequency scope, and the spectral processing conventions (transform sign, windowing, resolution); V04–V07 fixtures, independent analytical references, tolerance justification, resource budgets, and structural extensions of S01–S08 and of the synthetic/oracle analyzer coverage | Records reviewed against FND-03 conventions with exact sources; every V04–V07 threshold fixed with a written justification before implementation; analytical audit script extended and passing | `docs/methods/MAT-01-*.md`, `docs/validation/MAT-01-*.md` |
| MAT-02 | MAT-01 | Explicit PEC boundary/surface handling in the reference kernel; V04 cavity resonance evidence | V04 resonant frequencies within the fixed tolerances at three resolutions with mode identification and time/spectral-resolution effects documented; all twelve current CTests and the V01–V03 suites still pass unchanged | `docs/validation/MAT-02-*.md` |
| MAT-03 | MAT-02 | Isotropic dielectric and conductivity updates with material assignment on the Yee grid; V05 propagation/interface and V06 attenuation evidence | V05 phase velocity, reflection/transmission and placement checks and V06 attenuation/phase, nonnegative dissipation and zero-conductivity limit pass their fixed limits; vacuum regressions unchanged | `docs/validation/MAT-03-*.md` |
| MAT-04 | MAT-03 | Production spectral processing validated against independently calculated spectra (V07) and against the MAT-02 cavity analysis | V07 bin/phase/normalization/window checks pass; the production path reproduces the independently checked cavity spectra | `docs/validation/MAT-04-*.md` |
| MAT-05 | MAT-04 | Phase 2 gate review: acceptance matrix, clean-build reproduction of V01–V07, supported limits, P3 breakdown (absorbing boundary method study under O007) | Gate record with linked evidence and a decision | `docs/validation/MAT-05-*.md` |

Ordering note: MAT-02 may use an independently checked analysis script for the
first cavity evidence; MAT-04 then validates the production spectral path
against it, as the backlog already states. The constant-conductivity model must
not be presented as a broadband constant-loss-tangent material (project plan).

## Limits, open items, and next action

- Same-author review, Windows/Clang-only physical execution, and the
  eigenwave-fixture scope are recorded limits, not failures.
- The REF-05 commit `d736c92` and this gate's records are local until the owner
  pushes `main`; the hosted Ubuntu/GCC result for them is therefore pending.
  Pushing is an owner action under the workflow, not part of this gate.
- Peak working set and elapsed time are observations on the reference kernel,
  not performance evidence; P8 owns performance.
- O005–O010 remain open with their need-by points unchanged; none blocks MAT-01.

**Next exact action: MAT-01.** Write the P2 method notes and V04–V07
specifications under the existing FND-03 conventions: explicit PEC surface
treatment and its relation to the current `zero_tangential_e` closure, the
isotropic dielectric/conductivity update equations with stability and frequency
scope, and the spectral processing conventions. Fix V04–V07 fixtures, independent
analytical references, tolerances with justification, resource budgets, and the
required extensions of the structural suite and of the analyzer's synthetic/oracle
coverage. Do not implement P2 solver code before those records are reviewed.
Preserve all twelve CTests and the V01–V03 suites as permanent regressions.
