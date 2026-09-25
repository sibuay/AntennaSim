# MAT-03 — Per-cell isotropic materials, lossy update, closed-v1 material suites and V05/V06 analysis contract

2026-09-22. I specified this note before writing any MAT-03 code and before
executing any V05/V06 suite. Author review only. The
[MAT-01 method note](MAT-01-closed-domain-conventions.md) fixes the material
model, the edge averaging, the coefficients `Ca`/`Cb`, the lossy energy
identity and the closed-form discrete references. The
[MAT-01 specification](../validation/MAT-01-closed-domain-benchmarks.md) fixes
V05-A/B/C, V06-A/B/C, S10–S13, the analyzer/oracle coverage extensions, the
CLI contract and the resource budget. `scripts/check_material_benchmarks.py`
computes every closed-form prediction. This note records the API, error,
storage, fixture, output and analysis decisions that realize those
authorities. It changes no limit. Evidence goes in
`docs/validation/MAT-03-*.md`.

## Supported scope

The scope is per-cell, isotropic, nondispersive `eps_r >= 1` and constant
`sigma >= 0` with `mu = mu0`, on the unchanged uniform Yee grid, with or
without an explicit PEC mask. A constant `sigma` is **not** a constant
loss-tangent model: `tan(delta) = sigma/(omega eps)` falls as `1/f`. The
update accepts every `sigma >= 0` and every allowed `dt` (the centred
conduction term is dissipative). The *validated* conductivity scope is
`x = sigma dt/(2 eps) <= 0.045`, with the decay-rate error `x^2/3`
tabulated in V06-A. A larger `x` runs but is outside version 1 and must not be
presented as validated. The following are out of scope: magnetic material,
magnetic conductivity, dispersion, anisotropy, subcell or conformal material
boundaries, oblique interfaces, and loss-tangent fitting.

## Material map (`include/antennasim/material.hpp`)

`MaterialMap(const UniformGrid& grid, std::vector<double> eps_r,
std::vector<double> sigma_s_per_m)` owns two per-cell arrays in cell order
`i + Nx (j + Ny k)`. `x` is contiguous, as in the FND-03 field layouts.
Construction validates everything before it stores anything:

- Each vector's length must equal `Nx Ny Nz`.
- Every `eps_r` value must be finite and `>= 1`.
- Every `sigma` value must be finite and `>= 0`.

Any violation raises `std::invalid_argument`, which names the first
offending cell. The vectors are moved in, so the map performs no allocation.
`MaterialMap::uniform(grid, eps_r, sigma)` validates the two scalars **before**
it allocates the arrays. The byte count is computed with the REF-01 checked
arithmetic, so an impossible size is a `std::length_error` and never a wrap.
The accessors are `grid()`, `eps_r(cell)`, `sigma(cell)` (bounds checked),
contiguous `const` spans, and `bytes() = 16 Nx Ny Nz`. A map is solver input
only. It carries no field, clock or fixture.

## Edge coefficients (D023: deduplicated table plus a `uint32` index)

`EdgeCoefficients` realizes the MAT-01 formulas for one map and one validated
`VacuumTimeStep`. It is built only over the E samples in the FND-03 update
ranges. These are the unconstrained edges, including interior PEC-masked edges,
which are skipped at update time. For an `E_a` edge at storage index `(i_a,
i_b, i_c)` (cyclic `a,b,c`), the four neighbouring cells are
`(i_b-1, i_c-1)`, `(i_b, i_c-1)`, `(i_b-1, i_c)` and `(i_b, i_c)` in the
transverse plane at cell `i_a`. The values are summed left to right in that
order and then divided by four:

```text
eps_r,e = (((eps_r,1 + eps_r,2) + eps_r,3) + eps_r,4) / 4
sigma_e = (((sigma_1 + sigma_2) + sigma_3) + sigma_4) / 4
eps_e   = eps_r,e * epsilon0
x_e     = (sigma_e * dt) / (2 * eps_e)
Ca_e    = (1 - x_e) / (1 + x_e)
Cb_e    = (dt / eps_e) / (1 + x_e)
```

