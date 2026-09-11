# Validation plan and benchmark register

**Current state:** physical benchmark runners are implemented, but no full
physical benchmark has passed. REF-01 has
[passing production grid structural checks](validation/REF-01-core-grid.md), and
REF-02 has [passing field storage/access checks](validation/REF-02-field-storage.md).
REF-03 has [passing CFL and equation-level kernel checks](validation/REF-03-reference-updates.md).
REF-04 has [passing sources, probes, fixture, and CLI artifact checks](validation/REF-04-reference-runs.md).
This does not establish electromagnetic accuracy or complete V03.

The initial equations and input/sampling contract are recorded in
[FND-03 conventions](methods/FND-03-yee-conventions.md), with
[specification audit evidence](validation/FND-03-review.md). V01–V03 now have
[fixed version-1 acceptance specifications](validation/FND-04-reference-benchmarks.md)
and [author-review/calculation evidence](validation/FND-04-review.md). Their
production fixtures and raw-output runners now exist; full numerical measurements
remain pending. The
[FND-05 foundation gate](validation/FND-05-foundation-gate.md) passed on
2026-09-06. REF-01 through REF-04 are complete and REF-05 is ready. P0 infrastructure,
S01–S07, six primary p24/V03-shape S08 checks, and grid/CFL/source/probe/run-input
checks pass. Larger S08 fixtures and full physical runs remain pending.

## Acceptance policy

Before a numerical feature is implemented, write its benchmark specification in
`docs/validation/` and method note in `docs/methods/`. Create those directories with
their first real records. Each specification must contain:

- Governing equations or trusted reference data, exact provenance, and applicable
  assumptions; do not use this solver's output as its own accuracy reference.
- Geometry, material parameters, units, excitation, boundary conditions, sampling
  locations, mesh sequence, time step, and simulation/measurement duration.
- The observable and independent comparator, including error definition and
  normalization. Specify absolute floors where relative error is ill-conditioned.
- Numerical acceptance thresholds and why they are appropriate for the physical
  objective, reference uncertainty, discretization, and measurement procedure.
- Expected mesh/time/domain sensitivity and what constitutes a failed result.
- A reproducible command, resource estimate, and expected evidence artifacts.

Tolerance lifecycle: **proposed → reviewed → fixed for the benchmark version**.
Thresholds below are deliberately not invented before geometry and measurement
definitions exist. FND-04 must supply concrete values for V01–V03 before P1 begins;
each later phase must do the same for its benchmarks before implementing the
corresponding method. Revisions require a reason and preserve previous evidence.

## Benchmark register

V01–V03 have status **Specified and author-reviewed; runners implemented,
only structural/smoke subsets run; physical acceptance pending**.
V04–V15 remain **Specified at planning level only**. S01–S08 structural
acceptance requirements are included in the FND-04 version-1 specification.

Implemented structural coverage: `reference.grid` (CTest labels
`reference_structural;fast`) covers REF-01's extent/count/size/geometry-input
subset with 136 runtime checks plus compile-time count-type constraints.
`reference.fields` adds 23838 storage/index/location/wall checks and 1976 reads
through a test-only stencil harness on the three S01 grids. `reference.vacuum`
adds 27013 CFL, actual-loop, boundary, curl/sign/divergence/adjoint, half-stage,
time, and failure-policy checks. Independent Fraction golden states compare
every sample at two complete source-free steps. `reference.run` adds 3337 current,
continuity, source overflow, native probe and input checks, plus S08 identities
on six primary p24 grids and the V03 shapes. `reference.run_artifacts` independently
checks S07 signed synthetic fits, raw native output, repeatability, bad arguments,
overwrite refusal and incomplete-artifact rejection. Larger fixtures execute
their S08 checks before stepping in REF-05. A 100-step zero-state regression
passes, but V03 long-time stability is still pending.

All three independent Python convention/specification/golden-state audits are
registered in CTest, and Python is required whenever `BUILD_TESTING=ON`; validation
therefore fails closed instead of reporting a reduced suite as a pass. GitHub CI
runs the same eleven-test Debug/Release suite and retains logs and smoke artifacts.

