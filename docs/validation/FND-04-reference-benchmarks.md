# FND-04 — Initial reference benchmark specifications

Version 1, 2026-09-05. **Author-reviewed; thresholds fixed for this version.**
No physical benchmark has run and no accuracy is established. This contract
resolves O003 for P1; [review evidence](FND-04-review.md) records its limits.
The implementation sequence remains REF-01 through REF-05 after FND-05 passes.

## Basis and scope

Use [FND-03](../methods/FND-03-yee-conventions.md) verbatim for SI constants,
binary64, array locations, curl signs, current units, time levels, and
`zero_tangential_e` closure. All cases are uniform, homogeneous vacuum, scalar
CPU, without material loss. Three-dimensional storage and updates are required.

Primary references rechecked on 2026-09-05:

- Schneider, *Understanding the Finite-Difference Time-Domain Method*,
  [chapter 7](https://eecs.wsu.edu/~schneidj/ufdtd/chap7.pdf), sections 7.2–7.5,
  especially equations 7.33–7.39 and 7.45–7.46: continuum/discrete harmonic
  dispersion and impedance. Here k is prescribed and omega is solved on the
  physical branch, rather than prescribing omega and solving for k.
- Schneider, [chapter 9](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf), section
  9.3 and equation 9.53: 3D placement, curl updates, unequal-spacing CFL bound.

The fixture construction, measurement definitions, energy derivation, error
budgets, and thresholds below are project derivations/decisions. They are not
published accuracy guarantees. The independent continuum comparators are
`c0=299792458 m/s` and `eta0=mu0*c0=376.730313412030... ohm`, using FND-03's
pinned constants. Comparisons to the discrete formula separately diagnose the
implementation. A match to that formula alone does not pass V01.

## V01/V02 shared fixture

Define roles a (propagation axis), b (electric axis), c (remaining axis). Run
all six ordered pairs `(a,b)=(x,y),(x,z),(y,x),(y,z),(z,x),(z,y)`. Let u and v
be their positive Cartesian unit vectors and `w=u cross v`; w can be negative.
The stored magnetic component sign is `s=w dot e_c`. Use local coordinates
`(r_a,r_b,r_c)` that are positive along the three Cartesian axes, even if w is
negative. Thus no coordinate reflection is hidden in the permutation.

| Parameter | Fixed value |
| --- | --- |
| Wavelength / nominal continuum period | lambda=0.3 m; T=lambda/c0 |
| Electric amplitude | A=1 V/m |
| Domain lengths in roles (a,b,c) | (3,3,4)*lambda; origin zero |
| Mesh sequence p=lambda/d_a | 24, 48, 96 |
| Spacings (d_a,d_b,d_c) | (1,1.5,2)*lambda/p |
| Cell counts (N_a,N_b,N_c) | (3p,2p,2p) |
| Step / duration | dt=q*dt_max, q=0.99; N=floor(0.1*T/dt); evolve N full steps |
| Initial / imposed excitation | Analytic curl fixture below at E^0 and H^(-1/2); J=0 throughout |
| Boundary | FND-03 zero tangential E; initial normal H=0 |
| Recorded states | n=0 through N inclusive; native E and H times, without interpolation |

The frequency and discrete wave number for these axis-aligned cases are

```text
k = 2*pi/lambda
K = (2/d_a)*sin(k*d_a/2)
omega_d = (2/dt)*asin(c0*dt*K/2)
E_interior(r,t) = v*A*cos(k*r_a - omega_d*t)
H_interior(r,t) = w*(A/eta0)*cos(k*r_a - omega_d*t)
```

Initialization uses omega_d to create a single discrete travelling harmonic
in the measurement region. E is evaluated at t=0 and H at t=-dt/2. Continuum
dispersion error remains measurable as `omega_measured/(k*c0)-1`. This is a
controlled eigenwave experiment, not a broadband launch or antenna feed test.

### Compatible finite-box initialization

A plane wave simply clipped on the walls violates the initial divergence
contract. Instead generate it as discrete curls of compactly supported
potentials, independently of the production update functions.

For any potential location, define its minimum distance to either face along
axis j in cell units as `dwall_j=min(r_j/d_j, N_j-r_j/d_j)`. Set

```text
m_j = min(1, max(0, (dwall_j-2)/2))
M(r) = m_x*m_y*m_z
P(r,t) = -w * (A/K) * M(r) * sin(k*r_a-omega_d*t)  [V]
Q(r,t) =  v * (A/(eta0*K)) * M(r) * sin(k*r_a-omega_d*t)  [A]
E^0 = curl_backward P(r,0)
H^(-1/2) = curl_forward Q(r,-dt/2)
```

P has H-component locations, Q has E-component locations. `curl_backward`
is the H-to-E curl in FND-03 without dt/epsilon; `curl_forward` is the ordinary
E-to-H curl, i.e. the negative of FND-03's H increment without dt/mu. Compute
interior E curls and set constrained tangential E to exactly zero; the collar
already makes their full curls zero. Set potential samples outside the domain
to zero only in the independent fixture generator if needed for a boundary
identity check; the solver itself never reads ghosts.

The central plateau gives the stated harmonic since the centered difference
of sin is K*cos and `u cross w=-v`. The two-cell zero collar ensures initial
normal H and tangential E are zero. The curl construction gives zero discrete
divergence (up to roundoff) at interior E-divergence nodes and all H-divergence
cell centers. Surface charge at a reflecting wall is not tested by an exterior
vacuum divergence stencil. The taper region contains other fields/modes; those
are excluded from the propagation measurements, not treated as a plane wave.

REF-04 must check these initial identities and the interior analytic samples
before calling the solver. The generator may share constants and location
metadata, but must not call the production curl/update/diagnostic functions.
Retain raw native initial samples in the evidence.

### Probes and exact discrete isolation

For each of the six components, record one native line using axial indices
`i_a=p,...,2p-1`, at transverse indices `i_b=N_b/2`, `i_c=N_c/2` (permuted
into x/y/z storage). Add that component's native half offsets to obtain its
actual coordinates. Different components need not share the same transverse
physical point: the reference plateau is uniform there. Store component,
indices, coordinates, time, and value, including the initial H negative time.

Every line point is at least `p-0.5` cells from each outer face. For the
conservative dependency proof, one half update traverses at most one cell
coordinate per axis, so N complete H/E steps traverse at most 2N cells in
each axis. Reserve six more cells for the mask transition, the initial curl
footprint, and staggering. Require **p-0.5 > 2N+6** for every requested case
and native component before allocation/execution. This encloses the full
backward dependency cone in the uniform potential plateau. It covers all six
faces and contamination launched at startup, not only an axial return time.
It is deliberately larger than the minimal Yee dependency radius.

Also run all six p=24 cases in an enlarged box: add 2*lambda to each side,
giving role lengths (7,7,8)*lambda and counts (7p,14p/3,4p). Shift the original
wave origin and probes by 2*lambda in each Cartesian axis. Use the same dt,
steps, and phase relative to the shifted original origin. The guard must pass;
matching samples after the origin shift must differ by at most 1e-10 in E/A
and eta0*H/A. This checks the fixture and proof implementation. Passing the
size comparison cannot excuse a failing dependency guard.

## V01 — Propagation, amplitude, and refinement

At each recorded E time n*dt, independently fit the active electric line to
`F_i = a_n*cos(k*r_a,i) + b_n*sin(k*r_a,i)` by a two-column least-squares
solve using the actual native positions. Define `C_n=a_n+i*b_n`. Do not fit k
or frequency to a preselected dispersion answer. The spatial k is the fixture
input; the temporal phase change is measured from the evolved samples.

Use `omega_m=Arg(C_N/C_0)/(N*dt)`. The expected phase is positive and below pi
(about 0.597 rad on the primary sequence), so the principal branch is unique.
Require positive omega_m. At every time, require a fit-column condition number
below 2, `abs(C_n)>=0.5*A`, and at least p samples; failure invalidates the
measurement and fails the case rather than dropping samples. No temporal FFT,
window, frequency bin, zero-crossing E/H division, or source-transient removal
is involved. Measure the final phase independently of the initializer's omega_d.

| Metric | Required limit |
| --- | --- |
| Continuum relative phase-speed error `abs(omega_m/(k*c0)-1)` | p=24: 0.0015; p=48: 0.000375; p=96: 0.00009375 |
| Discrete relative frequency error `abs(omega_m/omega_d-1)` | <=1e-9 |
| Active E fitted amplitude `abs(abs(C_n)/A-1)` | <=1e-9 at every recorded time |
| Active line fit residual, max absolute error divided by A | <=1e-9 |
| Inactive electric / magnetic line samples | max(abs(E)/A, eta0*abs(H)/A)<=1e-9 |
| Refinement | positive continuum errors decreasing strictly; both log2(error_p/error_2p) in [1.8,2.2] for every axis/polarization |

Budget: the independent dispersion relation predicts relative errors
0.00120829246432, 0.000301257333745, and 0.0000752634589699. The leading term
is `(1-(c0*dt/d_a)^2)*(k*d_a)^2/24`; exact evaluation predicts orders
2.003901430 and 2.000974863. The continuum caps scale with h^2 and allow about
24 percent margin over the exact predictions. The short observation time
adds no frequency-bin uncertainty because phase is recovered spatially.
The 1e-9 discrete/amplitude limits are implementation correctness budgets,
many orders above the ~1e-15 synthetic fitting residual yet far below the
smallest physical error (~7.5e-5). They are not attainable accuracy claims
for arbitrary waves. Reject zero/negative or noise-floor refinement errors;
investigate rather than declaring infinite order.

Sensitivity suite at p=24, for all six axis/polarization combinations:

- Set q=0.5 with the same physical geometry/mesh and N=floor(0.1*T/dt).
  This gives six steps, and the guard still passes. Expected continuum error
  is 0.00243512003878; require <=0.003 and all other per-case limits above.
  Smaller dt at fixed spatial k can increase this scheme's phase-speed error;
  do not require time-step reduction to improve this observable.
- Use cubic spacing lambda/24 with original physical lengths, counts
  (72,72,96), q=0.99 and four steps. Expected error is 0.00192599561389;
  require <=0.003 and the same discrete, amplitude, and isolation limits.

These plus the enlarged runs give 36 configurations total. Axis-aligned waves
do not establish oblique-wave accuracy; mixed derivatives and component signs
also require the structural suite below. Oblique and broadband accuracy are
outside the version-1 propagation claim.

## V02 — Signed vacuum impedance at native events

Reuse all 36 V01 configurations and their output; no separate simulation.
Fit active E and the signed Cartesian H component separately using their
own axial coordinates as above. At state n, their times are n*dt and
(n-1/2)*dt. Define corrected coefficients

```text
CE = fit_E * exp(-i*omega_m*n*dt)
CH = fit_H * exp(-i*omega_m*(n-1/2)*dt)
Z = CE/CH
Z_reference = s*eta0,  where s=(u cross v) dot e_c
```

Use V01's measured omega_m, not omega_d, for the phase translation. Take each
sample's recorded time, including n=0; verify the timestamp contract separately.
There is no spatial averaging attenuation: each fit uses the native coordinate
and shifts only its harmonic coefficient to a common phase origin.

At every state require `abs(fit_H)>=0.5*A/eta0`, condition number below 2,
and p native samples. Missing/weak/ill-conditioned data fail the case. Require
`abs(Z/(s*eta0)-1)<=1e-8` as a **complex** relative error, plus magnetic fitted
amplitude error <=1e-9 and max H fit residual normalized by A/eta0 <=1e-9.
Wrong signs and quadrature errors must fail, even if abs(Z) is correct.

For axis-aligned vacuum waves the discrete relation gives amplitude ratio
mu0*Omega/K=eta0, so there is no spatial-discretization impedance budget here.
The 1e-8 allowance covers two 1e-9 fitted coefficient errors and translating
the half-step offset using a frequency measured to 1e-9. Pinned constants
eliminate rounded-377-ohm error. The synthetic audit checks both signs and
both propagation directions at native offsets/times; it does not exercise
the future production probes. Report the raw coefficients, corrected complex
ratio, and residuals, not just a magnitude or pass flag.

## V03 — Stability and input policy

### Long-time fixtures

Use cells (12,14,16), spacings (0.01,0.015,0.02) m and the same vacuum closure.
Run q=0.5 and q=0.99, each with two excitations, for four cases. No observation
region is isolated from the walls here: this tests the closed discrete update,
not free-space radiation or validated PEC resonances.

Define an H-located potential at each component/index as
`P_j=d_min*R_j V`, where
`R_j=((17*i+31*j_index+43*k+13*component_id) mod 101 - 50)/50`, with
component_id=(0,1,2) for (x,y,z). Set P exactly zero wherever any face distance
is <=2 cells. Form the E-edge array `F=curl_backward P` and normalize all its
entries by the largest absolute entry, which must be nonzero. F is now a
dimensionless, boundary-compatible discrete-divergence-free shape. This fixed
integer formula excites short and long spatial scales without a random seed.

1. Initial-field case: E^0=(1 V/m)*F, H^(-1/2)=0, J=0; run 20,000 full steps.
2. Driven case: zero initial fields; for update n=0,...,7 prescribe
   `J^(n+1/2)=(0.01*epsilon0*(1 V/m)/dt)*F*sin(pi*(n+1/2)/8)` A/m^2.
   Thereafter J=0; run 20,008 steps total. The source is an imposed compact
   solenoidal current, with div J=0 and rho=0 in the interior. It is not a
   lumped feed or port. Reference the source-free diagnostics to state n=8,
   after the last driven update; verify the current sign separately below.

### Diagnostic and derivation

Use dV=dx*dy*dz. Define the weighted E inner product with half weights for
each transverse boundary coordinate (quarter at two-coordinate intersections),
and H with half weights for its normal boundary coordinate. All weighted
boundary samples are constrained zero; all unconstrained samples have weight
one. Report the weights explicitly instead of counting a collocated energy
on cell centers. Sum in binary64 using compensated summation.

With `C E=curl_forward E` and `C* H=curl_backward H`, zero tangential E gives
the discrete summation-by-parts identity `<E,C*H>=<CE,H>` under those weights.
The no-source step is Hplus=Hminus-dt/mu0*CE, then
Enew=E+dt/epsilon0*C*Hplus. Its modified energy invariant is

```text
U_n = dV/2 * [epsilon0*<E^n,E^n> + mu0*<Hminus,Hminus>]
Q_n = dV/2 * [epsilon0*<E^n,E^n> + mu0*<Hminus,Hplus>]
    = U_n - dV*dt/2 * <Hminus, C E^n>
```

Hplus in Q is the hypothetical next half-step from the same E^n, without
advancing state. An independent diagnostic can compute the last expression
including at the final state. Do not use E^(n+1) with H^(n-1/2). The adjoint
identity cancels terms on substituting both update equations, giving
Q_(n+1)=Q_n in exact arithmetic. Also
`dt*c0*||C||/2 <= q` implies `(1-q)*U_n <= Q_n <= (1+q)*U_n`.
This bounds a positive invariant for q<1 while allowing U_n to oscillate.
It does not assert conservation of a physical collocated energy estimate.

At every state from reference n_ref (0 or 8) through final, require finite
fields and diagnostics, Q_ref>0, U_ref>0, and

```text
abs(Q_n-Q_ref)/Q_ref <= 1e-8
U_n/U_ref <= ((1+q)/(1-q))*(1+1e-8)
Q_n >= (1-q)*U_n - 1e-8*Q_ref
Q_n <= (1+q)*U_n + 1e-8*Q_ref
```

Record max normalized invariant error and its step, min/max U/U_ref, first
non-finite sample if any, maximum absolute field/component, source cutoff,
and block maxima for each consecutive 1,000 source-free steps. Save diagnostics
every step (20,001 states after cutoff inclusive), not full field volumes.
The energy bound also bounds each field sample by its positive norm weight;
it is stronger than merely checking NaNs. No requirement for monotone U is used.

Tolerance justification: 20,000 steps at ~1e-16 binary64 precision gives a
baseline accumulated arithmetic scale around 1e-12 before conditioning and
stencil constants; the worst allowed q increases norm conditioning by at most
199. Compensated sums keep volume reductions from dominating. 1e-8 leaves
room above that planning budget while exposing secular growth. This is a
reviewed error budget, not a rigorous floating-point bound. Failures require
investigation and preserved outputs. Passing these finite tests supports only
the declared lossless grids/durations, never unconditional stability for new
materials/boundaries or arbitrary run lengths.

### CFL and invalid-input checks

Exercise both cubic and unequal spacing, with an independent dt_max calculation.
The following tests must be executable under the future `reference_structural`
CTest label, without running an unstable time integration:

- Default q=0.99 and q=0.5 produce positive finite dt with relative error <=
  5e-15 to the independent formula; positive `q=1-2^-20` is accepted for a
  one-step finite smoke check, without a long-time claim at that fraction.
- Reject q=0, negative, 1, >1, NaN and infinity. Explicit dt, if offered, follows
  the FND-03 strict dt<dt_max policy: reject equality and the next binary64
  value above, accept a representable value below. Do not silently clamp.
- Reject each non-finite/non-positive spacing, fractional/negative/0/1 cell
  counts, zero/fractional/negative step counts, unsupported material/boundary,
  incompatible initial wall data, out-of-range probe/source, boundary source,
  and non-finite field/current samples. Check all axes/components, not one.
- Exercise checked size_t addition/product/byte overflow and max_size limits
  before allocation; use limit-derived inputs, without attempting huge memory
  allocations. Check denormal/extreme spacings and run durations that cause
  zero/non-finite coefficients, lengths, coordinates, or repeated/non-finite
  timestamps. Reject unrepresentable cases with a reason.
- Inject a non-finite update result in a controlled test; the run must fail
  with step/component/index and no successful result artifact. Malformed CLI
  numbers fail before conversion to unsigned storage. Invalid-input tests
  assert errors and absence of successful results, not a particular prose text.

## Structural acceptance specification

These are required even when V01–V03 pass. They prevent a single analytic
fixture from masking errors. Use independent small-grid enumerations/formulas,
never the production operator as its own expected answer.

| ID / owner | Fixture and assertion | Threshold |
| --- | --- | --- |
| S01 / REF-01–02 | Cells (2,2,2), (2,3,4), (5,4,3); six extents, native positions, contiguous unique offsets, every first/last valid index, invalid index in each axis, all stencil reads; unequal spacings (2,3,5) m | Integer counts/offsets exact; coordinates exact for these binary64-representable fixtures |
| S02 / REF-02–03 | Enumerate all faces/edges/corners; constrained E is the union of transverse walls; initial normal H zero and remains zero; unconstrained samples evolve in a compatible nonzero fixture | Constrained values exactly zero; no unintended zeroing |
| S03 / REF-03 | Independently prescribe affine vector fields F=(2x+3y+5z,7x+11y+13z,17x+19y+23z); local curl=(6,-12,4); isolate each of 12 derivative contributions and both signs on unequal spacing | Normalized increment error <=1e-13; absent contributions <=1e-13 |
| S04 / REF-03 | Constant fields give zero curl locally; polynomial potentials G=(x^2*y+z^3,y^2*z+x^3,z^2*x+y^3) on (5,4,3), spacing (2,3,5), with exact-rational expected differences; div(curl)=0 using forward H/cell and backward E/interior-node divergence | Zero-curl values exact where no cancellation error; divergence <=1e-12 times sum of absolute differentiated terms, with floor 1 in fixture units |
| S05 / REF-03 | Independently enumerated weighted adjoint identity on (2,3,4) and (5,4,3), spacing (2,3,5); E/H values=(17*i+31*j+43*k+13*component_id) mod 101 - 50, ids 0..5 in Ex,Ey,Ez,Hx,Hy,Hz order; zero constrained E and normal boundary H; E/H dot products evaluated separately | Residual <=1e-12*max(1,sum of absolute terms), in chosen test units |
| S06 / REF-03–04 | Two full steps with independently calculated half stages on (5,4,3); single allowed interior J edge in each component with initially zero fields gives Enew=-dt*J/epsilon0 and Hplus=0 at first step | Scale-normalized sample error <=1e-13; single-edge source is a local coupling test with charge governed by discrete continuity, not a source-free fixture |
| S07 / REF-04 | Probe n=0,1,2 timestamps and coordinates, H begins at -dt/2; synthetic signed harmonic at native offsets; zero/weak H and invalid fit matrix fail estimator; reverse-travelling synthetic wave has correct direction/sign | Integer labels exact, time/coordinate <=5e-15 relative with absolute floor 5e-15*dt or spacing; complex ratio <=1e-12 |
| S08 / REF-04–05 | V01 and V03 fixture zero walls, discrete divergence, and plateau amplitudes before evolving; zero initial state/J stays zero over 100 steps | Boundaries and zero run exact; other normalized identities <=1e-11 (normalization below) |

S03/S04 local affine/polynomial data are not globally boundary-compatible.
Test the interior stencil algebra in a local harness; do not relax public
run validation to admit these as reflecting-box initial conditions. S06's
single-edge J is accompanied by the implied charge change
`rho_new-rho_old=-dt*div J`; it tests coupling without a port claim.

For normalized update errors divide by the sum of absolute independently
expected old-field and increment terms, floored at 1 V/m or 1 A/m in the
declared fixture. For S08 compare plateau E/A and eta0*H/A; normalize divergence
by sum_a |F_a|/d_a from the divergence stencil, floored at A/d_min for E or
A/(eta0*d_min) for H. A 1e-11 allowance covers subtracting nearly equal curl
terms in the normalized fixture. S05 is mandatory before interpreting Q as
an invariant. Exact rational convention-audit results supplement these tests
but cannot replace running them on the production storage/kernel.

## Reproduction contract and resource budget

Available now, and actually executed for specification review:

```powershell
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

**Execution status as of REF-04 (2026-09-10):** the built-in CLI suites exist and
their smoke subset passes [structural/artifact checks](REF-04-reference-runs.md).
The full commands below and physical analyzer remain unexecuted REF-05 work;
the analyzer script is not yet implemented. On Windows, first put the local
compiler runtime on the process PATH (also supplied by the CMake presets):

```powershell
$env:PATH = (Join-Path (Get-Location) '.tools/llvm-mingw-20250613-ucrt-x86_64/bin') + ';' + $env:PATH
& ./build/windows-local-release/antennasim.exe --benchmark reference-v1 --suite propagation --output build/evidence/reference-v1/propagation
& ./build/windows-local-release/antennasim.exe --benchmark reference-v1 --suite stability --output build/evidence/reference-v1/stability
python scripts/analyze_reference_benchmarks.py --input build/evidence/reference-v1 --output build/evidence/reference-v1/analysis
& ./.tools/cmake/cmake/data/bin/ctest.exe --preset windows-local-debug -L reference_structural
```

The named built-in benchmark suite is a minimal fixture selector, not a general
persistent project schema. `propagation` selects all 36 configurations above;
`stability` selects four long cases. Analysis independently reads emitted raw
samples/metadata; it must not import solver operators. Commands return nonzero
for failed checks or incomplete artifacts. REF-05 must also run the full
applicable CTest suite in Debug/Release and repeat the physical gate suite from
a clean Release build. Actual CLI location/flags may be revised before
implementation with an explicit contract update and no acceptance weakening.

Each run writes a metadata JSON (version, local snapshot/hash or revision,
constants, units, geometry, six extents, dt/q/steps, initialization and source,
boundary, coordinates/timestamps, CPU/backend/compiler/FP settings), native
probe CSV, and diagnostics CSV as applicable. Analysis writes per-case metrics
with thresholds/status, refinement tables, residual and long-time traces,
and a Markdown report linking raw evidence. Keep small report/identities under
docs/validation; large generated data stay under ignored build/evidence.
Write to fresh result directories or fail rather than replace prior evidence.

Calculated resource budget (not measured runtime):

| Case | Role cell counts | Six-field MiB | Full-grid cell-steps per run |
| --- | --- | --- | --- |
| Primary p=24 | (72,48,48) | 7.806 | 497,664 |
| Primary p=48 | (144,96,96) | 61.596 | 7,962,624 |
| Primary p=96 | (288,192,192) | 489.380 | 127,401,984 |
| p=24 enlarged | (168,112,96) | 83.736 | 5,419,008 |
| p=24 cubic | (72,72,96) | 23.218 | 1,990,656 |
| Stability | (12,14,16) | 0.137 | 53,760,000 initial; 53,781,504 driven |

Use the FND-03 exact array count and eight bytes per sample. The 36 propagation
cases total 865,603,584 cell-steps; four stability cases total 215,083,008.
Six component updates and diagnostic/fixture work multiply those counts.
Run serially; budget at most 2 GiB working memory with temporary potentials
released before integration, O(line length) probe buffers, and streamed CSV.
Measure actual peak memory and elapsed time at REF-04/05; abort and investigate
if allocation exceeds the declared budget. Do not infer seconds from operation
counts. This fits the recorded ~15.95 GiB machine capacity with margin but
does not establish performance. No GPU or extra dependency is required.

## Version and review rules

All limits above were selected from equations and independent synthetic
calculations before candidate solver output existed. The same collaborator
performed author review; no independent reviewer is claimed. FND-05 must check
readiness and the clean-build evidence. Later failed measurements keep P1 open;
they do not retroactively make this specification a passed physical benchmark.
Preserve version-1 limits and failed results if a reasoned revision is needed.
