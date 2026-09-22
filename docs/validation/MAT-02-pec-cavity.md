# MAT-02 — Explicit PEC edge masks and V04 cavity evidence

2026-09-18; addenda 2026-09-22 (V04-C driven acceptance strengthened after
review; then the driven component and edge named and the mode metadata sign
corrected; then the probe record required to be complete). **MAT-02 status: see the decision at the end.** This is the first
measured physical evidence for V04 and the first P2 solver capability. Same
collaborator implemented, ran and reviewed the work; no independent reviewer
is claimed. The [MAT-02 contract](../methods/MAT-02-pec-mask-contract.md)
fixed the API, fixtures, outputs, reductions and their validation before the
suites ran; the [MAT-01 specification](MAT-01-closed-domain-benchmarks.md)
supplies every limit (with the one recorded revision below) and the
[MAT-01 method note](../methods/MAT-01-closed-domain-conventions.md) the
conventions.

## Snapshot and method

Code revision: `bb9e29c` (`main`) plus this item's changes. New solver code:
`include/antennasim/pec.hpp`, `src/pec.cpp`, the mask-aware screening,
E-loop skip, current rejection and constructor overload in `src/vacuum.cpp`
(with the header and detail-kernel overload). New benchmark code:
`benchmarks/common.hpp` (helpers moved verbatim out of `reference.cpp`) and
`benchmarks/closed.{hpp,cpp}`; the CLI gains `--benchmark closed-v1`. New
tests and scripts: `tests/pec_check.cpp` (S09), `scripts/analyze_closed_benchmarks.py`,
`scripts/check_closed_analysis.py`, and a `--benchmark` option in the runner.
No P1 fixture, tolerance, or analyzer changed. The built executable's
source-content fingerprint is `f02fbe47c49ba3067e23051e3e10bc22456f1bfd522c5fd767ae20872e4bf61e` (SHA-256 of the LF-normalized
`source-snapshot.txt`); the [source manifest](MAT-02-source-sha256.txt)
hashes the working-tree bytes of the checked files.

Evidence types are labelled as in the validation plan: the analytical cavity
frequencies `omega_c` and the h^2 refinement expectation are the independent
continuum references; the exact discrete frequencies, line strengths and the
`C*C E = |K|^2 E` identity are analytical diagnostics of the scheme; the
shell/open-cavity equivalence, region zeros, oracle and V01–V03 reproduction
are internal-consistency checks.

## Structural checks (S09) and regression suite

`reference.pec` passes with 209550 checks in Debug and Release:

| Check | Result |
| --- | --- |
| Default mask on `(5,4,3)` and `(2,3,4)` | Equals the grid's tangential-wall classification on every E sample; H never masked; enclosed H equals the normal-H walls; counts equal the closed-form wall count; byte cost `Nex+Ney+Nez` |
| Box, shell, wall-touching and overlapping primitives on both grids | Every E sample agrees with the independent endpoint enumeration (both nodes in the closed box; shells additionally share a face-plane coordinate); contiguous views and counts agree |
| V04-C shell and solid box on `(18,22,26)` | Shell marks 864/1024/1120 = 3,008 edges beyond the closure; the solid box 13,072 |
| Two driven steps with a shell and a box on `(6,5,4)` | Masked E and enclosed H exactly zero; unmasked E and H evolve inside and outside the shell; the box interior stays silent |
| Closure-only mask versus the vacuum path | Stepper and kernel results bitwise identical over three driven steps and one modular-field kernel step |
| Rejections | Inverted, out-of-range, zero-width and unknown-shape primitives; mask/grid mismatch (stepper and kernel); every interior masked or enclosed sample nonzero in the initial data (input not clamped); a current on a masked edge (terminal, state not advanced); charged interior node still rejected; the V04-C mode inside a solid box and the C2 source inside a solid box |
| Fixtures | All `s=1` cavity modes and the three shell modes pass the production screening; eigen identity `1.14e-14`, divergence `4.17e-17`; 53-sample pulse centred on zero with bitwise mirrored samples |

## Reduction validation before physical acceptance

`reference.closed_analysis` passes in Debug and Release (726 checks after the
third 2026-09-22 revision; 709, 684 and 665 before it):

