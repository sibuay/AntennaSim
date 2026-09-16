# REF-05 — Reference propagation, impedance, stability and refinement measurements

2026-09-16. **REF-05 status: see the decision at the end.** This is the first
measured physical evidence for V01–V03. Same collaborator implemented, ran and
reviewed the work; no independent reviewer is claimed. The
[measurement contract](../methods/REF-05-measurement-contract.md) fixed the
reductions and their validation before the suites ran; the unchanged
[FND-04 v1 specification](FND-04-reference-benchmarks.md) supplies every limit.

## Snapshot and method

Solver, benchmark and CLI sources are unchanged since commit `b98bc4c`; this
item adds `CMakeLists.txt` test registration, the CI artifact path, and three
analysis scripts. The built executable's source-content fingerprint is
`f9ddf4f296e7858c33974167579f8423db73d51e36601589e2f58f26bc222f5c` (SHA-256 of
the CMake `source-snapshot.txt` text with LF newlines; on Windows the written
file uses CRLF, so normalize before recomputing). The
[source manifest](REF-05-source-sha256.txt) hashes the checked files.

Evidence types are labelled as in the validation plan: the continuum comparator
`c0`, `eta0` and the h^2 refinement expectation are the independent references;
the discrete dispersion frequency is an analytical diagnostic; the
enlarged-domain and oracle comparisons are internal-consistency checks.

## Reduction validation (before physical acceptance)

`reference.analysis_reductions` passes in Debug and Release:

| Check | Result |
| --- | --- |
| Synthetic V01/V02 on all 36 v1 geometries | Pass; continuum error equals the analytical prediction within 8.9e-16; discrete and impedance deviations ≤ 9.7e-16 |
| Injected faults (frequency, amplitude, sign, direction, contamination, missing sample, step count, geometry, mixed times, continuum, refinement order, enlarged difference) | All detected |
| Synthetic V03 traces, four q/excitation combinations | Pass; 20 blocks of 1,000 states; drift 2e-8, bound violation, NaN and short trace detected |
| Prescribed native line, resource budget, failure retention (analyzer revision 2) | A consistently relocated line is rejected; missing/unmeasured/over-budget/nonzero-status resource records fail; a corrupt metadata file still yields `metrics.json`/`report.md` with a provenance failure |
| Independent pure-Python oracle versus production smoke stability diagnostics | `U`, `Q`, six maxima and six centre probes agree within 1e-12 relative at states 0–2 for both q=0.99 cases, including the driven current updates |
| Two-step propagation smoke case through the production probes | Continuum error 0.00120829246, discrete 6.7e-16, impedance 1.3e-15 |

The oracle transcribes the six FND-03 component equations directly; the
benchmark library uses axis-permutation differences; the solver uses its own
kernels. Agreement across three separately written forms supports interpreting
the production `Q` trace as the derived invariant.

## V01/V02 — propagation, amplitude, impedance and refinement (36 cases)

Clean Release build, serial execution through `scripts/run_reference_benchmarks.py`.
All 36 cases pass every v1 limit. Measured values are identical across the six
axis/polarization orderings at the printed precision.

| Configuration | N | Continuum error `abs(omega_m/(k c0)-1)` | Cap | Analytical prediction | Discrete error | Amplitude E / H | Residual E / H | Inactive lines | Complex Z error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p=24 primary (6) | 3 | 0.00120829246 | 0.0015 | 0.00120829246432 | 4.4e-16 | 6.7e-16 / 8.9e-16 | 1.5e-14 / 1.5e-14 | 0 | 1.3e-15 |
| p=48 primary (6) | 6 | 0.000301257334 | 0.000375 | 0.000301257333745 | 6.7e-16 | 4.4e-16 / 6.7e-16 | 2.3e-14 / 2.2e-14 | 0 | 1.0e-15 |
| p=96 primary (6) | 12 | 0.0000752634590 | 0.00009375 | 0.0000752634589699 | 8.9e-16 | 6.7e-16 / 7.8e-16 | 6.4e-14 / 5.8e-14 | 0 | 1.1e-15 |
| p=24 enlarged (6) | 3 | 0.00120829246 | 0.0015 | 0.00120829246432 | 7.8e-16 | 6.7e-16 / 7.8e-16 | 2.3e-14 / 1.9e-14 | 0 | 1.6e-15 |
| p=24 q=0.5 (6) | 6 | 0.00243512004 | 0.003 | 0.00243512003878 | 2.2e-16 | 6.7e-16 / 6.7e-16 | 1.1e-14 / 1.2e-14 | 0 | 9.3e-16 |
| p=24 cubic (6) | 4 | 0.00192599561 | 0.003 | 0.00192599561389 | 2.2e-16 | 6.7e-16 / 6.7e-16 | 1.3e-14 / 1.3e-14 | 0 | 9.5e-16 |

