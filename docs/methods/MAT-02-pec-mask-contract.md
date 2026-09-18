# MAT-02 — Explicit PEC edge mask, closed-v1 runs, and V04 analysis contract

2026-09-18, specified with the implementation and before the V04 suites were
executed. Author review only. The fixed
[MAT-01 specification](../validation/MAT-01-closed-domain-benchmarks.md) remains
the acceptance authority and the
[MAT-01 method note](MAT-01-closed-domain-conventions.md) fixes the mask
semantics; this note records the API, error, fixture, output, and analysis
decisions that realize them. Evidence is in
[MAT-02 PEC cavity evidence](../validation/MAT-02-pec-cavity.md).

## Mask representation and semantics

`PecMask` (`include/antennasim/pec.hpp`) owns one byte per E sample in the
FND-03 layouts (`Nex+Ney+Nez` bytes, reported as `mask_bytes`) for a
validated `UniformGrid` and a list of `PecPrimitive` values. A primitive is a
`PecShape` (`Box`, solid; `Shell`, hollow) with a `CellBox` of half-open cell
ranges `[low, high)` per axis, accepted only when `0 <= low < high <= N` on
every axis (`std::invalid_argument` otherwise, before any allocation). The
marking rule `pec_marks` is the MAT-01 integer-index rule: an `E_a` edge with
storage index `(i_a, i_b, i_c)` is marked by a box when `low_a <= i_a < high_a`
and `low_t <= i_t <= high_t` for both transverse axes, and by a shell when in
addition one transverse index equals `low_t` or `high_t`. The mask is the
union of every primitive with the outer closure `Shell([0,N))`, which is always
present and equals the FND-03 tangential-wall set (S09 checks this against the
grid's own classification and an endpoint enumeration). `masked_counts()` and
`closure_counts()` report the per-component totals; `values()` exposes the
contiguous byte view of an E component and rejects H components. H samples are
never masked; `enclosed()` is true for an H sample whose four surrounding
tangential E samples (the FND-03 forward stencil) are all masked, which is the
general form of "outer normal wall, box interior, shell face-normal".

## Stepper integration

`ReferenceStepper(initial, dt)` keeps its P1 meaning and delegates to
`ReferenceStepper(initial, dt, PecMask{grid})`; the three-argument form takes
an explicit mask whose cells and spacing must match the fields
(`std::invalid_argument`). The initial screening rejects a nonzero value on any
masked E sample or enclosed H sample (`std::invalid_argument`, with the
state/component/index text of REF-03); on a closure-only mask these are
exactly the P1 wall checks. The E divergence screening is evaluated only at
nodes whose six surrounding E samples are unmasked, because charge on PEC
faces is implied by Gauss's law and not tracked; the H divergence screening is
unchanged. The E update loop keeps the FND-03 half-open ranges and skips
masked samples, so they are never written and stay exactly zero; the H update
is unchanged. With a closure-only mask the loop performs the identical
floating-point operations in the identical order, which is the bitwise vacuum
requirement (checked at kernel level in S09, on the smoke CSV bytes, and by the
zero-tolerance V01–V03 reproduction). An impressed current whose target edge is
masked is rejected before any mutation as a terminal `std::invalid_argument`
of the step (the stepper enters its failed state, as for every step
exception); `ElectricCurrent` itself still validates only against the outer
walls because it does not know the mask. `detail::advance_e` gains an overload
taking the mask; the old overload remains the closure-only kernel.

## Benchmark library (`benchmarks/closed.cpp`) and CLI

`--benchmark closed-v1 --suite cavity|cavity-spectrum|pec|smoke --output PATH
[--steps N]` with the REF-04 output lifecycle (fresh directory, provisional
`configuration.json`, streamed `probes.csv` and `diagnostics.csv`,
`metadata.json` after completion, exclusive `COMPLETE.json` with schema
`closed-v1-raw-1`). Fixed suites: `cavity` (30 V04-A cases
`cavity-<x|y|z>-m<nb><nc>-s<1|2|4>` plus `cavity-<x|y|z>-m11-s1-q50`),
`cavity-spectrum` (`spectrum-s1`), `pec` (`pec-c1-<x|y|z>`, `pec-c2-inside`,
`pec-c3-outside`); `smoke` runs `cavity-x-m11-s1`, `spectrum-s1`, `pec-c1-x`
and `pec-c3-outside` with `--steps` (default 2; the self-test uses 4 so that
the recurrence estimator has two rows). Two case kinds exist:

- **Mode** cases initialize the exact discrete standing mode inside a cavity
  of `(12,16,20)*s` cells at origin `origin` (zero for V04-A, three cells for
  V04-C C1, where the `pec_shell` of the cavity box is the only primitive):
  `E_a = A sin(k_b r_b) sin(k_c r_c)` on edges strictly inside the transverse
  cavity ranges with `r_b = (i_b - origin_b) d_b` computed from the integer
  offset first, so the shifted cavity reproduces the open cavity's arguments
  bitwise; `H^(-1/2) = (C E_s) sin(omega_d dt/2)/(mu0 Omega)` from the
  benchmark library's permutation curl. The fixture checks are the masked/
  enclosed exact zeros, the P1-style normalized divergence (E nodes with a
  masked neighbour skipped) and the exact eigenvector identity
  `C*C E_s = |K|^2 E_s` evaluated with the independent curls on every unmasked
  edge, both `<= 1e-11`. The three native lines of V04-A (`E_a` and `H_c`
  along `b`, `H_b` along `c`) are recorded at every state; `steps =
  ceil(2 T_c/dt)`. Mode cases with a shell also write per-state `U`, `Q`, six
  maxima and the region maxima below.
- **Source** cases start from zero fields and drive one `Ez` edge with the
  MAT-01 antisymmetric pulse `g_m` (`M = ceil(6 tau/dt)`, mirrored samples
  cancel bitwise) at `J0 = 1 A/m^2`; `spectrum-s1` records `Ez(7,9,13)` and the
  per-state `U/Q`/maxima for 32,768 steps; C2/C3 record `Ez` at the source and
  one interior/exterior edge for 4,096 steps plus region maxima.

Region maxima classify every sample exactly in doubled cell units against the
closed shell box: `interior` strictly inside, `exterior` strictly outside on
some axis, otherwise `surface` (shell edges and face-normal H). `U` and `Q`
keep the FND-04 outer-wall weights. Metadata add `suite`, `kind`,
`pec_primitives`, `masked_edges`, `closure_edges`, `origin`, `cavity_cells`,
`mode`, `s`, `omega_c`/`omega_d` (deterministic predictions), pulse
parameters, `probe_indices`, `mask_bytes`, and the two fixture maxima. Working
memory is budgeted as two field payloads plus the mask, probes, and the fixed
overhead under 2 GiB.

## Independent analysis and its validation

`scripts/analyze_closed_benchmarks.py --input ROOT --output DIR [--suite]`
reads only the emitted artifacts. It imports the closed-form predictions and
estimators of the MAT-01 audit (`cavity_mode`, `cavity_lines`,
`spectral_peaks`, `project`, `recurrence_frequency`, `pec_marked`), the REF-04
JSON reader and the REF-05 resource check; it imports no solver, fixture, or
diagnostic operator. Its structural audit re-derives extents, CFL, budgets,
closure counts, shell counts (endpoint rule), native times and positions,
per-state probe counts, finiteness, and the partition of the component maxima
by the region maxima. Reductions follow the specification verbatim: V04-A modal
projections on the three prescribed lines, the three-term recurrence
frequency, the amplitude/magnetic/residual limits, refinement per
polarization/mode; V04-B Hann/zero-padded identification on the first 32,768
and 16,384 states with the 0.25-bin, 0.15-height, spurious, continuum and
post-pulse growth (1.5 over the first 4,096 post-pulse states) rules, plus the
post-pulse invariant drift as a reported diagnostic; V04-C exact-zero region
maxima, C1 equivalence with the `cavity-<a>-m11-s1` samples (index shift 3,
`1e-12` normalized, bitwise count reported), the 3,008-edge mask counts, and
finiteness. Outputs are `metrics.json`, `cavity-trace.csv`,
`spectrum-peaks.csv` and `report.md`; the exit status is nonzero on any
failure and outputs are retained. `scripts/run_reference_benchmarks.py` gains
`--benchmark closed-v1`.

`scripts/check_closed_analysis.py` (CTest `reference.closed_analysis`) must
pass before the physical results are interpreted: synthetic exact modes for
all 30 V04-A configurations with estimator deviation `<= 1e-11` and the
injected faults of the specification (frequency `3e-9`, amplitude `3e-9`,
H sign, phase `1e-6`, relocated line, missing sample, extra line, step count,
geometry, mixed times, continuum, refinement order); the V04-B modal-sum
record on both analyses with shifted-line, spurious-line, missing-line,
truncated-record, growth, nonzero-start and nonfinite faults; V04-C synthetic
C1/C2/C3 with nonzero exterior, surface and interior samples, a `1e-11`
interior deviation, a missing reference and a wrong mask count; and, with
`--app`, the four-step smoke suite reproduced by a pure-Python transcription
of the update equations with an independently enumerated mask, the exact mode
fixture, the pulse, `U/Q`, component and region maxima and every probe within
`1e-12`, followed by the analyzer on the smoke cases with the shell case
required to reproduce the open cavity.

## Acceptance fixed before execution

S09 as specified (`reference.pec`); V04-A/B/C limits exactly as fixed in
MAT-01; all fifteen CTests in fresh Debug and Release trees without compiler
warnings; the full V01–V03 suites re-run through the mask-capable kernel
reproduce the tracked REF-05 summary at zero tolerance and the smoke CSV bytes
are unchanged; measured peak memory within 2 GiB. A failure keeps MAT-02 open
with its outputs retained. Passing supports only the PEC-cavity envelope of
the MAT-01 specification: exact-mode resonance at the declared grids, the
driven single-cavity spectrum, and interior shell enforcement.