| Check | Result |
| --- | --- |
| Synthetic exact modes, all 30 V04-A configurations plus the `q=0.5` cases | Pass; worst estimator deviation 1.1e-12 (continuum minus prediction, discrete, amplitude, magnetic, residual) |
| Injected V04-A faults | Frequency 3e-9, amplitude 3e-9, H sign, phase 1e-6, relocated line, missing sample, extra line, step count, geometry, mixed times, continuum 1 percent, refinement orders: all detected |
| Synthetic V04-B modal-sum record | Both analyses pass (worst offset 0.0004 bin); shifted line (0.6 bin), spurious line (0.1 strength), missing required line, truncated record, dominant growth, null-component growth above the floor, nonzero start, nonfinite maxima: all detected |
| Synthetic V04-C | C1/C2/C3 pass; nonzero exterior/surface/interior region maxima, a 1e-11 interior deviation from the reference cavity, a missing reference and a wrong mask count: all detected |
| Synthetic V04-C excitation (revision 1.2) | An identically-zero driven record (detected three ways: deposit, floor, invariant), a 1e-11 relative error in the first deposit, a second component moving at state 1, a driven peak at 0.05 of the largest deposit, a 1e-11 post-pulse drift of `Q`, a nonzero start and a 1e-13 relative `dt` error: all detected, for both C2 and C3 |
| Pure-Python oracle versus the four-step closed-v1 smoke suite | Independently enumerated mask counts agree; every probe, `U`, `Q`, the six component maxima and the eighteen region maxima agree within 1e-12 relative at states 0–4 for `cavity-x-m11-s1`, `spectrum-s1`, `pec-c1-x` and `pec-c3-outside` |
| Analyzer on the smoke cases | Four-step cavity: continuum error 0.000892586471 (cap 0.0052), discrete 1.1e-14, amplitude 2.4e-15, magnetic 3.9e-16; the shell case reproduces the open cavity bitwise (265/265 samples) with silent maximum 0 |

The oracle transcribes the six explicit component equations and skips edges
by its own endpoint rule; the benchmark library uses permutation differences
and the `pec_marks` rule; the solver uses its kernels and byte mask. Three
separately written forms therefore agree on every smoke state.

## V04-A — eigenmode resonance, magnetic relation and refinement (30 cases)

Clean Release build, serial execution through `scripts/run_reference_benchmarks.py
--benchmark closed-v1`. All 30 cases pass every limit. The measured continuum
error equals the exact discrete prediction at nine digits in every case; the
implementation-level errors are at roundoff.

| Polarization / mode | N (s=1/2/4) | Continuum error s=1 | s=2 | s=4 | Caps | Orders |
| --- | --- | --- | --- | --- | --- | --- |
| x (1,1) | 109/217/433 | 0.000892586471 | 0.000222975771 | 0.0000557332637 | 0.0052/0.0013/0.000325 | 2.00110499, 2.00027641 |
| x (2,1) | 61/121/242 | 0.00419036084 | 0.00104552852 | 0.000261252758 | same | 2.00284206, 2.00071425 |
| x (1,2) | 81/162/324 | 0.00208018753 | 0.000519576995 | 0.000129864808 | same | 2.00130413, 2.00032702 |
| y (1,1) | 61/121/242 | 0.000907837501 | 0.000226308129 | 0.0000565364449 | same | 2.00414568, 2.00103533 |
| y (2,1) | 55/109/217 | 0.000946480876 | 0.000235759598 | 0.0000588863186 | same | 2.00525685, 2.00131212 |
| y (1,2) | 32/63/125 | 0.00450320766 | 0.00111361438 | 0.000277648944 | same | 2.01570327, 2.00391593 |
| z (1,1) | 57/113/226 | 0.000543505516 | 0.000135425184 | 0.0000338282070 | same | 2.00479862, 2.00119744 |
| z (2,1) | 31/62/123 | 0.003881777 | 0.000959836489 | 0.000239303003 | same | 2.01585667, 2.00395016 |
| z (1,2) | 45/90/179 | 0.00134452466 | 0.000334712309 | 0.0000835898515 | same | 2.00610271, 2.0015219 |

