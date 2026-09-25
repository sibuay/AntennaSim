# MAT-03 — Per-cell dielectric and constant-conductivity updates, V05/V06 evidence

2026-09-22 to 2026-09-23. **MAT-03 status: see the decision at the end.** This
is the first measured evidence for materials. The same collaborator
implemented, ran and reviewed the work, and no independent reviewer is
claimed.

The [MAT-03 contract](../methods/MAT-03-material-update-contract.md) fixed the
API, the storage (D023), the fixtures, the outputs, the reductions and their
validation before any V05/V06 suite ran. The
[MAT-01 specification](MAT-01-closed-domain-benchmarks.md) supplies every
limit, with one revision recorded below (V05-B purity 1.5, D025). The
[MAT-01 method note](../methods/MAT-01-closed-domain-conventions.md) supplies
the conventions.

## Snapshot and method

The code revision is `2ef9c48` (`main`) plus this item's changes.

**New solver code:**

- `include/antennasim/material.hpp` and `src/material.cpp`: `MaterialMap`, and
  `EdgeCoefficients` with the deduplicated table and `uint32` index.
- The routing of every `ReferenceStepper` constructor through the material
  kernel `Enew = Ca E + Cb curl H`, with the vacuum table as the default.
- Eps-weighted Gauss-law screening, and `Cb` in the source term. The
  `detail::advance_e` overload taking coefficients.

**New benchmark code:** `benchmarks/material.{hpp,cpp}` (the `dielectric`,
`interface`, `slab-cavity`, `lossy` and `dissipation` suites and the smoke
additions). There are also helpers in `benchmarks/common.hpp`, V04 metadata
provenance and memory accounting in `closed.cpp`, and the corrected
`reference-v1` budget in `reference.cpp`.

**New tests and scripts:**

- `tests/material_check.cpp` (S10–S13), with `tests/material_steps_golden.hpp`
  from `scripts/generate_material_steps.py`.
- `scripts/material_reductions.py` (the V05/V06 reductions) and
  `scripts/check_material_analysis.py` (synthetic, coefficient-audit and
  oracle checks).
- Extensions to `analyze_closed_benchmarks.py` and `check_closed_analysis.py`.
- The corrected transient budget in `check_material_benchmarks.py`.

No V01–V04 fixture, tolerance or reduction changed.

The source-content fingerprint of both fresh builds is
`1621d840d4ee1871afa7d92e1a302b9bd7ab4d38e67d1f6c80342165da433801`. The
Release executable's SHA-256 is `fbb58d99…`. The
[source manifest](MAT-03-source-sha256.txt) hashes the working-tree bytes of
the checked files.

**Evidence types.**

- **Continuum references (independent):** the medium phase speed and
  impedance, the modal Fresnel `R`/`T`, the slab-cavity transcendental roots,
  the decay rate `sigma/(2 eps)` and the damped frequency.
- **Analytical diagnostics of the scheme:** the discrete dispersion, the
  closed-form discrete `R_d`/`T_d`, the discrete slab roots and eigenvector,
  and the exact lossy growth factor `z`.
- **Internal consistency:** the dissipation identity, the S10–S13
  enumerations, the oracle, and the zero-tolerance reproductions.

## Structural checks (S10–S13) and regression suite

| Test | Checks | Result |
| --- | --- | --- |
| `reference.material_map` (S10) | 3022 (9554 after the second 2026-09-25 review, which added two maps whose `sigma` does not follow `eps_r` and a transcribed P1 driven step; see the second addendum) | Modular maps on `(2,3,4)` and `(5,4,3)`: every edge entry equals an independent cell-to-edge enumeration (worst `2.08e-16` relative); entry edge counts equal the enumeration; entries distinct. A vacuum map gives `Ca=1`, `x=0`, `Cb=dt/epsilon0` bitwise, identical to the default table. Rejected: `eps_r<1`, `sigma<0`, NaN/inf, wrong lengths, grid and spacing mismatch, wall-edge lookups. The material kernel with vacuum coefficients is bitwise the P1 kernels (closure and interior shell); the stepper with a vacuum map (masked or not) is bitwise the default over driven steps. Every constructor now shares the material kernel, so that last comparison shows only that a vacuum map and the default table agree; the stepper-level bitwise P1 evidence is V06-C, a manual run, not a CTest. `div E=0` with a modular map is rejected; `div(eps E)=0` is accepted |
| `reference.material_update` (S11) | 1034 | Single edge at `x` in `{0, 0.01, 0.045, 0.5}` with `J`: worst `1.87e-16` normalized. Two full lossy steps on `(5,4,3)` against 513 exact-rational samples: worst `1.0e-15` normalized per component (limit `1e-13`) |
| `reference.material_timestep` (S12) | 19 | Material `dt`, CFL limit and `e_scale` equal the vacuum values for `eps_r` of 1, 4 and 2.25 with `sigma` up to 5 S/m. These equalities hold by construction (the stepper takes the `VacuumTimeStep` it is given), so only the rejection checks can detect a regression. `eps_r<1` and `sigma<0` are rejected by `uniform` on a grid of `2^50` cells as `invalid_argument` (before allocation). `eps_r=1e308` (`Cb=0`) and `x=inf` are rejected as `overflow_error` |
| `reference.material_dissipation` (S13) | 611 | One step on modular E/H fields with the S10 map: `abs(Q_(n+1)-Q_n+D_n)` is at most `7.04e-17` of the sum of absolute terms (limit `1e-12`) |
| `reference.material_steps` | 513 samples x 3 states | The exact-rational generator reproduces the committed header; exact walls, `div(eps_r,e E)` and `div H` |

