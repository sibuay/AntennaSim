# REF-03 — Vacuum reference stepping contract

Date: 2026-09-07. Recorded before implementation. P1 implementation contract;
physical V01–V03 validation and the P1 gate remain pending.

## Method and scope

Implement the six equations, exact ranges, constants, SI units, spatial/time
placements, and reflecting `zero_tangential_e` closure in
[FND-03](FND-03-yee-conventions.md). Governing equations are
`mu0*dH/dt=-curl E`, `epsilon0*dE/dt=curl H` here (J=0).
H is updated completely from n-1/2 to n+1/2, then E from n to n+1.
No material, source, probe, CLI, backend, or physical PEC extension is included.

Source reconfirmed for implementation: Schneider, *Understanding FDTD*,
[Chapter 9](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf), section 9.3,
equations 9.9–9.20 and section 9.7 equation 9.53. The local FND-03 specialization
fixes component signs, array orientation, SI scaling, and ranges. Pinned 2022
constants remain c0=299792458, mu0=1.25663706127e-6,
epsilon0=1/(mu0*c0*c0), eta0=mu0*c0. No constants update is implied.

Uniform vacuum stability requires
`dt_max = (d_min/c0)/sqrt(sum_a (d_min/d_a)^2)`.
This scaled expression avoids squaring large reciprocals. Accept only finite
`0<dt<dt_max`, or finite `0<q<1` with dt=q*dt_max (default q=0.99).
A q whose rounded dt reaches the limit is rejected, never clamped. This is
a stability policy, not achieved accuracy. The interior method is second-order
for smooth fields; boundary returns, initialization, and measurement errors
still require the fixed physical benchmarks.

## Concrete API and failure policy

- `VacuumTimeStep` is a validated value constructed by `from_courant(grid,q)`
  or `from_seconds(grid,dt)`. It retains spacing, dt, dt_max, actual dt/dt_max,
  dt/mu0 and dt/epsilon0. Require positive finite dt_max, dt/2, both scales,
  each reciprocal spacing, and each scale/spacing coefficient. This deliberately
  rejects extreme geometry that cannot support the chosen binary64 evaluation.
  Nonpositive/nonfinite q/dt or violated strict CFL: invalid_argument;
  nonrepresentable derived quantities: overflow_error.
- `times_at(n)` returns E=n*dt and H=(n-1/2)*dt, computed by multiplication.
  Use uint64_t states, n<=2^52-1, preserving exact half indices. At n>0,
  require strictly ordered previous E < current H < current E and previous H
  < current H, all finite. At n=0 require H<0 and E=0. Reject overflow or
  merged timestamps. This checks an individual state, not an arbitrary run's
  step-count parser (REF-04).
- `ReferenceStepper(initial, time_step)` explicitly copies a validated initial
  FieldStorage into owned storage at n=0. Spacing must match the time-step value.
  Expose fields only by const reference; no mutation during integration and no
  implicit solver copy/move. Temporary initialization storage can be released
  after construction; transient construction needs two field payloads.
- Reject nonfinite initial samples and nonzero tangential E / normal H walls.
  For this source-free API, require backward E divergence at interior nodes
  and forward H divergence at cells to be within
  `1e-11*max(1,sum(abs(each divided endpoint)))` in the relevant SI derivative
  units, matching the S08 structural roundoff budget. Reject nonfinite arithmetic
  as well. This is compatibility screening, not a magnetic-charge repair or
  exact proof of divergence-free data. Initial E represents rho=0 here.
- `step()` checks next timestamps before mutation, updates every H sample, then
  every unconstrained E sample, preserving exact zero tangential E. Normal H is
  updated normally and stays zero from the boundary-compatible curl stencil.
  Time advances only after the full step succeeds. No current coupling yet.
- A nonfinite output throws `FieldUpdateError` with input state n, target
  component, and integer index. In-place updates can leave a partial field;
  the stepper becomes failed and rejects further stepping or field/time reads.
  State/failure inspection remains available. Earlier borrowed const views must
  be discarded after any exception; C++ cannot revoke a previously returned view.
  No rollback copy or output artifact
  is created. A time preflight failure occurs before mutation and is also terminal.
- Internal detail curl and family-update routines serve the production stepper
  and local S03/S04 harness. They are not public physical-run entry points.
  Local tests may evaluate incompatible polynomial/affine fields through these
  routines without weakening the stepper's initial validation.

The scalar reference uses bounds-checked field access and explicit curl formulas,
with ordinary binary64 differences/division and then the dt/material scale.
Overflow is rejected even where a differently scaled expression might succeed.
Extra field magnitudes are not silently clipped. Cost is O(field samples) per
step and O(field samples) initialization screening, with no per-step field copy.
Optimization and measured runtime/memory remain later work.

## Independent acceptance fixed before implementation

Use [FND-04 S01–S06 and V03 input policy](../validation/FND-04-reference-benchmarks.md)
without changing thresholds. A separate Python Fraction calculation uses
Levi-Civita axis permutations and native coordinates to generate small golden
states. It must not import production code or use candidate output. Retain its
script, generated header, and deterministic regeneration check.

| Requirement | Comparator / test |
| --- | --- |
| CFL | Independently compute 1/(c0*sqrt(sum(1/d_a^2))) for cubic and unequal grids, default q/.5, <=5e-15 relative; reject 0/negative/1/>1/NaN/infinity; explicit dt equality/next-above rejected, next-below accepted; q=1-2^-20 one-step smoke |
| Representability/time | Extreme and denormal spacings, tiny q/dt, zero/overflowing coefficients, n=0/1/2 exact expected times, huge index/nonfinite/merged timestamps; errors before stepping |
| S01/S02 | Actual family loops on all three small grids, exact zero constrained E/normal H across two steps; compare every unconstrained result to independent golden states on (5,4,3); no unwanted zeroing |
| S03 | Affine F=(2x+3y+5z,7x+11y+13z,17x+19y+23z), curl=(6,-12,4); each of twelve signed terms individually plus reversed slopes; normalized increment error <=1e-13, absent increments <=1e-13 |
| S04 | Constant curl exactly zero; G=(x^2*y+z^3,y^2*z+x^3,z^2*x+y^3), exact-rational central differences at native targets, and forward/backward divergence of production curls <=1e-12 times absolute differentiated terms, floor 1 |
| S05 | Both weighted dot products from production curls on specified modular fields for (2,3,4)/(5,4,3); independently known exact dot values -52411/30 and -27929/6; residual <=1e-12*max(1,sum absolute terms) |
| S06 subset | dt=1e-9 s, cells (5,4,3), spacing (2,3,5); exact-rational compact-potential initial E/H curls; compare all fields after H1/E1/H2/E2, <=1e-13 normalized by abs(old)+abs(increment), floor 1; public stepper agrees with full states |
| Input/failure | All components: nonfinite initial samples, nonzero walls, nonzero divergence; time-step/grid mismatch; finite divergence-free curl data scaled to force nonfinite E update, precise diagnostic and terminal failure |
| Regression | Five retained CTests and both analytical audits, Debug/Release; zero-state 100-step smoke only, not long-time stability |

S06 current sign/coupling belongs to REF-04, with its declared charge continuity.
Run-count parsing, source/probe requests, timestamps in emitted results and
nonfinite-output artifact handling also remain REF-04. Physical propagation,
impedance, refinement and long-time stability remain REF-05. Report same-author
review and platform limits; a passing structural suite does not close P1.