Sensitivity `q=0.5`, `s=1`, mode (1,1): 0.00130992749 (x), 0.00224636418 (y),
0.00208035094 (z) against the 0.0028 cap, equal to the predictions. Over all 30
cases the discrete error `abs(omega_m/omega_d-1)` is at most 8.8e-14, the modal
amplitude error at most 9.7e-13, the magnetic relation error at most 1.1e-12
and the normalized projection residual at most 4.0e-15 (limits 1e-9). The
specification's tabulated predictions are the x-polarization values; the y and
z polarizations have their own predictions from the same formula (the
transverse lengths permute), all below the polarization-independent caps, and
the audit had checked every polarization.

Interpretation: the fixture is the exact discrete eigenvector, so the
measured resonance error is the Yee dispersion of the cavity mode and the
physical content is that it lies below the h^2 caps at three resolutions and
refines at second order with the predicted constants; the magnetic relation
confirms the sign and half-step timing of both transverse H components
against the mode's own curl, including on the outer PEC closure.

## V04-B — driven spectrum, identification and resolution (1 run, 2 analyses)

The `spectrum-s1` run (32,768 steps, 53-sample pulse on `Ez(5,7,9)`, probe
`Ez(7,9,13)`) passes every identification limit on both records:

| Mode | f_d GHz | f_c GHz | peak offset (bins) full / truncated | height error full / truncated | continuum error | limit full / truncated |
| --- | --- | --- | --- | --- | --- | --- |
| (1,1,0) | 1.395817 | 1.396576 | 0.00019 / 0.00018 | 0 / 0 | 5.433e-4 | 7.59e-4 / 9.74e-4 |
| (1,1,1) | 1.445563 | 1.445979 | 0.00016 / 0.00038 | 5.6e-6 / 1.4e-5 | 2.878e-4 | 4.96e-4 / 7.04e-4 |
| (1,1,2) | 1.584524 | 1.584975 | 0.00018 / 0.00016 | 1.0e-3 / 7.1e-4 | 2.847e-4 | 4.74e-4 / 6.64e-4 |
| (1,2,0) | 1.764169 | 1.766544 | 0.00024 / 0.00008 | 4.3e-4 / 7.4e-4 | 1.344e-3 | 1.51e-3 / 1.69e-3 |
| (1,1,3) | 1.789580 | 1.792846 | 0.00021 / 0.00004 | 6.9e-4 / 3.4e-4 | 1.822e-3 | 1.99e-3 / 2.16e-3 |
| (1,2,2) | 1.917681 | 1.918958 | 0.00011 / 0.00019 | 4.4e-4 / 1.9e-4 | 6.657e-4 | 8.22e-4 / 9.79e-4 |
| (1,1,4) | 2.037293 | 2.048734 | 0.00019 / 0.00013 | 1.9e-5 / 2.0e-3 | 5.585e-3 | 5.73e-3 / 5.88e-3 |
| (1,3,0) | 2.239394 | 2.251911 | 0.00019 / 0.00012 | 2.6e-4 / 2.4e-3 | 5.558e-3 | 5.69e-3 / 5.83e-3 |

Limits: 0.25 bin, 0.15 height, no spurious peak (none found on either record),
continuum within dispersion plus 0.25 bin. Every peak sits within 0.0004 bin of
the exact discrete line and the heights follow the closed-form strengths within
0.0024, so the driven cavity reproduces the modal Green's-function prediction
of the method note; the continuum error of each peak is the mode's dispersion.
The truncated analysis shows the resolution effect exactly as predicted: the
continuum limit is dominated by the bin term, not by dispersion.