The fifteen existing tests pass unchanged. That includes the S09 bitwise
comparisons of the stepper with the P1 kernels, which now run through the
material kernel.

## Reduction validation before physical acceptance

`reference.closed_analysis` grows from 726 to 2636 checks (2641 after the
first 2026-09-25 review addendum, 2654 after the second, 2655 after the
hosted-CI fix):

| Check | Result |
| --- | --- |
| Synthetic V05-A (18 configurations) and V06-A (10, both `sigma`) | Pass; worst estimator deviation `4.95e-14`. Detected faults: frequency `3e-9`, amplitude `3e-9`, H sign, H phase `1e-6` (impedance), inactive leak `1e-8`, continuum 1 percent, step count, conductivity metadata, decay-rate change `2e-3`, growth factor `3e-9`, the lossless-initialization transient `(z0-x)/(1+x)`, and an amplitude below the `0.5 A` floor |
| Synthetic V05-B (reduced-TE oracle series, `p=16`, three orientations) | Pass. Detected: a one-state shift of the reflected window (discrete `R` and `Im R`), a 0.1 percent reflected magnitude, a transmitted shift, a one-ulp `b`-plane mismatch, an orientation series scaled by `1+1e-11`, a gate/layout change, and a missing sample. Under revision 1.5: TE_2 content of `2e-9 a_n` at the peak state and `3e-13` of the peak at a quiet state are detected; `5e-10 a_n` and roundoff-scale `2e-15` of the peak pass. Version 1 would have reported `7.5e-9` for the latter. A zero record passes only when exactly pure |
| Synthetic V05-C | Pass (`2.26e-12`). Detected: frequency `3e-9`, amplitude `3e-9`, the vacuum shape in place of the slab eigenvector, continuum 1 percent, step count, and a missing sample |
| Synthetic V06-B | Pass for both `q`. Detected: a `2e-8 Q_n` balance fault, a `1e-11` increase, a negative `D`, a bound violation, `Q_N/Q_0=1e-3`, a nonfinite value, a state-0 `D`, and a step count |
| Coefficient-table audit | The closed-form plane classes equal a brute-force enumeration on `(6,9,2)` with the plane along `y`. Detected: a wrong edge count, a wrong `Cb` (`1e-14`), a one-ulp vacuum `Cb`, an extra or missing entry, the index bytes, the map summary, the interface cell, a missing table, a `sigma` perturbed by `1e-14`, a `Ca` perturbed by `1e-14`, a non-vacuum V04 entry, and the V04 map bytes. Retained V04 evidence without a table is accepted |
| Pure-Python material oracle against the nine-case closed-v1 smoke suite at four steps | Independently averaged per-cell materials, the lossy update, `D`, and transcribed wave, sheet, slab and modular fixtures. Every probe, `U`, `Q`, `D` and the six maxima agree within `1e-12` at states 0–4 for `dielectric-xy-p24`, `interface-x-p16`, `slab-x-m1-p24`, `lossy-xy-p24-sig0p1` and `dissipation-q99`. The four V04 smoke cases still agree. A separate mutation check detected a `1e-10` change in the oracle's `Cb`, a `1e-9` change in `sigma` and a `1e-9` change in the slab fixture |

The oracle, the benchmark library and the solver compute the edge means in
three different summation orders and with three separately written curls.

## V05-A — homogeneous dielectric eigenwave (18 cases): pass

All six orderings give identical metrics at each `p`. The measured continuum
error equals the exact discrete prediction at nine digits:

| p | N | Continuum error | Cap | Prediction |
| --- | --- | --- | --- | --- |
| 24 | 6 | 0.00244345191 | 0.003 | 0.00244345191 |
| 48 | 12 | 0.000610746151 | 0.00075 | 0.000610746151 |
| 96 | 25 | 0.000152679168 | 0.0001875 | 0.000152679168 |

The refinement orders are 2.00028 and 2.00007 for every ordering. Over the 18
cases, with limits `1e-9` or `1e-8`:

| Quantity | Worst value |
| --- | --- |
| Discrete error | `6.7e-16` |
| Amplitude error (E / H) | `6.7e-16` / `1.1e-15` |
| Fit residual | `4.6e-14` |
| Inactive lines | exactly 0 |
| Complex impedance `abs(Z/(s eta)-1)` against `eta=188.365156706` ohm | `1.6e-15` |

## V05-B — TE-mode interface (7 cases): pass under revision 1.5; version 1 failed on purity

| Case | N | gate | Band max continuum (R / T) | Cap | Discrete `R`,`T` | `abs(Im R)` | Purity 1.5 | Purity v1 (reported) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p=16 (x, y, z) | 611 | 316 | 0.0471713 / 0.0471740 | 0.06 | 1.23e-5 | 4.09e-6 | 8.53e-12 | 1.47e-9 |
| p=32 (x, y, z) | 1221 | 632 | 0.0103654 / 0.0103663 | 0.0135 | 1.28e-5 | 5.36e-6 | 1.03e-11 | 5.14e-8 |
| p=64 (x) | 2441 | 1263 | 0.00251327 / 0.00251488 | 0.0034 | 1.31e-5 | 5.40e-6 | 1.58e-11 | 1.28e-7 |

The measured `abs(R)` continuum errors equal the specification's closed-form
predictions: `0.0471713`, `0.0103654` and `0.00251327`. The discrete
coefficients agree within `1.31e-5` of `R_d`/`T_d`. That is the level at which
the audit's reduced oracle reproduced them, set by the finite gate, against a
limit of `1e-4`.

The `E_b[j=1]` and `E_b[j=0]` planes are bitwise equal at every state. The
three orientations produce bitwise-identical probe series (difference 0) at
`p=16` and `p=32`. The refinement orders of the x band maximum are 2.18609 and
2.04334, strictly decreasing, against the predicted 2.186 and 2.042.

**Version-1 purity failure (retained).** The first analysis failed the
version-1 purity rule in all seven cases, with the values in the last column.
That analysis is retained in `build/evidence/MAT-03/interim-interface/`. The
investigation (`build/evidence/MAT-03/purity-investigation.{py,log}`) is read
only and uses the retained raw run:

- The limit is exceeded at 2, 7 and 28 of 612, 1222 and 2442 states. At every
  one of them the TE_1 amplitude at probe 1 is below `1e-6` of the record peak
  (carrier zero crossings and the quiet gaps between pulses).
- By amplitude band (at least `1e-2` of the peak, `1e-4`, `1e-6`, below), the
  normalized residual grows from `~1e-13` to `1e-11`, `1e-9` and `1e-7`, while
  the residual measured against the peak stays at `0.7–1.7e-15` in every band.
  This is binary64 roundoff carried by the other transverse modes. It is not a
  solver, source-profile or material-assignment error, because each of those
  would scale with the amplitude.
- At the version-1 every-64-state cadence the worst values would have been
  `3.6e-10`, `1.6e-10` and `9.1e-10`. The owner-confirmed every-state record
  exposed the zero crossings.

Revision 1.5 (D025) normalizes by `max(abs(a_n), 1e-4 peak)`. The floor comes
from `eps * peak` with a factor of about 500 for accumulation. The version-1
limit is unchanged at states with `abs(a_n) >= 1e-4 peak`, about 58% of the
record. The other 42% (256 of 612, 513 of 1222 and 1026 of 2442 states,
including 33, 65 and 129 exactly-zero states before the pulse arrives) are
bounded by `1e-13` of the peak. Between `2.2e-7` and `1e-4` of the peak (218,
431 and 856 states) that is looser than the version-1 relative limit by up to
about 450 times. The first version of this record said the limit was
unchanged "wherever the amplitude is resolvable"; the 2026-09-25 review
corrected that (see the review addendum). The same raw run was
re-analyzed without re-running the solver. The owner delegated the decision on
2026-09-23 on the condition that it resolve the failure without lowering the
quality bar, and asked that the principle apply to future work (validation
plan, failure handling).