Limits: discrete, amplitude, residual and inactive ≤ 1e-9; complex impedance
≤ 1e-8. Fit condition numbers stayed below 2 and every line had p samples at
every state. The signed final impedance is `+376.730313` ohm for the (x,y),
(y,z), (z,x) orderings and `-376.730313` ohm for (x,z), (y,x), (z,y), matching
`s*eta0` with imaginary parts at most 2.1e-13 ohm. The measured frequencies
are positive with phase advance about 0.597 rad on the primary sequence.

Refinement, for every one of the six orderings: continuum errors
0.00120829246 > 0.000301257334 > 0.0000752634590, observed orders 2.00390143
and 2.00097486, inside [1.8, 2.2] and equal to the analytical prediction
(2.003901430, 2.000974863) at the printed precision.

Enlarged-domain comparison, each ordering: integer shifts of 48/32/24 cells in
the propagation/electric/remaining axes, 576 of 576 samples matched with
coordinates shifted by exactly 2λ, maximum normalized difference 2.82e-14
against the 1e-10 limit. The dependency guard passed before allocation.

Interpretation: the measured continuum phase-speed error equals the analytical
Yee dispersion prediction to nine digits because the fixture is the discrete
eigenwave; the physical content of the pass is that this error is below the
h^2-scaled caps at three resolutions and refines at second order with the
expected constant. It does not establish oblique-incidence, broadband or
source-launched accuracy.

## V03 — long-time stability (4 cases)

All four cases pass. Diagnostics were recorded at every state; no nonfinite
value occurred; `Q_0=U_0` held exactly for the initial-field cases and the
driven cases started from exactly zero diagnostics.

| Case | Steps | n_ref | U_ref (J) | Q_ref (J) | max `abs(Q_n-Q_ref)/Q_ref` (state) | min / max `U_n/U_ref` | Bound `(1+q)/(1-q)` | Max source-free `abs(E)` V/m / `eta0*abs(H)` V/m |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stable-q50-initial | 20000 | 0 | 6.7316e-15 | 6.7316e-15 | 5.86e-16 (8623) | 0.7803 / 1.4785 | 3 | 1.691 / 1.627 |
| stable-q50-driven | 20008 | 8 | 3.1897e-18 | 2.3496e-18 | 4.92e-16 (2842) | 0.7111 / 1 | 3 | 0.03158 / 0.03536 |
| stable-q99-initial | 20000 | 0 | 6.7316e-15 | 6.7316e-15 | 1.29e-15 (2905) | 1 / 4.2629 | 199 | 2.655 / 2.439 |
| stable-q99-driven | 20008 | 8 | 9.1971e-20 | 3.9690e-20 | 1.21e-15 (1283) | 0.5436 / 1 | 199 | 0.005454 / 0.005194 |

The invariant limit is 1e-8; the measured drift is seven orders below it and
below the planning-level 1e-12 arithmetic scale, consistent with compensated
summation of a quantity that is exactly conserved in exact arithmetic. The
lower and upper `Q` bounds relative to `U` were never violated. Each case has
20 complete 1,000-step source-free blocks; the block maxima of the invariant
error are 3.3e-16 first / 4.9e-16 last (q=0.5 driven), 3.5e-16 / 5.9e-16
(q=0.5 initial), 1.1e-15 / 4.5e-16 (q=0.99 driven) and 8.2e-16 / 8.2e-16
(q=0.99 initial): no secular growth. The q=0.99 initial-field case shows the
expected large excursion of the non-conserved `U` (up to 4.26 times its start,
field maxima 2.66 V/m from a 1 V/m shape) while `Q` is constant; this is the
modified-energy behavior near the Courant limit, not an instability. During
the driven interval the magnetic maxima (up to 2.2e-5 A/m at q=0.99) exceed
their source-free values, as expected for a pulse that is later radiated into
the closed box. Centre-probe values remained finite with normalized maxima
0.83 and 1.48 (initial cases) and 0.015 and 0.0027 (driven cases).

Interpretation: the reflecting closed grid at the declared spacings and
durations produces no late-time growth for either Courant fraction, with or
without the impressed solenoidal pulse. Passing supports only these lossless
fixtures and 20,000-step observation windows.

## Resources and environment

Measured with `scripts/run_reference_benchmarks.py` (psutil 5.8.0 peak working
set sampled every 50 ms; this is process resident memory, not a heap proof) and
the CLI's per-case elapsed time. Both suites ran serially with no concurrent
build.