The mean is taken over the relative value and multiplied by `epsilon0`
afterwards. Distinct `(eps_r,e, sigma_e)` pairs are deduplicated by their exact
bit patterns in first-seen storage order (`Ex`, `Ey`, `Ez`; `i` fastest).
Each entry stores `eps_r,e`, `sigma_e`, `x_e`, `Ca_e`, `Cb_e` and the number of
update-range edges that use it. Every E sample carries a `uint32_t` table
index. Samples outside the update ranges (the tangential outer walls) hold
index 0 and are never read. `at(component, index)` rejects them with
`std::out_of_range`, as `detail::curl_at` does.

Validation happens entry by entry, before any field is allocated. `x_e`,
`Ca_e` and `Cb_e` must be finite and `Cb_e > 0`. Otherwise the result is
`std::overflow_error`, naming the component and index of the first edge that
produced the entry. Two examples are four cells of `eps_r = 1e308`, whose sum
overflows so that `Cb = 0`, and a `sigma` large enough to make `x` infinite, so
that `Ca` is NaN. More than `2^32 - 1` entries, or an unrepresentable sample
count, raises `std::length_error`. A map whose spacing differs from the time
step's raises `std::invalid_argument`. `VacuumTimeStep` holds only the spacing,
so `EdgeCoefficients` cannot compare cell counts. The stepper rejects a map
whose cells differ from the fields' before stepping (corrected in the
2026-09-25 review; the text first said the coefficients rejected both).

`EdgeCoefficients::vacuum(grid, dt)` is the default. It evaluates the same
formula for `eps_r,e = 1`, `sigma_e = 0` once, which gives exactly `Ca = 1`,
`x = 0` and `Cb = dt/epsilon0`: the same expression and the same rounding as
`VacuumTimeStep::e_scale()`. It then stores a single entry and a zero index,
without a per-cell map. A grid with at least two cell counts equal to 1 has no
update-range edges, and its table is empty. Nothing reads an entry there.
S10 checks that a vacuum `MaterialMap` produces the bitwise-identical table.

Memory (D023): `4 (Nex+Ney+Nez)` bytes of index plus 48 bytes per entry. At the
V05-A/V06-A `p=96` transient, the peak is two field payloads (978.8 MiB), the
PEC byte mask (30.7 MiB), the index (122.6 MiB), the per-cell map (162 MiB) and
the fixed 16 MiB overhead, about **1.28 GiB**. Two doubles per edge would add
490.5 MiB instead of 122.6 MiB, about **1.64 GiB**. Vacuum runs allocate no
map, so V01 at `p=96` peaks at about 1.12 GiB. The MAT-01 budget sentence
("two 489.380 MiB payloads plus the mask") omitted coefficient and map storage.
It is corrected in the specification's resource budget, and every benchmark's
`working_bytes_budgeted` counts it.

## Stepper integration (`include/antennasim/vacuum.hpp`, `src/vacuum.cpp`)

```cpp
ReferenceStepper(const FieldStorage&, VacuumTimeStep);                                  // vacuum, closure
ReferenceStepper(const FieldStorage&, VacuumTimeStep, PecMask);                         // vacuum, mask
ReferenceStepper(const FieldStorage&, VacuumTimeStep, const MaterialMap&);              // closure
ReferenceStepper(const FieldStorage&, VacuumTimeStep, PecMask, const MaterialMap&);
[[nodiscard]] const EdgeCoefficients& coefficients() const noexcept;
```

Every constructor delegates to one private constructor that takes an
`EdgeCoefficients`. The two vacuum forms pass `EdgeCoefficients::vacuum`. The
coefficients are declared, and therefore built and validated, before the owned
`FieldStorage`, so a rejected map or coefficient allocates no field copy. A
map with different cells or spacing from the fields raises
`std::invalid_argument`.

- **Time step.** `VacuumTimeStep` and its CFL policy are unchanged. The
  accepted `dt` for any material is the vacuum value (MAT-01: `eps_r >= 1` and
  a dissipative conduction term keep the FND-03 bound). The stepper computes
  no material-dependent time step.
