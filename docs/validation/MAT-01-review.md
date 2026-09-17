# MAT-01 — Closed-domain specification review evidence

Date: 2026-09-18. Decision: **MAT-01 complete; MAT-02 ready; P2 remains open.**
Scope: the [P2 method note](../methods/MAT-01-closed-domain-conventions.md),
the [V04–V07/S09–S14 specification](MAT-01-closed-domain-benchmarks.md), and
the [analytical audit](../../scripts/check_material_benchmarks.py) registered
as CTest `reference.material_specification`.

The same collaborator authored and reviewed this work. No second agent or
independent human reviewer participated. The closed-form discrete comparators
and the reduced-system oracle are independent of the future solver, but the
reviewer is not independent. The audit imports no production code and evolves
no three-dimensional field; it evaluates specification algebra and synthetic
signals only.

Identity: commit `2a0fd91` (`main`) plus this item's changes. No C++ source,
preset, fixture, tolerance, test executable, or analyzer of P1 changed; the only
build-system change registers the new Python audit. The
[MAT-01 manifest](MAT-01-source-sha256.txt) hashes the working-tree bytes of
the reviewed inputs and final records (CRLF checkout, as for REF-06).

## Completion matrix

| MAT-01 obligation (P1 gate breakdown) | Evidence / outcome |
| --- | --- |
| Method note for explicit PEC surfaces, interior and outer | E-edge mask semantics, grid-aligned box marking by exact index arithmetic, outer closure as the always-present special case, exact zeros, rejected sources, untouched H, implied surface charge, cost |
| Isotropic dielectric and constant-conductivity update with supported frequency scope | Per-cell `eps_r>=1`, `sigma>=0`, `mu0`; four-cell arithmetic edge averaging; Schneider 9.27–9.32 / 3.50–3.52 coefficients in a form that reproduces vacuum bitwise; constant `sigma` declared not a loss-tangent model; supported loss scope `sigma*dt/(2*eps)<=0.045` with the tabulated `x^2/3` decay error |
| Stability under materials | Eps-weighted dissipation identity `Q_(n+1)=Q_n-D_n`, `D_n>=0`, derived from the S05 adjoint identity; vacuum CFL bound retained and justified; `eps_r<1` rejected |
| Spectral processing conventions | `dt*sum w_n x_n exp(-2 pi i f t_n)` at native E/H times, rectangular and Hann windows, bin resolution, peak refinement, no implicit half-step shift, production/direct-sum agreement requirement |
| Records reviewed against FND-03 with exact sources | FND-03 conventions unchanged; Schneider chapters 3 (3.11, 3.12), 7 (7.6–7.8) and 9 (9.3, 9.7) rechecked from the extracted chapter text with section, equation, and printed-page references |
| V04–V07 fixtures, independent references, fixed tolerances with justification | V04-A/B/C, V05-A/B/C, V06-A/B/C, V07 items 1–7 with continuum references, closed-form discrete diagnostics, caps at 1.24–1.35 times the exact predictions, and `1e-9`/`1e-8`/`1e-11`/`1e-4` implementation limits |
| Resource budgets | Calculated per suite by the audit: 5,358,056,072 cell-steps, largest transient the `p=96` two-payload construction (2 x 489.380 MiB) within 2 GiB |
| Structural extensions of S01–S08 | S09–S14 with fixtures, independent enumerations, and thresholds |
| Synthetic/oracle analyzer coverage extensions | Per-benchmark fault-injection list and the oracle extension (mask, materials, lossy update, `D_n`) fixed before MAT-02 |
| Analytical audit script extended and passing | `check_material_benchmarks.py` passes standalone (Python 3.9.7, 19.3 s) and in CTest (Python 3.10.2, 14.2–14.7 s) in both configurations |

## Deterministic calculations executed

Environment: Windows 10 x64 (build 19045), AMD Ryzen 5 3600; Anaconda Python
3.9.7 for the standalone run, Python 3.10.2 under CTest; standard library only.
Command from the project root:

```powershell
python scripts/check_material_benchmarks.py
```