Fields: finite at every state; the invariant `Q` after the pulse is constant to
6.2e-16 relative and `U/Q_ref` stays within 0.921–1.152 (the `(1±q)` bounds are
0.01 and 1.99). The version-1 growth rule ("no component maximum beyond 1.5
times its maximum over the first 4,096 post-pulse states") **failed** on `Hz`:

| Component | Window maximum | Later maximum | Ratio | Floor (v1.1) |
| --- | --- | --- | --- | --- |
| Ex | 4.917e-2 V/m | 5.032e-2 | 1.023 | 1.12e-10 |
| Ey | 3.538e-2 | 4.272e-2 | 1.207 | 1.12e-10 |
| Ez | 1.117e-1 | 1.313e-1 | 1.176 | 1.12e-10 |
| Hx | 2.334e-4 A/m | 2.810e-4 | 1.204 | 3.02e-13 |
| Hy | 3.020e-4 | 3.210e-4 | 1.063 | 3.02e-13 |
| Hz | 5.418e-19 | 1.394e-18 | 2.573 | 3.02e-13 |

`Hz` is analytically zero for a z-directed edge current (the excitation is TM
to z, and the discrete mixed differences of `Ez` that feed `Hz` cancel
exactly), so its recorded maxima are accumulated roundoff fifteen orders below
the other H components; the block maxima rise linearly (5.4e-19 to 1.4e-18
over eight 4,096-state blocks) while the energy invariant is constant. The
version-1 rule had no absolute floor, contrary to the validation plan's policy
for ill-conditioned relative comparisons; revision 1.1 of the specification
adds the floor `1e-9` of the family's largest window maximum (nine orders
above the observed roundoff, seven below the smallest physical component) and
requires null components to stay below it. The version-1 analysis is retained
under `build/evidence/MAT-02/analysis-v1-growth-rule/` and in the preview run;
under revision 1.1 the case passes. No solver, fixture, identification limit or
cap changed.

## V04-C — interior PEC enforcement (5 cases)

| Case | Steps | Shell edges | Silent-region maximum | Equivalence with `cavity-<a>-m11-s1` |
| --- | --- | --- | --- | --- |
| pec-c1-x | 109 | 864/1024/1120 | 0 (surface and exterior, every state) | 5,830 of 5,830 samples bitwise; max difference 0 |
| pec-c1-y | 61 | 864/1024/1120 | 0 | 3,286 of 3,286 bitwise; 0 |
| pec-c1-z | 57 | 864/1024/1120 | 0 | 2,378 of 2,378 bitwise; 0 |
| pec-c2-inside | 4096 | 864/1024/1120 | 0 (surface and exterior) | driven; see the excitation table |
| pec-c3-outside | 4096 | 864/1024/1120 | 0 (interior and surface) | driven; see the excitation table |

Driven-side excitation under specification revision 1.2 (measured by the
re-analysis of 2026-09-22 described in the addendum; the same raw run):

| Case | First driven state | Closed-form deposit | Relative error (limit 1e-12) | Peak E | Floor (0.1 of the largest deposit) | Ratio | Post-pulse `Q` drift (limit 1e-12) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pec-c2-inside | 7.22927367e-08 V/m | 7.22927367e-08 V/m | 6.77e-15 | 1.791 V/m | 0.1734 V/m | 1.033 | 4.11e-16 |
| pec-c3-outside | 7.22927367e-08 V/m | 7.22927367e-08 V/m | 6.77e-15 | 1.935 V/m | 0.1734 V/m | 1.116 | 3.74e-16 |

No other component of the driven region is nonzero at state 1 in either case.

The three shifted modes pass the full V04-A reductions inside the shell with
identical metrics to the open cavity, every sample outside the open box is
exactly zero at every state, and the pulses inside and outside the shell leave
the other side exactly zero while the driven side reproduces the closed-form
deposit of the source and conserves the invariant, so the interior primitive
enforces the same boundary as the outer closure, shields both ways, and does
so while the shielded side is actually carrying a field.

## V01–V03 regression through the mask-capable kernel

The full 36-case propagation and 4-case stability suites were re-run from the
clean Release build and re-analyzed; `scripts/compare_reference_analysis.py`
against the tracked [REF-05 summary](REF-05-analysis-summary.json) at zero
tolerance: all 1211 compared values of the 40 cases (823 floating-point) agree with zero difference, and the only reported mismatch is the source fingerprint, which changed from `f9ddf4f2…` to `f02fbe47…` because the kernel, headers, build file and CLI changed. The reference-v1 smoke CSVs written by the new build
are byte-identical to those of the MAT-01 build (six files). Together with the
S09 kernel-level check this is the bitwise vacuum equivalence required by the
contract.

## Clean-build regression matrix

Environment: Windows 10 x64 (build 19045), AMD Ryzen 5 3600, project-local
LLVM-MinGW 20250613 / Clang 20.1.7, CMake/CTest 3.31.10, Ninja; strict
binary64 without fast math or contraction; CTest discovered Python 3.10.2 for
the six Python-driven tests; the manual runner/analyzers used Anaconda Python
3.9.7 with psutil 5.8.0. Both build directories were absent before
configuration; verbose build logs show the FND-02 flag set on every target and
no compiler warnings. Commands as at REF-06 with `B=build/MAT-02-{release,debug}`.

