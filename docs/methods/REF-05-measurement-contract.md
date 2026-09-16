# REF-05 — Physical measurement and analysis contract

2026-09-16, specified before the full suites were executed. Author review only.
The fixed [FND-04 v1 specification](../validation/FND-04-reference-benchmarks.md)
remains the acceptance authority; this note fixes how its V01–V03 observables are
computed from the REF-04 raw artifacts and how those reductions are validated
before any physical result is accepted. No solver equation, fixture, tolerance,
or CLI contract changes.

## Inputs and independence

The analyzer `scripts/analyze_reference_benchmarks.py` reads only the emitted
`COMPLETE.json`, `metadata.json`, `probes.csv`, and `diagnostics.csv` of the
`propagation` and `stability` suites, plus the optional `resources.json` written
by `scripts/run_reference_benchmarks.py`. It imports the REF-04 artifact audit and
the independently tested harmonic estimator; it imports no solver, fixture, or
diagnostic operator. Geometry, spacing, Courant fraction, time step, step count,
case enumeration, and the discrete dispersion frequency are re-derived from the
v1 definitions inside the analyzer and compared with the metadata; a mismatch
fails the case even when its measurements would pass.

## V01/V02 reductions

Per case, for every recorded state n=0..N and each of the six native lines:

- exactly p samples whose integer indices are exactly the prescribed v1 line
  (axial p..2p-1 plus the 2λ cell offset for enlarged runs, transverse indices
  at the domain centre), one common recorded time per line, finite values;
- active E (component b) and signed Cartesian H (component c) are fitted to
  `a cos(k r_a) + b sin(k r_a)` at their own native axial coordinates by the
  two-column least-squares solve of `reference_measurements.fit_harmonic`, which
  rejects fewer than p samples, condition number ≥ 2, nonfinite data, and
  fitted magnitude below `0.5 A` (E) or `0.5 A/eta0` (H);
- `omega_m = Arg(C_N/C_0)/(N dt)` from the active E fits, required positive;
- `Z_n = (C_E,n e^{-i omega_m t_E})/(C_H,n e^{-i omega_m t_H})` with the recorded
  native times, compared with `s eta0`, `s=(u×v)·e_c`, as a complex ratio;
- the four inactive lines contribute `max(|E|/A, eta0|H|/A)`.

Limits are the v1 table: continuum caps 0.0015/0.000375/0.00009375 for primary
p=24/48/96 and the enlarged p=24 runs, 0.003 for the q=0.5 and cubic runs;
discrete, amplitude, residual, and inactive limits 1e-9; complex impedance 1e-8.
Refinement per axis/polarization requires positive, strictly decreasing primary
continuum errors with both `log2(error_p/error_2p)` in [1.8,2.2]. The enlarged
comparison matches every primary sample to the enlarged sample whose integer
index is offset by the exact 2λ cell shift per axis, checks the coordinates are
shifted by 2λ, and requires `|ΔE|/A` and `eta0|ΔH|/A` ≤ 1e-10 with all samples
matched. Continuum error is also reported against the analytical dispersion
prediction, which is a diagnostic label, not an acceptance reference.

## V03 reductions

Per case the diagnostics trace must contain states 0..N in order, with N=20000
(initial-field) or 20008 (driven). With `n_ref=0` or 8, `U_ref,Q_ref>0`, and for
every `n≥n_ref`: `|Q_n−Q_ref|/Q_ref ≤ 1e-8`, `U_n/U_ref ≤ ((1+q)/(1−q))(1+1e-8)`,
and `(1−q)U_n − 1e-8 Q_ref ≤ Q_n ≤ (1+q)U_n + 1e-8 Q_ref`. The analyzer records the
maximum normalized invariant error and its state, min/max `U/U_ref`, the first
nonfinite diagnostic if any, per-component maxima over all states and over the
source-free interval, the maximum normalized centre-probe value, and block maxima
for each of the 20 consecutive 1,000-step source-free blocks. It also requires
`Q_0=U_0` for the initial-field cases and zero initial diagnostics for the driven
cases. Probes must be finite.

## Reduction validation before acceptance

`scripts/check_reference_analysis.py` (CTest `reference.analysis_reductions`) must
pass before the physical results are interpreted:

1. Synthetic prescribed discrete harmonics on all 36 v1 geometries pass with
   continuum error equal to the analytical prediction, discrete/impedance
   deviations ≤ 1e-12; injected discrete-frequency, amplitude, sign, direction,
   inactive-contamination, missing-sample, relocated-line, step-count, geometry,
   time-mixing, continuum, refinement-order, and enlarged-difference faults are
   detected; resource-record faults and a corrupt metadata file are reported in
   written outputs rather than by an uncaught exception.
2. Synthetic 20,000/20,008-state diagnostics traces pass with the expected block
   partition; drift above 1e-8, bound violations, nonfinite values and short
   traces are detected.
3. With the built CLI, the smoke suite is executed and the two stability cases
   are reproduced by an independent pure-Python transcription of the FND-03
   update equations, the V03 modular-potential fixture, the driven-current
   pulse, and the weighted `U/Q` diagnostic on nested lists; `U`, `Q`, the six
   maxima and the six centre probes must agree within 1e-12 relative at every
   state. The two-step propagation smoke case must pass the V01/V02 reductions.

The oracle transcribes the six explicit component equations directly; the
benchmark library uses axis-permutation differences and the solver its own
kernels, so three separately written forms are compared.

## Execution, resources, and evidence

Run the suites serially from a clean Release build with
`scripts/run_reference_benchmarks.py`, which records elapsed time and, with
psutil, the process peak working set per suite in `resources.json`, and aborts
a suite whose peak exceeds the 2 GiB budget with a nonzero status; per-case
elapsed time comes from the CLI metadata. The analyzer adds a `resources`
suite that fails when `resources.json` is missing or unreadable, a suite's
runner status is nonzero, or its peak is unmeasured or over budget, and a
`provenance` entry for unreadable metadata or mixed source snapshots, so every
failure is reported in the written outputs. Analysis writes `metrics.json`
(compact per-case metrics with thresholds and status), `propagation-trace.csv`
(per-state fits and complex impedance), `stability-blocks.csv`, and `report.md`
to a fresh directory and exits nonzero on any failure while retaining outputs.
The tracked evidence keeps the compact metrics and the report; raw arrays stay
under the ignored `build/evidence` tree.

Acceptance fixed before execution: all 36 propagation cases, six refinement
sequences, six enlarged comparisons, and four stability cases pass their v1
limits from one source snapshot; the reduction validation passes; Debug and
Release CTest suites pass including the new test; measured peak memory stays
below the 2 GiB budget. Any failure keeps REF-05 open with its outputs retained.
Passing supports only axis-aligned vacuum propagation/impedance and closed-grid
stability for the declared fixtures and durations.
