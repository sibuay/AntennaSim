# REF-04 — Sources, probes, and reference runs

2026-09-10, specified before implementation. Author review only. The fixed
[FND-04 v1 specifications](../validation/FND-04-reference-benchmarks.md) remain
the acceptance authority. Physical measurements and the P1 gate belong to REF-05.

## Current and charge

Use SI vacuum Maxwell equations `mu0*dH/dt=-curl E` and
`epsilon0*dE/dt=curl H-J`. Schneider's [chapter 9, section 9.3](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf)
(rechecked 2026-09-10) supplies the staggered curl equations; impressed current
coupling and the continuity specialization here follow FND-03.
Prescribe J in A/m^2 on E edges at `(n+1/2)*dt`:
`Enew=Eold+(dt/epsilon0)*curl Hplus-(dt/epsilon0)*Jhalf`.
All H updates precede E updates and current subtraction. A positive isolated
current therefore produces negative E and initially zero H (S06).

Keep the existing rho=0, divergence-free initial-field screening unchanged.
An impressed current subsequently implies
`rho_new-rho_old=-dt*div_backward Jhalf` at interior nodes. No charge array,
charge projection, conductor feed, or port is introduced. Non-solenoidal
currents are permitted with this implied charge; the V03 source is solenoidal.
J must be finite, target an unconstrained E edge, and have unique targets.
A validated sparse current shape owns these samples and grid geometry; a finite
scalar amplitude selects each half-time value. Zero amplitude means no drive.
Preflight all scaled samples before field mutation. Any stepping exception is
terminal under REF-03; overflow reports the input state/component/index.
The strict vacuum CFL policy is unchanged. Finite forcing has no unconditional
bounded-energy claim; V03 tests the specified source-free interval after cutoff.

## Run and output

Native probes retain component, integer index, SI position, state, actual native
E or H time, and signed value. No interpolation, normalization, or magnitude
conversion is performed. H starts at -dt/2. Validate requests before execution.
Step text is ASCII decimal digits only, positive, at most 2^52-1, checked with
`from_chars` before unsigned conversion. Validate final timestamps before
allocation, and every actual step with the stepper's existing checks.

CLI contract: `--benchmark reference-v1 --suite propagation|stability|smoke
--output PATH`. Fixed propagation/stability suites retain all v1 parameters.
`smoke` runs p=24 x/y propagation and both q=.99 stability fixtures with two
steps; optional `--steps N` applies only to smoke and must still satisfy the
propagation isolation guard. Smoke establishes plumbing, not physical acceptance.
Unknown, duplicate, missing, and unsupported options fail before output creation.

Create a fresh output directory exclusively, fail if it already exists, stream
CSV, and write a completion marker only after all streams close successfully.
Write provisional configuration/provenance before field allocation; incomplete
case and pending fixture status distinguish placeholder checks from measurements.
Failure retains partial evidence without a completion marker and reports the
case name as well as the underlying error. Metadata identify
schema, constants, units, geometry, extents, native times, source/initialization,
boundary, compiler/FP policy, source snapshot, planned memory, and elapsed time.
No general project persistence schema is introduced. Results are solver output;
fixture checks, geometry, resource counts, and initialization are deterministic
calculations. Output success never means V01–V03 passed.

## Fixtures and independent checks

Generate the FND-04 potentials on demand from native positions using an
axis-permutation finite-difference curl separate from production kernels.
No potential volumes are retained. Check zero walls, normalized divergence,
and every propagation plateau probe before constructing a stepper (S08,
1e-11); keep the raw initial probes. Enumerate all 36 propagation configurations
and all four stability configurations, with the dependency guard checked before
allocation. Enlarged probes use the exact original index plus the 2-lambda shift.
The V03 current shape is the normalized curl fixture; its half-time sine pulse
ends after eight updates. Diagnostics use independent forward differences and
compensated weighted sums for U and Q as specified in FND-04.

Budget field construction at two field payloads plus sparse-current storage,
probe storage, and fixed overhead, at most 2 GiB. Release the initial field after
stepper construction. Cases execute serially; CSV does not retain run history.
Measure process peak memory separately with the run audit. Do not run the full
physical suite as an implicit REF-04 accuracy claim.

Acceptance fixed before implementation: retained six CTests and three Python
audits; S06 each E component/both current signs with normalized error <=1e-13,
implied discrete continuity and unchanged initial screening; invalid sources,
probes, counts, nonfinite update/failure policy; S07 native n=0,1,2 locations and
times <=5e-15 with the v1 floors. Independently read emitted CSV/JSON, check
sample counts and finite values, deterministic reruns, refusal to overwrite,
and incomplete-artifact rejection. `scripts/reference_measurements.py` implements
the independent native harmonic fit and signed time correction; synthetic S07
checks include both directions/signs, n=0/1/2, weak H and singular matrices.
The REF-05 analyzer still needs to apply those measurements to full solver runs.