- **E update (the material kernel).** On every unmasked update-range edge:
  `Enew = Ca_e * E + Cb_e * curl_H`. This uses the unchanged `curl_at`, the
  unchanged loop order and the unchanged nonfinite-result check. The H update
  is unchanged. The build already compiles every target with
  `-ffp-contract=off -fno-fast-math` (Clang/GCC) or `/fp:strict` (MSVC), so no
  fused multiply-add is formed. With `Ca = 1.0` exactly, `1.0*E` is exact and
  the sum is the P1 `E + e_scale*curl` bit for bit. `detail::advance_e(fields,
  dt, n, mask, coefficients)` is the new kernel overload. The P1 vacuum
  overloads remain unchanged as independent references for S09/S10.
- **Impressed current.** After the E loop, `E <- E - Cb_e * (amplitude * J)`.
  This keeps the REF-04 form, with `Cb_e` of the target edge in place of
  `e_scale`. The pre-mutation finiteness check uses `Cb_e * (amplitude*J)`.
- **Initial screening.** Finiteness, masked-E and enclosed-H zeros, and the H
  divergence are unchanged. The E divergence screening becomes the discrete
  Gauss law `div(eps_r,e E) = 0` at nodes whose six E samples are unmasked,
  using each edge's `eps_r,e` from the table. The tolerance is unchanged and
  is relative to `sum |eps_r,e E / d|`. In vacuum `eps_r,e = 1.0` exactly, so
  the screening arithmetic and decisions are those of P1. This is the physical
  rho=0 condition with materials: an E field that is divergence free across a
  dielectric interface carries surface charge and is rejected, while a field
  with continuous normal D is accepted. After the first step, charge follows
  discrete continuity and conductive relaxation. No charge is stored or
  projected.

## Structural tests (S10–S13; CTest)

One executable, `tests/material_check.cpp`, holds four independently written
groups, each registered as its own CTest (`reference.material_map` S10,
`reference.material_update` S11, `reference.material_timestep` S12,
`reference.material_dissipation` S13). The pure-Python generator
`scripts/generate_material_steps.py` (CTest `reference.material_steps`)
produces the S11 two-step golden states in exact rational arithmetic, starting
from the binary64 inputs, and checks that the committed header matches. No
production rule serves as its own oracle:

- **S10.** On `(2,3,4)`, the per-cell map uses the S05 modular value
  `v = max(0, ((17i+31j+43k) mod 101) - 50)` with `eps_r = 1 + v/60` and
  `sigma = v/50`. The specification's "clipped at 0" applies to the value, the
  only reading that keeps `eps_r >= 1`. Every edge's table entry must equal the
  test's own four-cell enumeration within `1e-15` relative. The per-entry edge
  counts must equal the enumeration. A vacuum map must give `Ca = 1` and
  `Cb = dt/epsilon0` bitwise and equal `EdgeCoefficients::vacuum`. Rejected:
  `eps_r < 1`, `sigma < 0`, NaN and infinity in either array, wrong lengths,
  and a map on a mismatched grid. The material kernel with vacuum coefficients
  must be bitwise equal to the P1 kernels (closure and masked), and the stepper
  with a vacuum map must be bitwise equal to the P1 constructors.
  Added in the 2026-09-25 review:
  - Two more maps whose `sigma` does not follow `eps_r` (constant `eps_r = 4`
    with varying `sigma`, and unrelated modular values). In the modular map,
    equal `eps_r,e` implies equal `sigma_e`, so a table key that ignored
    `sigma` passed every check.
  - The driven stepper compared bit for bit, with bit-pattern equality, against
    a transcription of the P1 step: the P1 kernels, then
    `E <- E - e_scale*(amplitude*J)`, with drive values that are not binary
    fractions. Every constructor now shares the material kernel, so the
    stepper forms agree with one another by construction.
- **S11.** A single edge with prescribed `eps_e`, `sigma_e`, curl and `J`:
  `Enew` must equal the independent formula for `x_e` in `{0, 0.01, 0.045,
  0.5}` within `1e-13` normalized. Then two full lossy steps on `(5,4,3)` with
  spacing `(2,3,5)` m, with the S10 map and a D-compatible fixture
  `E = (C* P)/eps_r,e`, must match the exact-rational transcription within
  `1e-13` normalized per component.