| ID | First phase | Case / independent reference | Required measurements and checks |
| --- | --- | --- | --- |
| V01 | P1 | Free-space propagation / analytical wave behavior | Travel time or phase velocity; numerical dispersion; amplitude; samples chosen before boundary returns |
| V02 | P1 | Free-space plane-wave impedance / analytical medium relation | E/H with spatial and temporal staggering handled explicitly; source transients and near-zero samples excluded by a predefined rule |
| V03 | P1 | Stability and input policy / derived discrete stability conditions | Valid time-step handling, non-finite/invalid input rejection, long-run field or energy diagnostics for a declared source/boundary setup |
| V04 | P2 | PEC cavity / analytical resonant modes | Resonance error; spectral-resolution effects; mode identification; mesh/time sensitivity; boundary enforcement |
| V05 | P2 | Homogeneous dielectric and planar interface / analytical propagation and interface relations | Phase velocity, reflection/transmission, field placement and material assignment |
| V06 | P2 | Conductive dielectric / analytical propagation for the declared material model | Attenuation and phase; nonnegative dissipation; zero-conductivity limit; supported frequency range |
| V07 | P2 | Known synthetic signals / independently calculated spectra | Frequency bins, complex phase, amplitude normalization, windowing, sampling duration and direct-transform comparison |
| V08 | P3 | Absorbing boundary / incident-versus-reflected field experiment | Reflection versus frequency, incidence and polarization; layer/domain sensitivity; faces/edges/corners; late-time growth |
| V09 | P4 | Port extraction / independently specified voltage-current signals and suitable canonical/reference loads | Sign, units, reference impedance, complex impedance, S11 and power consistency; weak-signal behavior |
| V10 | P4–P5 | Finite modeled dipole / trusted solver for matching geometry/feed, analytical trends where applicable | Input impedance/resonance first; radiation pattern/directivity/gain/efficiency later; mesh/domain/time and feed sensitivity |
| V11 | P5 | NF2FF and power processing / independent field or radiation references | Surface invariance within declared limits, angular integration, normalization, symmetry/polarization, accepted/radiated/lost power balance |
| V12 | P6 | Rectangular microstrip patch / trusted solver or measured reference with full model provenance | Resonance, complex impedance/S11, patterns, gain and efficiency; feed/substrate/mesh sensitivity and reference uncertainty |
| V13 | P7 | Nonuniform-grid cases / analytic cases and validated uniform-grid solutions | Refinement behavior, grid-transition errors, stability, material/interface treatment, accuracy versus resource cost |
| V14 | P8–P9 | Backend comparisons / permanent CPU reference plus physical benchmarks | Fields and derived metrics within justified tolerances; repeatability policy; runtime and peak memory on named hardware |
| V15 | Later port expansion | Horn with validated waveguide excitation / trusted reference | Input behavior where comparable, radiation pattern, gain, beamwidth, domain/mesh sensitivity |

V09 covers both processing and actual port coupling: synthetic-signal checks alone
cannot validate a physical excitation. V10 must not treat an idealized thin-wire
formula as exact ground truth for a finite-radius, finite-gap voxelized geometry.

## Regression layers

| Layer | Purpose | Run policy |
| --- | --- | --- |
| Structural/unit | Indexing, extents, units, invalid inputs, deterministic utility behavior | Relevant changes and fast suite |
| Small physical cases | Local/component correctness and compact analytic comparisons | Numerical changes affecting those cases |
| Analytical and trusted-reference benchmarks | Physical accuracy across the declared operating envelope | Feature completion and phase gates |
| Convergence and long-time cases | Sensitivity, refinement, late-time instability, boundary effects | Related method changes and phase gates |
| Integration/project | Serialization, geometry, audits, reproducible end-to-end runs | Introduced with persistent projects and later workflows |
| Backend equivalence | CPU parallel/GPU numerical consistency | Backend changes, then releases |

Exact test labels and runtimes will be recorded once the runner exists. Include
all six field components and anisotropic cell dimensions where relevant; a single
polarization on cubic cells is not sufficient coverage for the update kernel.

## Evidence report contents

Record benchmark/version, code revision, source provenance, configuration,
environment, commands, measured values, thresholds, and pass/fail status. Include
plots or tables that expose discrepancies rather than only a pass summary.

For convergence, use a justified sequence of resolutions—normally at least three
when feasible—and record computational cost. Do not claim convergence from one
run. Distinguish spatial discretization effects from finite duration, spectral
resolution, source/port error, boundary error, and reference uncertainty.

An analytical estimate helps interpret behavior; a convergence result checks
internal consistency; an independent reference tests external agreement. Label
these evidence types separately and retain contradictory evidence for review.

## Failure handling

1. Preserve the failing configuration and output summary.
2. Reproduce the failure and locate the responsible subsystem.
3. Check equations, staggering, units, source/boundary conventions, and measurement
   assumptions before attempting parameter tuning.
4. Fix the cause and rerun affected benchmarks and regressions.
5. Record the failure, resolution, and any remaining limits in the evidence report.

Do not fabricate reference results, silently replace baselines, loosen thresholds
to fit the implementation, or label unsupported configurations as validated.
