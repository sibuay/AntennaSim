# Validation plan and benchmark register

**Current state:** V01–V03 version-1 benchmarks have been measured and passed
from a clean Release build ([REF-05 evidence](validation/REF-05-reference-measurements.md)),
and the [P1 gate (REF-06)](validation/REF-06-reference-propagation-gate.md)
passed on 2026-09-17 after reproducing those measurements exactly from a second
clean build; its record bounds the supported envelope. REF-01 has
[passing production grid structural checks](validation/REF-01-core-grid.md), and
REF-02 has [passing field storage/access checks](validation/REF-02-field-storage.md).
REF-03 has [passing CFL and equation-level kernel checks](validation/REF-03-reference-updates.md).
REF-04 has [passing sources, probes, fixture, and CLI artifact checks](validation/REF-04-reference-runs.md).
REF-05 has [passing physical measurements with validated reductions](validation/REF-05-reference-measurements.md).
These establish only the declared axis-aligned vacuum and closed-grid envelope.

The initial equations and input/sampling contract are recorded in
[FND-03 conventions](methods/FND-03-yee-conventions.md), with
[specification audit evidence](validation/FND-03-review.md). V01–V03 now have
[fixed version-1 acceptance specifications](validation/FND-04-reference-benchmarks.md)
and [author-review/calculation evidence](validation/FND-04-review.md). Their
production fixtures, raw-output runners, and independent analyzer now exist and
their full measurements pass. The
[FND-05 foundation gate](validation/FND-05-foundation-gate.md) passed on
2026-09-06 and the P1 gate on 2026-09-17. REF-01 through REF-06 and MAT-01
through MAT-03 are complete and MAT-04 is ready. P0 infrastructure, S01–S09 on every
executed fixture, grid/CFL/source/probe/run-input/mask checks, and the full
V01–V03 v1 suites pass. V04–V07 have
[fixed version-1 specifications](validation/MAT-01-closed-domain-benchmarks.md)
under the [MAT-01 conventions](methods/MAT-01-closed-domain-conventions.md),
with [audit evidence](validation/MAT-01-review.md). V04 (PEC cavity
eigenmodes, driven spectrum, interior enforcement) has
[passing measured evidence](validation/MAT-02-pec-cavity.md) from a clean
Release build (MAT-02, 2026-09-18), with the V01–V03 suites reproduced at
zero tolerance through the mask-capable kernel. V05 (dielectric eigenwave,
TE-mode interface, slab-loaded cavity) and V06 (lossy eigenwave, dissipation
identity, zero-conductivity limit) have
[passing measured evidence](validation/MAT-03-dielectric-conductivity.md) from
a clean Release build (MAT-03, 2026-09-23). V01–V04 were reproduced at zero
tolerance through the material kernel. No spectral production capability is
validated.

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

V01–V03 have status **Version 1 measured and passed (REF-05, 2026-09-16);
P1 gate passed and measurements reproduced exactly from a clean build (REF-06,
2026-09-17)**. They are permanent regressions: any change to the kernel, fixtures,
or analyzer must keep them passing with their fixed limits.
V04 has status **Version 1 measured and passed (MAT-02, 2026-09-18);
re-confirmed under specification revisions 1.2, 1.3 and 1.4 of the V04-C
driven acceptance and probe-record completeness (2026-09-22)** from a clean Release build with the independent, fault-checked
closed-v1 analyzer; it is a permanent regression through the `closed-v1`
suites and their smoke subset. Revision 1.2 followed a review finding that the
version-1 C2/C3 criterion required only finiteness of the driven side and so
could not fail on a run that injected nothing, and revision 1.3 a follow-up
finding that the strengthened criterion still accepted the deposit in the
wrong electric component and never referred to the driven edge, and revision
1.4 a third finding that a prescribed probe absent from every state passed both
the audit and the reduction, which read its missing samples as zero; the same
raw runs pass all three revisions with the margins in the
[MAT-02 evidence](validation/MAT-02-pec-cavity.md).

V05 and V06 have status **Version 1 measured and passed (MAT-03, 2026-09-23)**
from a clean Release build with the extended independent analyzer. V05-B mode
purity passes under specification revision 1.5, which normalizes by
`max(abs(a_n), 1e-4 peak)`. The version-1 rule failed only at carrier zero
crossings, where its relative normalization demanded precision below roundoff,
and that failure is retained in the evidence (D025). V06-C reproduced V01–V03
at zero tolerance. V05/V06 are permanent regressions through the `closed-v1`
material suites and their smoke subset.