- **S12.** The accepted `dt` equals the vacuum value for a material grid, and
  the stepper's `time_step()` is unchanged. `eps_r < 1` is rejected by
  `MaterialMap::uniform` on a grid whose arrays could not be allocated
  (`std::invalid_argument`, not an allocation error). Coefficient overflow
  (`eps_r = 1e308`) and nonfinite `x` are rejected with `std::overflow_error`
  before stepping.
- **S13.** On the S05 modular E/H fields with the S10 map and the outer
  closure, one step through the detail kernels must satisfy
  `abs(Q_(n+1) - Q_n + D_n) <= 1e-12 * sum of absolute terms`. Q uses
  eps-weighted `U` minus the cross term. `D_n = dV dt <sigma_e Ebar, Ebar>_w`.
  The test computes everything with its own differences and averages. The
  specification writes `max(1, sum)` "in chosen test units". A sum-relative
  limit is at least as strict.

The fifteen existing CTests remain unchanged and must keep passing.

## Benchmark library and CLI (`benchmarks/material.{hpp,cpp}`, `closed-v1`)

`--benchmark closed-v1 --suite dielectric|interface|slab-cavity|lossy|dissipation`
joins the existing `cavity|cavity-spectrum|pec|smoke` suites. They have the same
REF-04 output lifecycle, the same schema (`closed-v1-raw-1`), a fresh
directory, streamed CSV, metadata written after completion and an exclusive
`COMPLETE.json`. Role axes `(a,b,c)` are as in the specification. Every
fixture is the exact discrete one, and every prediction is a deterministic
calculation that the analyzer recomputes independently.

| Suite / cases | Names | Fixture |
| --- | --- | --- |
| `dielectric` / 18 | `dielectric-<ab>-p<24,48,96>`, six orderings | V01 primary grid, uniform `eps_r = 4`. FND-04 compact potentials with `E_b = A cos(k r_a)` and `H_c = s (1/eta) cos(k r_a + omega_d dt/2)` in the plateau, where `eta = eta0/2`, `omega_d = (2/dt) asin(c0 dt K/(2 sqrt(eps_r)))` and `N = floor(0.1 sqrt(eps_r) lambda/(c0 dt))`. The V01 isolation guards apply. |
| `interface` / 7 | `interface-<a>-p<16,32>` for `a` in x,y,z; `interface-x-p64` | `v05b_geometry`. Cells with `i_a >= i_int` have `eps_r = 4`. Zero fields. `J_b = sin(pi i_c/N_c)` on every `E_b` edge of the plane `i_src` (both `b` planes), with half-time amplitudes `gaussian_pulse(dt, N)` applied at every step. |
| `slab-cavity` / 18 | `slab-<a>-m<1,2>-p<24,48,96>` | `v05c_geometry` (`d_b = 2 lambda0/p`; see the V05-C erratum). `eps_r = 4` for `i_a >= p/2`. `E_b = A e[i_a] sin(pi i_c/N_c)` on both `b` planes, with `e` the discrete eigenvector at the root `f_d` of `slab_discrete` (bisection inside the generator). `H^(-1/2) = (C E_s) sin(omega_d dt/2)/(mu0 Omega)`. `N = ceil(2/(f_c dt))` with `f_c` the continuum root. |
| `lossy` / 26 | `lossy-<ab>-p<24,48>-sig0p01`/`-sig0p1`, six orderings; `lossy-xy-p96-sig0p01`/`-sig0p1` | The `dielectric` grid, `eps_r = 4`, uniform `sigma`. Exact lossy eigenwave: `E_b = A cos(k r_a)` and `H_c = s abs(h) cos(k r_a + phi)` at `-dt/2`, with `h = hhat z^(-1/2)`, `hhat/A = (i dt K/mu0)/(z^(1/2) - z^(-1/2))` (principal root), `phi = -arg(h)` and `z` the root of the MAT-01 quadratic with positive imaginary part (`lossy_step_root`). |
| `dissipation` / 2 | `dissipation-q99`, `dissipation-q50` | V03 normalized modular fixture on `(12,14,16)`, `(0.01,0.015,0.02)` m, uniform `eps_r = 2.25`, `sigma = 0.01` S/m, 2000 steps. The six centre probes and the per-state diagnostics are recorded. |

**Fixture checks.** These are recorded in metadata and fail the case before any
step, at `1e-11`:

- the P1 normalized divergence with the eps-weighted E form;
- for waves, the plateau of the prescribed E and H values;
- for the slab, the eigen identity `C* C E_s = mu0 eps_e Omega^2 E_s` per
  unmasked edge, normalized by `mu0 eps_e Omega^2`, with `eps_e` from the
  benchmark library's own four-cell averaging.

A check that does not apply to a kind is written as `0`: the plateau error
outside the wave kinds, and the eigen error outside the slab. The divergence
check runs on every case. It cannot fail for the five version-1 fixtures:
- the waves and the modular field are curls in a uniform medium;
- the interface starts from zero fields;
- the slab has only `E_b`, which does not vary along `b`.

So it would detect only a gross construction error. Both points were recorded
in the 2026-09-25 review.

**Probes.** Waves record the six V01 native lines (`6p` samples) at every
state. The interface records the `E_b` line along `c` at `(i_p1, j=0)`
(`N_c + 1` samples, which include probe 1 at `N_c/2`) and `E_b` at
`(i_p2, 0, N_c/2)`, `(i_p1, 1, N_c/2)` and `(i_p2, 1, N_c/2)`, all **at every
state**. Revision 1.4 requires every state to record the same keys. This is a
superset of the version-1 "every 64 states" line, so the purity limit applies
at every recorded state. The slab records the `E_b` line along `a` at
`(j=0, i_c=N_c/2)`, from `i_a = 0` to `N_a`. Dissipation records the six
centre samples.

**Diagnostics** (`diagnostics.csv`) are recorded for `dissipation`, and in
`smoke` for every material case. They are computed by the benchmark library
with its own permutation differences, its own four-cell edge averages and
compensated sums:

- `U_J = dV/2 (epsilon0 sum w eps_r,e E^2 + mu0 sum w H^2)`;
- `Q_J = U_J - dV dt/2 sum w H (C E)`;
- `D_J` on row `n` is the dissipation `D_(n-1) = dV dt sum w sigma_e Ebar^2`
  of the step that produced state `n`, with `Ebar` the mean of the retained
  previous E and the current E; it is `0` on row 0;
- the six component maxima.

The existing V04 cases keep their vacuum diagnostic expression unchanged, so
their output stays bitwise identical.

**Metadata** keeps every existing closed-v1 field. Each new kind has a pinned
`initialization` and `source` description. Every case, including V04, adds:

- `materials`: the rule text, the distinct per-cell `(eps_r, sigma)` pairs with
  cell counts, and `map_bytes`, which is 0 for the vacuum default;
- `coefficients`: the solver's table at 17 digits. Each entry holds the edge
  `eps_r,e`, `sigma_e`, `x`, `Ca`, `Cb` and its edge count, written as the keys
  `eps_r`, `sigma_S_per_m`, `x`, `Ca`, `Cb` and `edges`. The table also carries
  `index_bytes`, `table_bytes` and the `provenance` text of the formulas above;
- `diagnostic_bytes`;
- the kind-specific quantities: `omega_d`, `z`, `h`, `phi`, `f_d_hz`, `f_c_hz`,
  `i_int`, `i_src`, `i_p1`, `i_p2` and `gate`.

The emitted key names are given as the code writes them (the version of this
note before the 2026-09-25 review read `eps_r_e`, `sigma_e`, `f_d` and `f_c`).

**Working memory.**
`working_bytes_budgeted = 2 field payloads + mask + map + 4 E-count + table
allowance (48 bytes times the distinct-pair bound) + probes + currents +
retained previous E (dissipation diagnostics) + 16 MiB`.
The preflight rejects anything above 2 GiB. `reference-v1` now counts the mask
and the vacuum index that its stepper allocates, as MAT-02 noted it should. Its
probe/diagnostic CSV bytes are unchanged (V06-C).

**Smoke.** `smoke` adds `dielectric-xy-p24`, `interface-x-p16`,
`slab-x-m1-p24`, `lossy-xy-p24-sig0p1` and `dissipation-q99` to the four V04
cases, at `--steps` (default 2; the self-test uses 4). The smoke material
cases record diagnostics so that the oracle checks `U`, `Q`, `D` and the
maxima on nonuniform and lossy maps.

## Independent analysis (`scripts/analyze_closed_benchmarks.py`)