| Suite | Cases | Elapsed | Peak working set | Declared limit |
| --- | --- | --- | --- | --- |
| propagation | 36 | 606.45 s | 1,031,151,616 bytes | 2,147,483,648 bytes |
| stability | 4 | 158.58 s | 5,152,768 bytes | 2,147,483,648 bytes |

| Case group | Per-case elapsed |
| --- | --- |
| p=24 primary / q=0.5 / cubic / enlarged | 0.56–0.73 s / 0.80–0.84 s / 1.92–2.00 s / 6.11–6.23 s |
| p=48 primary | 6.40–6.66 s |
| p=96 primary | 84.26–86.34 s |
| stability, each 20,000/20,008 steps with per-state diagnostics | 39.4–39.9 s |

The p=96 peak corresponds to the two 489.380 MiB field payloads present during
construction; the observed 983 MiB is consistent with the budgeted transient.
These are observations on the checked-access reference kernel, not a
performance baseline.

Environment: Windows 10 x64, AMD Ryzen 5 3600, project-local LLVM-MinGW
20250613 / Clang 20.1.7, CMake/CTest 3.31.10, strict binary64 without fast math
or contraction; analysis with Anaconda Python 3.9.7 and psutil 5.8.0. The
compiler ran inside the ordinary session sandbox this time; the earlier
approved-execution constraint did not recur. The 12-test CTest suite passed
from a clean Release build (13.39 s) before the physical runs and from a clean
Debug build (23.81 s) afterwards; after the analyzer revision 2 both suites
were rerun incrementally and passed (Release 15.80 s, Debug 25.97 s), with
no compiler warnings in any build.

## Reproduction

From the repository root, choosing fresh output locations:

```powershell
./scripts/build.ps1 -Configuration Release
python scripts/run_reference_benchmarks.py --app build/windows-local-release/antennasim.exe --output build/evidence/REF-05/run1 --runtime-path .tools/llvm-mingw-20250613-ucrt-x86_64/bin
python scripts/analyze_reference_benchmarks.py --input build/evidence/REF-05/run1 --output build/evidence/REF-05/analysis
python scripts/check_reference_analysis.py --app build/windows-local-release/antennasim.exe --output-root build/evidence/REF-05-audit
```

The tracked compact record is [REF-05-analysis-summary.json](REF-05-analysis-summary.json)
(the analyzer's `metrics.json`); raw probes, diagnostics, per-state fit traces
and block maxima remain under the ignored `build/evidence/REF-05/` tree.

## Failures, limits, and next action

- No physical, structural, or artifact check failed; no v1 tolerance or fixture
  changed. The reduction validation ran on both configurations before the
  physical results were interpreted.
- Review of the first analyzer revision found three evidence-acceptance gaps:
  probe lines were not checked against the prescribed v1 indices (a line moved
  consistently within the uniform plateau passed, and only the enlarged
  comparison caught it for p=24 primary cases), the 2 GiB memory budget was
  recorded but never enforced by the runner or analyzer, and a corrupt
  `metadata.json` crashed the analyzer's provenance pass before any report was
  written. Revision 2 adds the prescribed-line check, aborts a suite whose peak
  working set exceeds the budget and fails the analysis when a suite's status is
  nonzero or its peak is unmeasured or over budget, and records unreadable
  metadata as a provenance failure while still writing all outputs. Each gap has
  a fault-injection check in the self-test (97 synthetic checks). The retained
  run1 artifacts were re-analyzed under revision 2 with the same numerical
  results and an additional passing `resources` suite entry; the tracked summary
  is that re-analysis.
- Three defects in the new analysis/self-test code were corrected before any
  physical run: the analyzer split the `half-q` case name at its hyphen; two
  synthetic fault injections (continuum perturbation, enlarged difference) were
  below their limits; and the synthetic q=0.99 energy swing crossed the `(1+q)`
  bound. These were test-construction errors, not solver findings.
- Measured values are identical across the six axis/polarization orderings at
  the reported precision. This is an observation about symmetric arithmetic in
  the permuted fixtures, not a requirement.
- Limits: same-author review; physical suites ran on one Windows/Clang machine
  while hosted CI runs only the smoke-length reductions; the fixture is the
  axis-aligned discrete eigenwave in vacuum inside a reflecting box, so
  oblique, broadband, source-launched, PEC-resonance, material, open-boundary
  and antenna accuracy remain unvalidated; V03 supports only the declared
  lossless grids and durations.

Decision: **REF-05 complete.** C03 has its first measured physical report and
C04 begins. P1 remains open until REF-06 records the gate review against the
Phase 1 exit criteria and the supported limits.