## V05-C — slab-loaded TE cavity (18 cases): pass

The three orientations give identical metrics:

| Mode / p | N | `f_c` GHz | Continuum error | Cap | Prediction | Orders |
| --- | --- | --- | --- | --- | --- | --- |
| 1 / 24, 48, 96 | 216, 432, 863 | 0.3370011 | 2.98079753e-4, 7.45722299e-5, 1.86463129e-5 | 3.8e-4, 9.5e-5, 2.4e-5 | 2.98079753e-4, 7.457223e-5, 1.86463127e-5 | 1.99899, 1.99975 |
| 2 / 24, 48, 96 | 102, 203, 406 | 0.7162933 | 4.40176255e-3, 1.09929951e-3, 2.7475271e-4 | 5.5e-3, 1.4e-3, 3.5e-4 | same to nine digits | 2.00150, 2.00038 |

Discrete error at most `2.05e-13`, modal amplitude error at most `2.27e-12`,
and projection residual at most `2.9e-15`, all against `1e-9`. The
generator's bisected `f_d` agrees with the analyzer's to `4.4e-16`. The fixture
reported an eigen-identity error of `8.4e-14` on the smoke case, against
`1e-11`. This case checks the material assignment and the interface-edge mean
on every axis.

## V06-A — lossy eigenwave (26 cases): pass

All orderings agree at each `(p, sigma)`:

| sigma S/m | p | x | Decay error | Cap | Phase error | Cap | Minimum `abs(C_n)` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.01 | 24 | 0.004477 | 6.6808e-6 | 8.5e-6 | 0.00244508 | 0.0035 | 0.9735 |
| 0.01 | 48 | 0.002238 | 1.67018e-6 | 2.1e-6 | 0.000611151 | 0.0009 | 0.9735 |
| 0.01 | 96 | 0.001119 | 4.17547e-7 | 5.3e-7 | 0.00015278 | 0.00022 | 0.9724 |
| 0.1 | 24 | 0.04477 | 6.68876e-4 | 8.5e-4 | 0.0028152 | 0.0035 | 0.7643 |
| 0.1 | 48 | 0.02238 | 1.67068e-4 | 2.1e-4 | 0.000703325 | 0.0009 | 0.7644 |
| 0.1 | 96 | 0.01119 | 4.17576e-5 | 5.3e-5 | 0.000175802 | 0.00022 | 0.7559 |

The decay errors equal `x^2/3` and the phase errors equal the predictions of
the specification. Every per-step ratio agrees with the exact growth factor `z`
within `8.8e-15` (limit `1e-9`), so the fixture is the lossy eigenwave, not the
lossless start. The magnetic-line ratio agrees within `5.3e-15` (reported).
Fit residual is at most `4.3e-14`, and the inactive lines are exactly zero. The
generator's `z` equals the analyzer's bit for bit.

Refinement orders: decay 2.00001/2.00000 (`sigma=0.01`) and 2.00130/2.00033
(`0.1`); phase 2.00028/2.00007 and 2.00097/2.00024 for `xy`. The other
orderings' single 24/48 orders are identical. The supported conductivity scope
remains `x <= 0.045`. The largest case here is `x = 0.04477`.

## V06-B — closed-grid dissipation identity (2 cases): pass

| Case | Q_0 J | Max balance / Q_n | Max Q increase | Bounds | D >= 0 | Q_N/Q_0 |
| --- | --- | --- | --- | --- | --- | --- |
| dissipation-q99 | 1.51460e-14 | 6.32e-16 | none | every state | every state | 8.74e-12 |
| dissipation-q50 | 1.51460e-14 | 6.50e-16 | none | every state | every state | 2.60e-6 |

The balance limit is `1e-8`. `Q_0 = U_0`, because the initial H is zero.

## V06-C — zero-conductivity limit and V04 regression

- **V01–V03.** The full 36-case propagation and 4-case stability suites were
  re-run through the material kernel from the clean Release build and
  re-analyzed. Against the tracked [REF-05 summary](REF-05-analysis-summary.json),
  `scripts/compare_reference_analysis.py` at zero tolerance found all 1211
  compared values (823 floating-point) identical. The only mismatch is the
  source fingerprint, `f9ddf4f2…` to `1621d840…`.
- **V04.** The 36 V04 cases were re-run and re-analyzed (`--suite v04`).
  Against the tracked [MAT-02 summary](MAT-02-analysis-summary.json), all 1021
  compared values (677 floating-point) are identical at zero tolerance. The
  only mismatch is the fingerprint, `f02fbe47…` to `1621d840…`.