| Run | Configure | Build | CTest | Measured CTest time |
| --- | --- | --- | --- | --- |
| Fresh `build/MAT-02-release` | Pass | Pass, no warnings | 15/15 pass | 107.12 s |
| Fresh `build/MAT-02-debug` | Pass | Pass, no warnings | 15/15 pass | 113.42 s |
| Fresh `build/MAT-02-r12-release` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 107.26 s |
| Fresh `build/MAT-02-r12-debug` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 118.55 s |
| Fresh `build/MAT-02-r13-release` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 111.69 s |
| Fresh `build/MAT-02-r13-debug` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 123.02 s |
| Fresh `build/MAT-02-r14-release` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 114.92 s |
| Fresh `build/MAT-02-r14-debug` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 128.16 s |

The two `MAT-02-r12` runs are the regression matrix of the first addendum's
revision (the `MAT-02-r13` rows belong to the second addendum below):
both configure from an absent directory, build without warnings and pass the
same fifteen tests, now including 684 `reference.closed_analysis` checks. Both
reproduce the source fingerprint `f02fbe47…` exactly, which is the mechanical
confirmation that no C++ or CMake input changed. Retained ignored logs:
`build/MAT-02-r12-{release,debug}-{configure,build,test}.log` and
`build/MAT-02-r12-{release,debug}-LastTest.log`.

The fifteen tests are the thirteen of MAT-01 plus `reference.pec` and
`reference.closed_analysis`. The Release executable's SHA-256 is `021faf8f…`.
Retained ignored logs: `build/MAT-02-{release,debug}-{configure,build,test}.log`,
`build/MAT-02-run1.log`, `build/MAT-02-analysis.log`, `build/MAT-02-ref-run1.log`,
`build/MAT-02-ref-analysis.log`, `build/MAT-02-compare.log`, and the preview
`build/MAT-02-dev-*` logs.

## Resources

| Suite | Cases | Elapsed | Peak working set | Budget |
| --- | --- | --- | --- | --- |
| cavity | 30 | 288.40 s | 29,843,456 bytes | 2,147,483,648 bytes |
| cavity-spectrum | 1 | 91.59 s | 5,173,248 bytes | same |
| pec | 5 | 55.21 s | 5,918,720 bytes | same |
| propagation (regression) | 36 | 604.01 s | 1,063,329,792 bytes | same |
| stability (regression) | 4 | 156.05 s | 5,226,496 bytes | same |

These are observations on the checked-access reference kernel with per-state
diagnostics where recorded, not a performance baseline. The preview run from
the development tree took 296.1 s / 93.5 s / 64.5 s for the three closed
suites with peaks of 29.8, 5.2 and 5.9 MB, and its analysis agrees with the
clean-build analysis at zero tolerance (997 compared values of the 36 cases, 654 floating-point, identical at zero tolerance; the two summaries differ only in their source fingerprints).

## Reproduction

From the repository root, choosing fresh output locations:

```powershell
./scripts/build.ps1 -Configuration Release
python scripts/run_reference_benchmarks.py --benchmark closed-v1 --suites cavity cavity-spectrum pec --app build/windows-local-release/antennasim.exe --output build/evidence/MAT-02/run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-02/run1 --output build/evidence/MAT-02/analysis
python scripts/run_reference_benchmarks.py --app build/windows-local-release/antennasim.exe --output build/evidence/MAT-02/ref-run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_reference_benchmarks.py --input build/evidence/MAT-02/ref-run1 --output build/evidence/MAT-02/ref-analysis
python scripts/compare_reference_analysis.py --reference docs/validation/REF-05-analysis-summary.json --candidate build/evidence/MAT-02/ref-analysis/metrics.json
python scripts/check_closed_analysis.py --app build/windows-local-release/antennasim.exe --output-root build/evidence/MAT-02-audit
```

The 2026-09-22 re-analysis reuses the retained raw run and needs no solver:

```powershell
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-02/run1 --output build/evidence/MAT-02/analysis-r12
```