V07 has status **Version 1 specified (MAT-01, 2026-09-18); not run**; its
production comparison is MAT-04's. The fixtures, comparators, caps, resource
budgets (corrected for coefficient storage by D023) and S14 are in the
[MAT-01 specification](validation/MAT-01-closed-domain-benchmarks.md). V08–V15
remain **Specified at planning level only**. S01–S08 structural acceptance
requirements are included in the FND-04 version-1 specification; S09 is
implemented by `reference.pec` and S10–S13 by `reference.material_*`.

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
overwrite refusal and incomplete-artifact rejection. `reference.analysis_reductions`
adds 97 synthetic reduction, resource-budget and failure-retention checks, an
independent pure-Python oracle of the
stability diagnostics on smoke output, and a two-step production propagation
measurement. All larger fixtures executed their S08 checks before stepping in
the full REF-05 runs, and V03 long-time stability passed.
`reference.material_specification` (MAT-01) recomputes every V04–V07 prediction
and cap, checks the cavity, interface, slab, lossy and spectral estimators and
their fault detection on synthetic data, and verifies the interface gating
against a reduced-system oracle; it exercises no solver code.
`reference.pec` (MAT-02, S09) adds 209550 checks: the default mask against the
grid's wall classification, box/shell/wall-touching/overlapping primitives on
`(5,4,3)` and `(2,3,4)` and the V04-C shell and solid box on `(18,22,26)`
against an independent endpoint enumeration (3,008 and 13,072 edges), exact
zeros of masked E and enclosed H over two driven steps with evolving unmasked
samples, bitwise agreement of the closure-only mask with the vacuum kernel and
stepper, and the rejection matrix (inverted/out-of-range primitives, mask/grid
mismatch, nonzero masked or enclosed initial samples, a current on a masked
edge, the V04-C mode and C2 source inside a solid box). `reference.closed_analysis`
(MAT-02) adds 726 checks: synthetic exact modes on all 30 V04-A configurations
with the specified fault injections, the V04-B modal-sum record with shifted,
spurious, missing, truncated, growing and nonfinite faults, synthetic V04-C
C1/C2/C3 with region-leak, interior-deviation, missing-reference and mask-count
faults, under specification revision 1.2 the driven-excitation faults
(an identically-zero record, a perturbed first deposit, a second component
moving at state 1, a peak below the floor, a drifting invariant, a nonzero
start and a wrong time step), under revision 1.3 the wrong-component and
wrong-edge faults (the deposit moved to `Ex`, a wrong-sign or dead source
sample, a leaking second probe, a non-`Ez` or relocated probe, an unprobed
source edge, and the mutation revision 1.2 accepted) together with the
emitted initial-condition description, under revision 1.4 the probe-record
coverage faults (a uniformly absent probe, an extra probe, a set that varies
between states, a missing state, an empty record, a deleted second probe, a
single deleted state, a deleted source sample, a short declared probe set and
a duplicate standing in for a missing sample), and the four-step closed-v1 smoke suite
reproduced by a pure-Python
oracle with an independently enumerated mask (probes, `U`, `Q`, component and
region maxima within 1e-12), including the shell case reproducing the open
cavity bitwise.

MAT-03 adds the following tests:

- **`reference.material_map` (S10, 9554 checks).** Modular per-cell maps,
  and maps whose `sigma` does not follow `eps_r`, against an independent
  cell-to-edge enumeration. The vacuum map equals the default table bitwise,
  and the vacuum kernel is bitwise P1. The driven stepper is bitwise equal to a
  transcribed P1 step. Covers the rejection matrix and the eps-weighted Gauss
  screening. The count was 3022 before the 2026-09-25 review.
- **`reference.material_update` (S11, 1034).** The single-edge lossy update
  at four values of `x`, and two lossy steps against the exact-rational header
  that `reference.material_steps` regenerates.
- **`reference.material_timestep` (S12, 19).** The vacuum CFL value for every
  material; rejection before allocation, and on coefficient overflow.
- **`reference.material_dissipation` (S13, 611).** The one-step identity
  `Q_(n+1) - Q_n + D_n` on modular fields.
- **`reference.closed_analysis` (from 726 to 2654 checks).** Synthetic
  V05-A/B/C and V06-A/B series with their fault injections. The second
  2026-09-25 review added faults for every enforced limit, which a mutation run
  confirmed. The revision-1.5
  purity conditioning. The coefficient-table audit against a brute-force
  enumeration. A pure-Python material oracle that reproduces the five material
  smoke cases (probes, `U`, `Q`, `D`, maxima) within `1e-12`.

All seven independent Python convention/specification/golden-state/reduction
audits (MAT-03 added the material golden-state generator) are registered in CTest, and Python is required whenever `BUILD_TESTING=ON`;
validation therefore fails closed instead of reporting a reduced suite as a pass.
GitHub CI runs the same twenty-test Debug/Release suite and retains logs and smoke
artifacts. The full physical suites are run manually from a clean Release build
with `scripts/run_reference_benchmarks.py` (`--benchmark reference-v1` or
`closed-v1`), `scripts/analyze_reference_benchmarks.py` and
`scripts/analyze_closed_benchmarks.py`; `scripts/compare_reference_analysis.py`
checks a re-run's summary against the tracked one at zero tolerance for
gate-level reproduction evidence.

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

If investigation shows that a criterion fails only because its measurement is
ill-conditioned, the fix is to the measurement definition, not a looser limit.
An example is a relative residual divided by a quantity that passes near zero,
which then demands precision below binary64 roundoff. This applies only when
the investigation also shows that the absolute error stays at the roundoff
scale and that there is no solver defect.

- Keep the original limit wherever the quantity is resolvable.
- Add an absolute floor to the normalizer, derived from the roundoff scale
  with a stated margin.
- Show with injected faults that real defects just above the limit are still
  detected.
- Report how many measurements fall under the floor and how much looser the
  check is there. Derive the resolution threshold from the measured
  accumulated roundoff, not from a single rounding (added after the MAT-03
  review on 2026-09-25).
- Preserve the failing analysis, and record a numbered specification revision
  and a decision.

The owner adopted this rule on 2026-09-23; see MAT-01 V05-B revision 1.5 and
D025.

Do not fabricate reference results, silently replace baselines, loosen thresholds
to fit the implementation, or label unsupported configurations as validated.