- **Smoke bytes.** The reference-v1 smoke CSVs (six files) and the four V04
  closed-v1 smoke cases (eight files) written by the clean MAT-03 build are
  byte-identical to those written by the MAT-02 build (`build/MAT-02-final-review-release`).
  The comparison is in `build/evidence/MAT-03/smoke-bytes/compare.txt`.

Together with S10, this is the bitwise vacuum equivalence the contract
requires.

## Clean-build regression matrix

**Environment:** Windows 10 x64 (build 19045), AMD Ryzen 5 3600,
project-local LLVM-MinGW 20250613 / Clang 20.1.7, CMake/CTest 3.31.10 and
Ninja. Floating point is strict binary64, with no fast math and no contraction
(`-ffp-contract=off -fno-fast-math` confirmed on every target in the verbose
logs). CTest discovered Python 3.10.2. The manual runner and analyzers used
Anaconda Python 3.9.7 with psutil 5.8.0. Both build directories were absent
before configuration.

| Run | Configure | Build | CTest | Measured CTest time |
| --- | --- | --- | --- | --- |
| Fresh `build/MAT-03-release` | Pass | Pass, 0 warnings | 20/20 | 172.51 s |
| Fresh `build/MAT-03-debug` | Pass | Pass, 0 warnings | 20/20 | 294.36 s (concurrent with the physical run) |
| Same trees, final analysis scripts (revision 1.5) | — | Nothing to rebuild | 20/20 each | 168.40 s / 183.75 s |

The twenty tests are:

- the fifteen of MAT-02;
- the four S10–S13 groups (`reference.material_map`, `_update`, `_timestep`,
  `_dissipation`);
- the golden-state generator `reference.material_steps`.

The analysis scripts changed after the first CTest run of each tree: the
revision-1.5 purity rule and its self-test. No C++ or CMake input changed, the
fingerprint is the same, and both trees were re-run.

The retained logs are ignored by Git:

- `build/MAT-03-{release,debug}-{configure,build,test}.log` and
  `build/MAT-03-{release,debug}-test-final.log`;
- `build/MAT-03-run1.log`, `build/MAT-03-ref-run1.log` and
  `build/MAT-03-analysis*.log`;
- `build/MAT-03-compare.log` and `build/MAT-03-compare-v04.log`;
- the development-tree logs `build/MAT-03-dev-*`.

## Resources

| Suite | Cases | Elapsed | Peak working set |
| --- | --- | --- | --- |
| dielectric | 18 | 1078.33 s | 1,360,728,064 bytes |
| interface | 7 | 453.10 s | 45,039,616 bytes |
| slab-cavity | 18 | 86.47 s | 9,601,024 bytes |
| lossy | 26 | 475.68 s | 1,360,830,464 bytes |
| dissipation | 2 | 8.60 s | 4,100,096 bytes |
| cavity (V04 regression) | 30 | 310.78 s | 31,784,960 bytes |
| cavity-spectrum (V04 regression) | 1 | 90.40 s | 4,145,152 bytes |
| pec (V04 regression) | 5 | 60.17 s | 4,968,448 bytes |
| propagation (V06-C) | 36 | 592.32 s | 1,190,846,464 bytes |
| stability (V06-C) | 4 | 163.10 s | 4,132,864 bytes |

Every suite is below the 2,147,483,648-byte budget. The `p=96`
dielectric/lossy peak, 1.267 GiB, sits just under the D023 calculation of
1.279 GiB (map, index, two payloads, mask and overhead). With two doubles per
edge it would have been about 1.64 GiB. The V01 propagation peak rose from
1,063,329,792 bytes (MAT-02) to 1,190,846,464, which matches the 122.6 MiB
vacuum index.

These are observations on the checked-access reference kernel, not a
performance baseline. The dielectric run overlapped the Debug build and its
CTest.

## Reproduction

From the repository root, choosing fresh output locations:

```powershell
./scripts/build.ps1 -Configuration Release
python scripts/run_reference_benchmarks.py --benchmark closed-v1 --suites dielectric interface slab-cavity lossy dissipation cavity cavity-spectrum pec --app build/MAT-03-release/antennasim.exe --output build/evidence/MAT-03/run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-03/run1 --output build/evidence/MAT-03/analysis
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-03/run1 --output build/evidence/MAT-03/analysis-materials --suite materials
python scripts/analyze_closed_benchmarks.py --input build/evidence/MAT-03/run1 --output build/evidence/MAT-03/analysis-v04 --suite v04
python scripts/compare_reference_analysis.py --reference docs/validation/MAT-02-analysis-summary.json --candidate build/evidence/MAT-03/analysis-v04/metrics.json
python scripts/run_reference_benchmarks.py --app build/MAT-03-release/antennasim.exe --output build/evidence/MAT-03/ref-run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_reference_benchmarks.py --input build/evidence/MAT-03/ref-run1 --output build/evidence/MAT-03/ref-analysis
python scripts/compare_reference_analysis.py --reference docs/validation/REF-05-analysis-summary.json --candidate build/evidence/MAT-03/ref-analysis/metrics.json
python scripts/check_closed_analysis.py --app build/MAT-03-release/antennasim.exe --output-root build/evidence/MAT-03-audit
```

The fresh trees were configured with
`cmake --preset windows-local-{release,debug} -B build/MAT-03-{release,debug}`.
The tracked compact record is
[MAT-03-analysis-summary.json](MAT-03-analysis-summary.json), the analyzer's
`metrics.json` for the five material suites. The full eight-suite summary, the
traces, the raw probes and diagnostics remain under the ignored
`build/evidence/MAT-03/` tree.

## Findings during the item

- **V05-B purity, version 1.** A measurement-definition failure, recorded
  above. It was resolved by revision 1.5 (D025) with the failing analysis
  retained. No solver change.