The analyzer reads only artifacts. Its V05/V06 reductions live in
`scripts/material_reductions.py`. It imports the closed-form predictions of
the MAT-01 audit (`v01_like`, `v05b_geometry`, `gaussian_pulse`,
`discrete_reflection`, `beta_continuum`, `reduced_wavenumbers`, `dft_at`,
`v05c_geometry`, `slab_discrete`, `slab_continuum`, `roots`, `lossy_step_root`,
`kappa`, `project`, `recurrence_frequency` and the fixed caps) and the REF-05
estimators `fit_harmonic` and `native_impedance`.

**Structural audit.** It is extended with:

- the new kinds and their pinned descriptions;
- the `D_J` column;
- the budget floor with map and coefficient bytes;
- the coefficient table checked against an **independent analytic edge
  count**: a uniform map gives one entry over all update-range edges, and a
  material plane at `i_int` gives the three classes vacuum/mean/`eps_r = 4`
  with closed-form counts per component;
- entry values recomputed from the formulas (`<= 1e-15` relative; the vacuum
  entry exact).

Retained V04 raw evidence without these fields stays auditable. They are
required only for the new kinds.

**Reductions.** These follow the specification:

- **V05-A.** REF-05 V01/V02 fits with `K`, `p` samples, floors `0.5 A` and
  `0.5 A/eta`, `omega_m = arg(C_N/C_0)/(N dt)`. Limits: continuum cap;
  discrete, amplitude, residual and inactive lines `<= 1e-9`; complex
  impedance `abs(Z/(s eta) - 1) <= 1e-8` at every state; refinement per
  ordering (strictly decreasing, orders in `[1.8, 2.2]`).
- **V05-B.** `R_m` and `T_m` from the incident `[1, n_g]`, reflected
  `[n_g+1, N]` and transmitted `[1, N]` windows at the 21 band frequencies.
  Limits: continuum, discrete and `Im R`; purity at every state. The purity
  residual is normalized by `max(abs(a_n), 1e-4 peak)` under specification
  revision 1.5, added 2026-09-23 after the first measurement (D025). An
  all-zero record (`peak = 0`) passes only with zero residual. The version-1
  value divided by `abs(a_n)` stays in the report. Any non-finite line or
  point sample fails the case (added in the 2026-09-25 review). Also: exact `b` invariance; orientation agreement
  at `p = 16` and `32` within `1e-12` normalized by the x-orientation maximum;
  refinement of the x-orientation band-maximum continuum error. That error is
  the larger of the R and T errors, which are equal for this real, lossless
  interface.
- **V05-C.** Projection of the `a` line onto the analyzer's own eigenvector
  `e[i]` at its own root, then the recurrence frequency. Limits: continuum
  cap; discrete, amplitude and residual `<= 1e-9`; refinement per mode and
  orientation.
- **V06-A.** V01 fits at every E state; `rho_n = C_(n+1)/C_n`;
  `abs(rho_n/z - 1) <= 1e-9` at every step; `rho_m` their mean;
  `decay_m = -ln abs(rho_m)/dt` and `phase_m = arg(rho_m)/dt` against `alpha`
  and `omega'` caps; floor `abs(C_n) >= 0.5 A`, conditioning, sample counts
  and inactive lines as in V01. The magnetic-line ratio is reported. Decay and
  phase refinement orders must lie in `[1.8, 2.2]` wherever a sequence exists:
  both orders for `xy`, and the 24/48 order for the other orderings, which the
  specification runs at two resolutions. The H-line fit floor is the V01
  `0.5 A/eta`. The analyzer used `0.25 A/eta` until the 2026-09-25 review.
  The smallest measured H amplitude is `0.760 A/eta` (`lossy-xy-p96-sig0p1`),
  so no result changes.
- **V06-B.** Balance `abs(Q_(n+1) - Q_n + D_n) <= 1e-8 Q_n` wherever
  `Q_n > 0`; `Q_(n+1) <= Q_n (1 + 1e-12)` at every state; `D_n >= 0`; the
  two-sided bounds with `1e-8 Q_0`; finiteness; `Q_N/Q_0 <= 1e-4`. The last is
  applied as a limit and its value is reported. Until the 2026-09-25 review the
  analyzer applied the monotonicity check only where `Q_n > 0`. Every measured
  `Q_n` is positive, so no result changes.