The audit produced the following **analytical predictions and synthetic
checks**, not solver measurements (full transcript reproduced by the command):

| Benchmark | Prediction / synthetic result | Fixed limit |
| --- | --- | --- |
| V04-A continuum errors, modes (1,1)/(2,1)/(1,2) | s=1: 8.926e-4 / 4.190e-3 / 2.080e-3; s=2: 2.230e-4 / 1.046e-3 / 5.196e-4; s=4: 5.573e-5 / 2.613e-4 / 1.299e-4 | 0.0052 / 0.0013 / 0.000325 |
| V04-A refinement orders | 2.000276 to 2.015857 | [1.8, 2.2] |
| V04-A `q=0.5` (1,1) errors x/y/z | 1.310e-3 / 2.246e-3 / 2.080e-3 | 0.0028 |
| V04-A synthetic estimator precision (frequency, amplitude, H relation, residual) | 1.1e-12; injected 3e-9 frequency, 3e-9 amplitude, H-sign and 1e-6 phase faults detected | 1e-11 synthetic; 1e-9 acceptance |
| V04-B lines below 2.27 GHz | 10 predicted, 8 required; minimum visible separation 12.0 bins (32768 states) and 6.0 bins (16384 states); pulse samples sum exactly to zero | >= 4 bins |
| V04-B synthetic identification | worst required-line offset 0.0002 / 0.0004 bin; relative height error 0.0010 / 0.0024; no spurious peak | 0.25 bin; 0.15; none |
| V05-A continuum errors `eps_r=4` | 2.443e-3 / 6.107e-4 / 1.527e-4; orders 2.000276, 2.000070; guards 23.5>18, 47.5>30, 95.5>56; `eta=188.365156706` ohm | 0.003 / 0.00075 / 0.0001875 |
| V05-B band-maximum `abs(abs(R_d)-abs(R_c))` | 4.717e-2 / 1.037e-2 / 2.513e-3 (`p=16/32/64`); `abs(R_c(f0))=0.344131`; `abs(R_d(f0))` 0.315939 / 0.337613 / 0.342531 | 0.06 / 0.0135 / 0.0034 |
| V05-B gated 1D oracle versus closed-form `R_d,T_d` | 1.23e-5 / 1.28e-5 / 1.31e-5; `abs(Im R_d)<=3.4e-16`; doubling back/far regions changed the gated series by 0 | 1e-4 |
| V05-C mode 1 (0.337001 GHz) errors | 2.981e-4 / 7.457e-5 / 1.865e-5; orders 1.998988, 1.999748 | 0.00038 / 0.000095 / 0.000024 |
| V05-C mode 2 (0.716293 GHz) errors | 4.402e-3 / 1.099e-3 / 2.748e-4; orders 2.001497, 2.000379 | 0.0055 / 0.0014 / 0.00035 |
| V06-A decay errors `sigma=0.01` / `0.1` S/m | 6.681e-6, 1.670e-6, 4.175e-7 / 6.689e-4, 1.671e-4, 4.176e-5 (equal to `x^2/3`, modulus identity exact to 1e-15) | 8.5e-6, 2.1e-6, 5.3e-7 / 8.5e-4, 2.1e-4, 5.3e-5 |
| V06-A phase errors | 2.445e-3, 6.112e-4, 1.528e-4 / 2.815e-3, 7.033e-4, 1.758e-4; final amplitudes 0.756–0.974 | 0.0035 / 0.0009 / 0.00022; floor 0.5 |
| V06 modal dissipation algebra | 24 exact-rational identities `Q_new-Q_old=-4x*Ebar^2` | exact |
| V06-B budget | `alpha*N*dt=12.7` over 2000 steps at `q=0.99`, `x=0.0064` | reported |
| V07 closed forms, native times, Gaussian, Parseval, FFT versus direct sum, Hann gain | worst discrepancy 4.59e-14 | 1e-12 |
| V07 two-tone peak offsets | 0.0007 and 0.0095 bin | 0.25 bin |

Two fixture defects were found by the audit before the specification was fixed;
neither concerns solver code:

1. With the spectral cutoff at 2.5 GHz the cavity line pair (1,2,4)/(1,1,5)
   near 2.31 GHz is only 1.56 bins apart and could not be identified separately.
   The cutoff was lowered to 2.27 GHz, and the second-resolution run at `s=2`
   was replaced by a truncated-record analysis of the `s=1` run, which
   demonstrates the resolution effect at one eighth of the cost.
2. The first interface layout (guide height `1.5 lambda0`, pulse width
   `0.25 f0`, short record) disagreed with the closed-form discrete reflection
   by 2.4e-2 at every resolution and its `abs(R)` error did not refine: pulse
   content near the TE cutoff propagated slowly and leaked across the time
   gate. The fixture now uses a `2 lambda0` guide (cutoff `f0/4`), a `0.15 f0`
   pulse, and a re-derived layout; two rejected variants (far region of three
   wavelengths with a 35-period record; 40-period record) reproduced wall echoes
   with errors of order one, confirming the echo timing and fixing the record
   length and gate as part of the fixture.

The audit also corrected its own pulse construction so that the differentiated
Gaussian samples cancel bitwise (`fsum` exactly zero) and widened the synthetic
precision requirement of the cavity estimator from `1e-12` to `1e-11` after the
866-state recurrence fit showed `1.5e-12` on the finest synthetic case; the
`1e-9` acceptance limits are unaffected.

## Clean-build and infrastructure regression

Fresh `build/MAT-01-release` and `build/MAT-01-debug` trees (absent before
configuration) with the project-local LLVM-MinGW 20250613 / Clang 20.1.7,
CMake/CTest 3.31.10 and Ninja; verbose build logs show `-std=c++20`, the
warning set, `-fno-fast-math` and `-ffp-contract=off` on every target and no
compiler warnings. Commands as at REF-06 with `B=build/MAT-01-{release,debug}`.

| Run | Configure | Build | CTest (after the final script revision) | Measured CTest time |
| --- | --- | --- | --- | --- |
| Fresh Release | Pass | Pass, no warnings | 13/13 pass; `reference.material_specification` 14.15 s | 28.14 s (first run 28.32 s) |
| Fresh Debug | Pass | Pass, no warnings | 13/13 pass; `reference.material_specification` 14.67 s | 39.41 s (first run 38.95 s) |

The thirteen tests are the twelve of REF-06 plus `reference.material_specification`
(labels `reference_structural;analytical_audit`, timeout 300 s). The Release
executable's SHA-256 is `63635f83…`; its source-content fingerprint is
`a9bee75b480ebddbfae42212ebcb34cb39a7e5b311ef464483b4955bbbdec598` (SHA-256 of
the LF-normalized `source-snapshot.txt`), which differs from REF-06's
`f9ddf4f2…` only because `CMakeLists.txt` is a snapshot input; no compiled
source changed. Retained ignored logs:
`build/MAT-01-{release,debug}-{configure,build,test,test-final}.log`.

Physical P2 benchmarks were **not run: no PEC mask, material array, or spectral
path exists**. The V01–V03 suites were not re-run for this item because no
solver, fixture, or analyzer changed; the REF-06 clean-build reproduction
remains the current physical evidence.

## Decision and handoff

D018 fixes the P2 conventions and the version-1 V04–V07 limits before any P2
code. The supported validation envelope is unchanged (axis-aligned vacuum
propagation and closed-grid stability); this review adds no numerical
capability and closes no phase gate.

Next exact action: **MAT-02**. Implement the E-edge PEC mask (outer closure plus
grid-aligned boxes) with its contract note; add S09; add the `closed-v1`
`cavity`, `cavity-spectrum`, and `pec` suites with the exact eigenmode fixture,
the antisymmetric pulse, and per-state exterior/surface maxima; write the
independent analyzer with the V04 reductions and the synthetic fault coverage
listed in the specification; then run V04 from a clean Release build. Keep the
vacuum path bitwise identical and all thirteen CTests and the V01–V03 suites
passing. No calendar schedule, automation, publication, or external service
changed.