The tracked compact record is [MAT-02-analysis-summary.json](MAT-02-analysis-summary.json)
(the closed analyzer's `metrics.json`); raw probes, diagnostics, per-state
modal traces and the peak tables remain under the ignored `build/evidence/MAT-02/`
tree.

## Addendum 2026-09-22 — V04-C driven acceptance strengthened after review

A later same-author review pass over this closed item found that the version-1
C2/C3 acceptance could not fail on a dead run. The criterion required the
driven side to be *finite*, and an identically-zero region is finite. Fed a
synthetic C2/C3 record whose every region maximum, `U` and `Q` are zero, the
analyzer returned `status: pass` with an empty failure list for both cases:
the silent-region requirement is satisfied by zeros, the finiteness
requirement is satisfied by zeros, and `max_alive` was recorded as a metric
but never compared against anything. No measured result was wrong — the
recorded peaks are 1.47–1.79 V/m (C2) and 1.29–1.94 V/m (C3) — and two other
checks would have caught a fully dead solver (the C1 equivalence against the
live V04-A cavity, and the four-state oracle comparison, which covers
`pec-c3-outside`). `pec-c2-inside` had no positive-field coverage anywhere,
and neither driven case had any at the fixed 4,096-step length. The gap was in
the acceptance criterion, not in the analyzer's implementation of it.

Resolution: MAT-01 [revision 1.2](MAT-01-closed-domain-benchmarks.md) adds the
excitation requirements (closed-form first deposit, an exact-zero rest of the
region at state 1, a dead-region floor on the driven peak, and the
dissipationless invariant after the pulse), all computed by the specification
audit from the fixed pulse and time step. The analyzer enforces them and the
reduction test injects eight faults per driven case, including the
identically-zero record that exposed the gap, which now fails three separate
requirements.

The raw runs were re-analyzed under revision 1.2 without re-running the
solver: `ANTENNASIM_SOURCE_SNAPSHOT` fingerprints only the C++ and CMake
inputs, none of which changed, so the retained `build/evidence/MAT-02/run1`
remains output of the same executable and carries the same `f02fbe47…`
fingerprint. All four suites pass; the measured margins are in the V04-C
excitation table above (deposit error 6.8e-15 against 1e-12, driven peak 10.3x
and 11.2x the floor, invariant drift 4.1e-16 and 3.7e-16 against 1e-12). The
tracked [summary](MAT-02-analysis-summary.json) is the re-analysis and records
`excitation_rule_version: 1.2`. `scripts/check_material_benchmarks.py`,
`scripts/analyze_closed_benchmarks.py` and `scripts/check_closed_analysis.py`
changed; no solver source, fixture, cap, identification limit or geometry did.

## Failures, limits, and next action

- One acceptance criterion failed as written and was revised with a recorded
  reason (V04-B growth rule, version 1.1); the failing analysis is retained.
  No solver, fixture, cap or identification limit changed, and the revision
  adds an absolute floor rather than widening a tolerance.
- One acceptance criterion was too weak to fail rather than wrong: the V04-C
  driven cases required only finiteness of the driven side, which a dead run
  satisfies. Found by review after this item was first closed, not by a
  measurement; see the addendum. Specification revision 1.2 adds the
  excitation requirements, the runs were re-analyzed under them and pass, and
  no recorded measurement changed value.
- Two defects in new test/audit code were corrected before any physical run
  and are not solver findings: the S09 pulse check summed the samples naively
  instead of checking the mirrored pairs (and assumed the wrong sign of the
  first sample), and two synthetic fault injections (continuum direction,
  null-component growth) were below their limits.
- The closed-v1 artifact audit initially rejected smoke output because smoke
  cases carry their own suite label; the audit now accepts any label under the
  smoke marker only.
- The `reference-v1` metadata budget (`working_bytes_budgeted`) does not count
  the closure-only mask that the stepper now allocates (`Nex+Ney+Nez` bytes,
  about one sixteenth of the field payload, 30.7 MiB at `p=96`); the measured
  peaks below include it and stay far under 2 GiB. The `closed-v1` budget
  counts the mask. Correct the reference budget when MAT-03 adds material arrays.
- Limits: same-author review, including the 2026-09-22 review pass and the
  revision it produced; physical suites ran on one Windows/Clang
  machine while hosted CI runs the smoke-length reductions; the supported PEC
  envelope is grid-aligned full-edge boxes and shells on the declared cavity
  grids, exact-mode and single-edge-pulse excitation, and 32,768-step
  durations; thin sheets, subcell or conformal conductors, finite
  conductivity, materials, absorbing boundaries, ports and antenna results
  remain unvalidated. The production spectral path (MAT-04) does not exist;
  the V04-B identification was performed by the independent analyzer as the
  backlog allows, and MAT-04 must reproduce it.


## Addendum 2026-09-22 (second) — driven component and edge named; metadata sign corrected

A follow-up review of the first addendum's work found two defects, both
recorded in the [review report](MAT-02-review-2026-09-22.md).

**R1 — the strengthened acceptance still accepted the wrong component.**
Revision 1.2 compared the *largest* of the three electric region maxima with
the closed-form deposit. Region maxima are unsigned and carry no location, so
the requirement was satisfied by a deposit in `Ex` or `Ey`, and nothing in the
reduction referred to the edge the source drives. Demonstrated on copies of
the retained C2/C3 records: exchanging the `Ex` and `Ez` maxima at state 1 —
globally and in the live region — and zeroing the recorded `Ez` source probe
left both the structural artifact audit and the complete PEC reduction
returning `pass` with empty failure lists for both driven cases. The original
evidence was not modified; the reproduction is retained at
`build/evidence/MAT-02/review-faults.py` with its mutated copies and results in
`build/evidence/MAT-02/review-wrong-component/`.

Resolution: MAT-01 [revision 1.3](MAT-01-closed-domain-benchmarks.md) requires
the deposit in `Ez` specifically, requires every other component to be zero at
state 1 both in the driven region and over the whole domain, and checks the
native `Ez` sample of the prescribed source edge — which C2 and C3 already
record — against the signed closed-form value `-(dt/eps0) J0 g_0`. The same
mutation now fails three requirements in each driven case. Measured on the
retained raw run:

| Case | Source edge | State-1 source sample | Signed closed-form deposit | Relative error (limit 1e-12) |
| --- | --- | --- | --- | --- |
| pec-c2-inside | (8,10,12) | -7.22927367e-08 V/m | -7.22927367e-08 V/m | 6.77e-15 |
| pec-c3-outside | (1,1,1) | -7.22927367e-08 V/m | -7.22927367e-08 V/m | 6.77e-15 |

**R2 — mode metadata recorded the opposite initial H sign.** Every mode case
emitted `H=-C E_s/(mu0 Omega) sin(omega_d dt/2) at -dt/2` into
`configuration.json` and `metadata.json`. That expression is the amplitude
`H_s` multiplied by `sin(omega_d dt/2)`, but the field written at `-dt/2` is
`H^(-1/2) = -H_s sin(omega_d dt/2)`, the positive form the initializer, the
MAT-01 and MAT-02 specifications and the independent pure-Python oracle all
use. This was a metadata defect only: no computed field, fixture check or
measurement was affected, and the eigenvector and divergence fixture checks,
the V04-A modal results and the oracle comparison all confirm the implemented
sign. Its consequence is that the initial condition could not be reconstructed
faithfully from the description the run carries.

Resolution: `benchmarks/closed.cpp` emits
`H=+(C E_s) sin(omega_d dt/2)/(mu0 Omega) at -dt/2 by permutation curl`, and
the structural audit now checks the emitted `initialization` description
against the two prescribed forms. The retained raw evidence is not rewritten:
the historical mode description is admitted only together with the source
snapshot `f02fbe47…` that emitted it, so those runs stay auditable while any
other description fails. Because a C++ input changed, the source fingerprint
moves to `706af2e4…`; the retained runs keep `f02fbe47…`, and the next full
physical run supersedes them under the new fingerprint.

**Verification.** `reference.closed_analysis` grows from 684 to 709 checks: the
wrong-component and wrong-edge faults for both driven cases (deposit moved to
`Ex`, wrong-sign source sample, dead source edge, leaking second probe, a
non-`Ez` probe, a relocated probe, an unprobed source edge, and the R1
mutation itself) and the initial-condition description against its current,
historical and flipped-sign forms. Re-analysis of the retained raw run passes
all four suites with every previously tracked value bit-identical; the tracked
summary gains only `source_probe_first_state`/`source_probe_error` per driven
case and the rule version. The smoke path exercises the corrected emitter
end to end: the audit reads freshly emitted artifacts carrying the new
description, and `pec-c3-outside` passes the source-edge check against the
real solver.

| Build | Configure | Build | CTest | Total test time |
| --- | --- | --- | --- | --- |
| Fresh `build/MAT-02-r13-release` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 111.69 s |
| Fresh `build/MAT-02-r13-debug` (2026-09-22) | Pass | Pass, no warnings | 15/15 pass | 123.02 s |

Both configure from an absent directory and reproduce the new fingerprint
`706af2e4…`. Retained CTest logs:
`build/MAT-02-r13-{release,debug}/Testing/Temporary/LastTest.log`. The
re-analysis reuses the retained raw run and needs no solver:

```powershell
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-02/run1 --output build/evidence/MAT-02/analysis-r13
```

Not repeated: a full physical re-run of V01–V04 under the new fingerprint,
hosted CI, and validation on a second machine.

## Addendum 2026-09-22 (third) — the probe record must be complete

A third review pass found that a prescribed probe missing from the entire
record passed both the structural audit and the V04-C reduction. The audit
compared the *number* of probe rows per state, which stays uniform when a probe
is absent from every state, and the revision-1.3 reduction read its prescribed
samples through a defaulting lookup, so the missing samples were read as the
zeros the requirements expect.

Demonstrated on copies of the retained C2/C3 records: deleting all 4,097
samples of the second prescribed probe (the shielded-side edge) from each
driven case — 8,194 rows down to 4,097 — left the artifact audit and the
complete PEC analysis returning `pass` with empty failure lists for both cases.
The original evidence was not modified. Two reproductions are retained: the
review's own `build/evidence/MAT-02/recheck-probe-completeness.py` with
`signoff-missing-probe/`, and `review-missing-probe/` from the fix. Re-running
the review's script after the fix stops at the audit, which now rejects the
mutated copies; its `result.json` was regenerated by that run and records the
post-fix outcome, so the pre-fix `pass` it originally held is preserved only in
the quoted finding of the [review report](MAT-02-review-2026-09-22.md).

Resolution: MAT-01 [revision 1.4](MAT-01-closed-domain-benchmarks.md) requires
the record to be complete, in two layers. The structural audit compares the
recorded `(component, index)` key set: identical at every state, and for a
source case exactly the `Ez` edges the artifact's own `probe_indices` declares.
Because that compares an artifact with itself, the V04-C reduction derives the
C2/C3 probe pairs from the fixture instead — `(10,12,16)`/`(8,10,12)` and
`(1,1,1)`/`(9,11,13)`, computed and geometrically checked by the specification
audit — and requires the declared and recorded sets to equal them. The
reduction then requires `(steps+1) * probes` prescribed samples and reads each
sample it needs as present rather than defaulted. The same deletion now fails
the audit with `recorded probes differ from the prescribed indices`, and the
reduction with the sample count and both missing states, in both cases:

| Mutation | Before | After |
| --- | --- | --- |
| Second probe deleted from every state (C2 and C3) | audit pass, reduction pass, no failures | audit rejects; reduction reports 4097 of 8194 prescribed samples and the two absent states |

`reference.closed_analysis` grows from 709 to 726 checks: the coverage rule
against a uniformly absent probe, an extra probe, a key set that varies between
states, a missing state and an empty record, and the reduction against a
deleted second probe, a single deleted state, a deleted source sample, a short
declared probe set and a duplicated sample standing in for a missing one.
Re-analysis of the retained raw run passes all four suites with every
previously tracked value bit-identical; the only tracked-summary change is the
rule version. Fresh Debug and Release (`build/MAT-02-r14-{debug,release}`)
configure, build without warnings and pass 15/15 CTests, 726
`reference.closed_analysis` checks in each, in 114.92 s and 128.16 s. No
solver, fixture, geometry, cap or identification limit changed, and the source
fingerprint stays `706af2e4…` because no C++ or CMake input changed.

Decision: **MAT-02 complete** (2026-09-18; re-confirmed on 2026-09-22 under
specification revisions 1.2, 1.3 and 1.4 after the review findings in the three
addenda). The explicit PEC capability is validated for the declared cavity
envelope; P2 remains open. Next exact action: MAT-03.