- **Specification errata recorded before any run.** The V05-C spacing text
  (`1.5` against the audit's `2`), the V05-B line cadence against revision 1.4,
  and the S10 clipping. See the specification. No limit changed.
- **Resource budget.** The MAT-01 transient omitted the coefficient and map
  storage. It is corrected in the specification and the audit script (D023).
  `reference-v1` metadata now also counts the closure mask that MAT-02 had
  flagged.
- **Tooling only, no numerical effect.** A shell heredoc mangled C++ escape
  sequences in an edit script, which was then written to a file. One Python
  expression in the coefficient audit failed to parse and was rewritten. A
  self-test run of the V05-B checks preceded the application of their
  revision-1.5 update and failed as expected on the superseded injection.

## Review addendum (2026-09-25)

A completion review re-checked the item before its first commit. It was done
by the same collaborator, with three separate read-only code passes (solver,
benchmark library, analysis scripts). No independent reviewer is claimed.

**Re-verified without change:**

- Fresh `build/MAT-03-audit-{debug,release}` trees: 0 warnings, 20/20 CTests.
  Their source snapshot is identical to the evidence build's, so the
  fingerprint is still `1621d840…`.
- All 71 entries of the previous source manifest matched the working tree.
- Re-analysing the retained `run1` material suites reproduced the tracked
  summary exactly, apart from the input path.
- No solver, fixture or reduction defect was found that lets a V05/V06 limit
  pass when it should fail.

**Corrected:**

- **Purity scope (wording).** The revision-1.5 text said the version-1 limit
  was unchanged "wherever the amplitude is resolvable". It is unchanged only at
  states with `abs(a_n) >= 1e-4 peak`. The floor covers about 42% of the
  states, and between `2.2e-7` and `1e-4` of the peak it is looser than
  version 1 by up to about 450 times. Version 1 also exceeded `1e-9` at a few
  states above `2.2e-7` of the peak (at most `5.05e-9`), because the
  accumulated roundoff (about `1.7e-15` of the peak) is larger than one
  rounding. The specification, D025, the contract, this record and the backlog
  now state the scope. The decision and the pass stand. The validation plan's
  failure-handling rule now asks for this count.
- **NaN in the V05-B purity maximum.** `max(x, nan)` returns `x`, so a NaN in
  an off-centre line sample left the case passing. The suite still failed,
  because the structural audit rejects non-finite values. The reduction now
  fails any non-finite line or point sample, and its limit comparisons are
  written so that a NaN fails. A new self-test fault (NaN at state 400,
  `k=5`) passed the previous code and fails the corrected one.
- **Defaulting fixture report.** The audit read
  `fixture_max_plateau_error` with a default of `0.0`, the defect class found in
  the MAT-02 review. Material cases must now report it (V04 metadata predates
  it). Three new faults run on the real smoke output: a missing key, `2e-11`
  and NaN.
- **Evidence wording.** The S10 vacuum-stepper comparison and the S12
  time-step equalities hold by construction, now that every constructor
  shares the material kernel. The table above says so. The stepper-level
  bitwise P1 evidence is the manual V06-C reproduction.

`reference.closed_analysis` now has 2641 checks. After the changes, the
affected CTests (`closed_analysis` and the `material` tests) pass in both
audit trees, and the retained material run re-analyses to the same summary.

**Recorded, not changed:**

- `closed-v1 --suite smoke --steps 9` or more fails on the wave isolation
  guard. This is not documented in the CLI help.
- Metadata gaps:
  - `phi` is absent, and lossy cases write `omega_d: 0`.
  - V04 metadata lacks the `diagnostic_bytes` field that the contract lists
    for every case.
  - The metadata `tau_s` expression differs by association from the source's.
- `initialize()` builds a second per-cell map (162 MiB at `p=96`). This stays
  within the budget.
- `EdgeCoefficients` does not record its `dt`. Only the stepper, which uses a
  single time step, is safe.
- A vacuum dt/field spacing mismatch reports a material error message.

None of these affects a recorded value.

## Second review addendum (2026-09-25)

The owner asked for a review of the completed item. Three reviewers read the
solver, the benchmark library and the analysis scripts against this contract.
They worked in separate sessions of the same assistant, so this is still not an
independent human review. Two of them also planted deliberate bugs in scratch
copies to test whether the checks catch them.

**Re-verified without change:**

- Fresh `build/MAT-03-indep-review-{debug,release}` trees: 0 warnings,
  20/20 CTests. The source snapshot is identical to the evidence build's
  (`1621d840…`), and the benchmark and solver sources did not change afterwards.
- All 71 manifest entries matched the working tree before this addendum's
  edits.
- The fixture review re-derived every fixture and the six orderings. It checked
  the smoke output against the closed forms: `z` and `h` to `2e-15`, and the
  slab `f_d` to `4.4e-16`. The reference-v1 and V04 smoke CSVs are again
  byte-identical to the MAT-02 build.
- No solver, fixture or reduction defect was found that lets a recorded
  V05/V06 result pass wrongly.

**Corrected (analysis and tests only; no solver or benchmark source changed):**

- **V06-B monotonicity at every state.** The check
  `Q_(n+1) <= Q_n (1 + 1e-12)` was applied only where `Q_n > 0`; the
  specification requires it at every state. An invariant that reached zero and
  reappeared, with the balance intact, passed. It now fails, and a new
  self-test fault covers it. Every measured `Q_n` is positive, so neither case
  changes.
- **NaN handling.** A NaN could disappear from several case-level maxima
  (inactive lines, V05-B `R`/`T`) and from the geometry comparisons, leaving
  the case marked as passing. The suite still failed through the structural
  audit. Every maximum now keeps a NaN, every limit is written so that a NaN
  fails, and new faults cover a NaN inactive sample and a NaN time step. An
  empty orientation record now fails instead of crashing or passing vacuously.
- **V06-A H-line floor.** The analyzer used `0.25 A/eta`; the V01 floor the
  contract names is `0.5 A/eta`. The smallest measured H amplitude is
  `0.760 A/eta` (`lossy-xy-p96-sig0p1`), so no case changes.
- **Unexercised checks.** Removing any of these left the self-test passing:
  - the V05-B continuum `abs(R)`/`abs(T)` cap;
  - the V06-A phase cap;
  - the fit-residual limit;
  - the V05-A H amplitude;
  - the V06-B lower energy bound;
  - the V05-B second-plane (`p1b`) check.

  Each now has a fault. A mutation run removed or reverted each check and each
  correction above, 11 mutants in all, and the self-test failed on every one.
  The first version of the empty-orientation fault did not fail a mutant; it
  was strengthened.
- **S10 gaps.**
  - A table key that ignored `sigma` passed S10–S13, because in the modular
    map equal `eps_r,e` implies equal `sigma_e`. S10 now also checks a map with
    constant `eps_r = 4` and varying `sigma`, and a map with unrelated `eps_r`
    and `sigma`.
  - The stepper comparison could not fail, since every constructor shares the
    material kernel. S10 now compares the driven stepper, bit pattern for bit
    pattern, with a transcribed P1 step: the P1 kernels, then
    `E <- E - e_scale*(amplitude*J)`.
  - The first attempt used drive values that are exact binary fractions, and a
    reassociated source term still passed. With `0.7`/`-1.3` and amplitudes
    `0.3 + 0.7n` it fails.
  - Both source mutants (the `sigma`-blind key and the reassociated source)
    now fail S10. S10 has 9554 checks (previously 3022).
- **Golden generator.** The exact-divergence check was an `assert`, which
  `python -O` removes. It is now an explicit failure.
- **Contract text.** The contract now matches the code in these places:
  - the emitted metadata key names (`eps_r`, `sigma_S_per_m`, `edges`,
    `f_d_hz`, `f_c_hz`);
  - cell-count mismatches are rejected by the stepper, not by
    `EdgeCoefficients`;
  - the vacuum table is empty on grids with no update-range edges.

After the changes:
- Both review trees rebuild without warnings and pass 20/20.
- `reference.closed_analysis` reports 2654 checks.
- Re-analysing the retained `run1` material suites reproduces the tracked
  summary exactly, apart from the relative suite paths.

**Recorded, not changed** (any change would need a benchmark-source change and
a new evidence build):
- A fixture check that does not apply to a kind is written as `0`, which cannot
  be told apart from a measured zero.
- The pre-run divergence check cannot fail for the five version-1 fixtures:
  the fields are curls in a uniform medium, zero, or invariant along `b`. The
  slab eigen check, by contrast, discriminates.

The known metadata gaps in the first addendum remain.

## Hosted CI addendum (2026-09-25)

The first hosted run after the push (Ubuntu/GCC, Python 3.13, run 4 of
Validation, commit `6c74934`) built both configurations and passed 19 of 20
CTests in each. `reference.closed_analysis` failed in a V05-B self-test case.
No solver output or recorded measurement was involved.

**Cause.** The case built a zero record with an impurity of `+1e-300` at
`k = 4` and `-1e-300` at `k = 12` on the `N_c = 16` line. It assumed the pair
cancels exactly against `sin(pi k/N_c)`, which needs
`sin(pi/4) == sin(3 pi/4)` in binary64. The Windows runtime returns equal
values; glibc may round them one ulp apart. On Linux the TE_1 amplitude was
therefore a subnormal `~1e-317`, not zero. The reduction still rejected the
record, through the purity limit, but the test required the zero-amplitude
message.

**Correction** (self-test only):
- The zero-amplitude case now places the impurity at `k = 0`, where
  `sin(0) = 0` exactly on every platform.
- A second case keeps the near-cancelling pair, with a `1e-10` relative
  mismatch. It must fail through the purity limit on every platform.

A local run that shifted `sin(3 pi/4)` by one ulp reproduced the CI outcome for
the old pair. Both new cases gave the same result with either sine.

**Consequence for the evidence.**
- The part of `reference.closed_analysis` after this case has not yet run on
  Linux: the V05-C, V06-B and coefficient-table self-tests, and the smoke
  oracle.
- The remaining checks compare integers, apply `1e-12` tolerances, or compare
  the solver with itself, so none should depend on the platform's `sin`
  rounding.
- Hosted run 5 (`1d3f537`) ran them: Debug and Release pass 20/20 CTests on
  Ubuntu/GCC with Python 3.13, including the full `reference.closed_analysis`
  and the material smoke oracle
  ([run 5](https://github.com/sibuay/AntennaSim/actions/runs/36153028594)).
- `reference.closed_analysis` has 2655 checks.

## Limits

- Same-author review. The physical suites ran on one Windows/Clang machine.
  Hosted CI runs only the smoke-length reductions and the structural tests;
  Ubuntu/GCC passed them in run 5. No full physical suite has run on GCC.
- The validated material envelope:
  - homogeneous `eps_r = 4` eigenwaves on the V01 grids at `p=24/48/96`;
  - the node-averaged planar interface between vacuum and `eps_r = 4` for the
    TE_1 mode in the declared band and layout;
  - the TE slab cavity on three axes;
  - constant conductivity with `x <= 0.045` (`sigma` 0.01 and 0.1 S/m at
    `eps_r = 4`);
  - the closed-grid dissipation identity (`eps_r = 2.25`, `sigma = 0.01`).
- Constant `sigma` is not a loss-tangent model. Oblique or curved interfaces,
  subcell treatment, magnetic, dispersive or anisotropic media, larger `x`,
  open boundaries, ports and antenna quantities remain unvalidated.
- The production spectral path (MAT-04) does not exist yet. The V05-B
  transforms are the independent analyzer's.

## Decision

MAT-03 meets its fixed acceptance:

- S10–S13 pass.
- All twenty CTests pass in fresh Debug and Release trees without warnings.
- V05-A, V05-B (under specification revision 1.5, with the version-1 failure
  retained), V05-C, V06-A and V06-B pass from the clean Release build.
- V06-C reproduces V01–V03 at zero tolerance, with byte-identical smoke CSVs.
- V04 is re-run and reproduced at zero tolerance.
- The measured peak memory is within 2 GiB.

**MAT-03 is Done** within the stated envelope. P2 remains open. The next item
is MAT-04 (production spectral processing, V07).