Every limit comparison is written so that a NaN fails, and every maximum keeps
a NaN (the built-in `max` can drop one). This was completed in the 2026-09-25
review. Before it, a NaN inactive-line sample or a NaN time step could leave a
case marked as passing, although the suite still failed through the
structural audit.

Outputs gain `material-trace.csv`. `--suite` accepts each suite name, `v04`
(the three V04 suites) and `materials` (the five V05/V06 suites). The material
limits are written to `thresholds` only when a material suite is analyzed, so a
V04-only re-analysis stays key-for-key comparable with the MAT-02 summary. The
exit status and output retention are unchanged.

**Self-test** (`scripts/check_closed_analysis.py` with the material part in
`scripts/check_material_analysis.py`, CTest `reference.closed_analysis`). It must pass before any V05/V06 result is
interpreted. It adds synthetic series built from the closed forms for every
new observable, with these injected faults detected:

- V05-A: frequency, amplitude, impedance sign/phase, inactive leak, refinement.
- V05-B: gate shift, magnitude, phase, `Im R`, `b`-plane mismatch, purity,
  orientation mismatch, refinement.
- V05-C: frequency, amplitude, wrong shape, refinement.
- V06-A: decay, growth factor, and the lossless-initialization transient
  `(z0 - x)/(1 + x)`.
- V06-B: balance, monotonicity, negative `D`, bound and final-energy faults.
- Coefficient-table faults: a wrong count, value or entry.

The 2026-09-25 review found six enforced checks that no fault exercised. It
added faults for them, and a mutation run confirmed that removing any of these
checks now fails the self-test:
- the V05-B continuum `abs(R)`/`abs(T)` cap and the second-plane (`p1b`)
  invariance;
- the V06-A phase cap;
- the fit-residual limit;
- the V05-A H amplitude;
- the V06-B lower energy bound.

It also added faults for the corrections above:
- an invariant that reaches zero and reappears;
- an H line under the `0.5 A/eta` floor;
- NaN inputs;
- empty orientation records.

With `--app`, a pure-Python oracle is extended with independently averaged
per-cell materials, the lossy coefficient update, `D`, and independent
transcriptions of the wave, sheet, slab and modular fixtures. It must
reproduce every probe and `U`/`Q`/`D`/maxima of the new smoke cases within
`1e-12` relative at every smoke state, and the existing four within the same
limit.

## Acceptance fixed before execution

Acceptance requires all of the following:

- S10–S13 as specified.
- All twenty CTests (the fifteen existing, plus S10–S13 and the golden-state
  check) pass in fresh Debug and Release trees without compiler warnings.
- V05-A/B/C and V06-A/B meet the fixed MAT-01 limits from the clean Release
  build.
- V06-C holds: the full V01–V03 suites reproduce the tracked REF-05 summary at
  zero tolerance through the material-capable kernel, apart from the source
  fingerprint, and the reference-v1 smoke CSVs are byte-identical to those of
  the MAT-02 build.
- V04 is re-run and re-analyzed from the same build.
- Measured peak working set stays within 2 GiB for every suite.

A failed criterion keeps MAT-03 open and its outputs are retained. No
tolerance is widened. Passing supports only the declared envelope:
grid-aligned planar dielectric interfaces with node averaging, homogeneous
lossless and lossy eigenwaves with `x <= 0.045`, the TE slab cavity, and the
closed-grid dissipation identity, at the declared grids and durations.

## Specification errata and clarifications (no limit changes)

- **V05-C spacing.** The specification text gives `(1, 1.5, 1) lambda0/p`.
  The audit's `v05c_geometry`, which produced every tabulated prediction and
  cap, uses `(1, 2, 1) lambda0/p`. With 1.5, mode 1 at `p=24` would predict
  3.093e-4 and 225 steps, instead of the tabulated 2.981e-4 and 216. The
  fixture follows the audit, and the specification text is corrected. This was
  confirmed by the owner on 2026-09-22.
- **V05-B line cadence.** Recorded at every state, as above. Confirmed by the
  owner.
- **Budget.** Coefficient and map storage are added to the MAT-01 transient
  (D023).
