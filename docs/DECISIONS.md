# Decision log

Recorded: 2026-09-05. Decisions below derive from the vision and the planning
baseline. They do not imply completed implementation.

## Accepted direction

| ID | Decision | Rationale and consequences | Revisit trigger |
| --- | --- | --- | --- |
| D001 | Begin with a C++20, uniform Cartesian 3D Yee FDTD CPU reference and CMake | Matches the vision; preserves a clear numerical baseline; Python supports analysis rather than hot solver loops | A documented toolchain or numerical constraint |
| D002 | Advance through evidence-based phase gates | Accuracy and reproducibility control readiness | Process revision supported by experience, without weakening numerical evidence |
| D003 | Keep solver, project data, UI, and AI separate | Solver outputs stay traceable; headless validation remains possible | Refine concrete interfaces as actual use cases appear |
| D004 | Preserve permanent analytical/reference regressions and CPU reference | Optimization requires numerical comparisons; reference provenance must be maintained | Extend the suite with every supported numerical capability |
| D005 | Use milestone-based work packages with no assumed dates, durations, or capacity | Explicit owner preference; reviews follow session, item, cycle, and phase events | Owner explicitly requests a time-based schedule |
| D006 | Keep planning and handoff records in repository Markdown | Reviewable, readable, and available to future work sessions without an external service | Team/project tooling needs justify a migration with preserved history |
| D007 | Defer detailed work breakdowns for distant phases | Early solver accuracy, reference access, and compute cost are unknown | Preceding phase passes and later work can be bounded |
| D008 | Use project-local LLVM-MinGW 20250613 / Clang 20.1.7, CMake/CTest 3.31.10, and Ninja package 1.11.1.4 | No working system C++ toolchain was found; avoids system repair and global package changes; Debug/Release scaffold checks pass | New platform, compiler issue, or CUDA host requirements |
| D009 | Start with CTest and small standalone test executables; disable fast math/contraction on Clang/GCC targets | No external C++ framework is needed for foundation checks; establishes an explicit initial floating-point policy | Numerical test complexity warrants a framework, or a documented method requires a policy revision |
| D010 | Use SI binary64 fields, six component-specific x-contiguous Yee arrays, E at integer times/H at half times, and a provisional zero-tangential-E box; default CFL fraction 0.99 with strict fraction <1 | Makes P1 storage, signs, updates, and failure behavior explicit; boundary reflects and requires isolated propagation measurements; see FND-03 method/review | Benchmark specification reveals an inconsistency, or later PEC/material/boundary phases require a documented extension |
| D011 | Fix V01–V03 version-1 benchmarks and S01–S08 structural checks before solver implementation | Compatible discrete-curl initial data and all-face dependency guards isolate native-sampled propagation/impedance; modified-energy diagnostics test closed-grid stability; see FND-04 specification/review | A documented analytical flaw or measurement limitation; preserve old limits and failed evidence before any revision |
| D012 | Use validated grid value types, integral-only counts, standard exception categories, and checked allocation/geometry limits | REF-01 rejects bad geometry and sizes before field allocation; six exact layouts remain independent of storage, CLI, and solver updates; see REF-01 contract/evidence | A supported use case requires different limits, error transport, or coordinate representation |
| D013 | Keep REF-02 field ownership fixed; expose checked sample access and const contiguous views; classify walls on the validated grid without enforcing them in storage | Prevents shape/storage mismatch and implicit large copies; coordinate and wall checks can run without field allocation; physical initialization and boundary evolution remain kernel/run responsibilities | A concrete run/checkpoint/transfer or profiled iteration requirement needs a broader owner/access API |
| D014 | Use validated vacuum time-step values and an owned source-free reference stepper with explicit initial copying, divergence/wall screening, and terminal in-place update failure | Pins constant/spacing/time conventions; protects active fields from external mutation; fails with state/component/index instead of exposing a successful partial step; independent local kernels and Fraction states validate implementation | REF-04 current/run requirements, checkpoint needs, or measured performance/representability limits justify a documented extension |
| D015 | Use validated sparse impressed currents, native probes, separate fixed benchmark runners and streamed CSV/JSON with exclusive completion markers | Preserves initial rho=0 screening, defines later charge by continuity, retains failed evidence and distinguishes raw completion from physical acceptance; see REF-04 contract/evidence | General project/source/charge requirements or measured resource constraints |
| D016 | Use GitHub for source control and required Debug/Release CI; make Python audits fail closed and retain compact validation evidence | Keeps reviewed snapshots bisectable, prevents reduced suites from passing silently, and makes local/remote evidence inspectable without tracking large generated arrays | Host, runner, dependency, retention, or distribution requirements change |
| D017 | Evaluate physical acceptance only through an independent artifact analyzer whose reductions are validated by synthetic fault injection and a separately transcribed oracle before results are read; run full suites manually from clean Release builds, keep smoke-length reductions in CTest/CI | Separates solver output from its judgement, catches analysis defects before they can mask or fabricate a pass, and keeps the fast suite bounded; see REF-05 contract/evidence | Suite runtime, hosted-runner capacity, or a new observable that the synthetic/oracle coverage does not exercise |
| D018 | Fix the P2 conventions before any P2 code: per-cell isotropic `eps_r>=1`/`sigma>=0` with `mu0`, four-cell arithmetic edge averaging, time-centred conductivity coefficients that reproduce the vacuum kernel bitwise, the unchanged vacuum CFL policy justified by the eps-weighted dissipation identity, E-edge PEC masks with the outer closure as a special case, `exp(-i omega t)*dt` transforms with rectangular/Hann windows, and closed-form discrete comparators for V04–V07 | Keeps P1 evidence valid by construction, makes implementation and discretization errors separable, and fixes caps from exact predictions with a 24–35 percent margin; see the MAT-01 method note, specification and review | A material, boundary, or spectral requirement outside the declared scope (magnetic or dispersive media, subcell conductors, constant loss tangent, oblique interfaces) or a failed P2 measurement that traces to a convention rather than an implementation |
| D019 | Represent PEC as an owned per-E-sample byte mask inside the reference stepper (outer closure always present, `pec_box`/`pec_shell` primitives by exact index arithmetic), screen initial data on masked E and enclosed H samples, skip masked edges in the unchanged FND-03 update ranges, reject currents on masked edges at the step, and keep the V04 evidence in a separate `closed-v1` benchmark library with an independent analyzer that imports the MAT-01 audit's closed-form predictions | Keeps the vacuum arithmetic bitwise identical (closure-only mask performs the same operations), makes enforcement exact rather than approximate, keeps solver code free of fixtures/CLI, and lets a V04 failure be attributed to implementation (discrete comparators) or discretization (continuum caps); see the MAT-02 contract and evidence | A conductor model that is not a set of full E edges (thin sheets, subcell/conformal surfaces, finite conductivity), a memory constraint that requires a bit mask, or a measured V04 failure traced to the mask semantics |
| D020 | Require the V04-C driven cases to carry their pulse, not merely stay finite: the first electric state of the driven region equals the closed-form deposit `(dt/eps0) g_0` within 1e-12 with the rest of that region exactly zero, its peak reaches 0.1 of the largest single-step deposit, and the invariant `Q` is zero at state 0, positive after the pulse and constant to 1e-12 (MAT-01 specification revision 1.2) | A criterion satisfied by a run that injected nothing cannot distinguish enforcement from inaction; the deposits come from the specification audit, so acceptance stays independent of solver output, and the smoke path now fails a driven case that stops carrying its pulse; see D020 detail and the MAT-02 addendum | A driven closed-domain case whose source is not a single prescribed edge current, or an update ordering in which more than the driven edge moves at state 1 |
| D021 | Name the component and the edge in the V04-C driven acceptance: the first deposit is required in `Ez`, with every other component zero at state 1 in the driven region and over the whole domain, and the native `Ez` sample of the prescribed source edge must equal the signed `-(dt/eps0) J0 g_0` at state 1 while the other prescribed probes stay zero (MAT-01 specification revision 1.3); pin the emitted `initialization` description to the specified form, admitting the one historical mode string only with the source snapshot that emitted it | Region maxima are unsigned and carry no location, so revision 1.2's largest-of-three comparison accepted an `Ex` deposit and no requirement referred to the driven edge; the probe record already contains the source edge, so the stronger check needs no new observable and no solver output; pinning the description keeps a run reproducible from its own metadata without rewriting retained raw evidence | A driven case whose source component or edge is not fixed by the specification, or a second historical metadata string that has to be admitted |
| D022 | Require the probe record to be complete rather than uniform: every state must record the same set of probe keys, a source case must record exactly the `Ez` edges its own `probe_indices` declares, the C2/C3 declared and recorded sets must equal the version-1 fixture sets computed by the specification audit, and a reduction must read a prescribed sample as present rather than defaulting an absent one to zero (MAT-01 specification revision 1.4) | Counting rows per state accepts a prescribed probe that is absent from every state, because the count stays uniform; a defaulting lookup then silently converts the missing measurement into a passing zero, so deleting a whole probe left both the audit and the reduction passing | A case whose recorded probe set legitimately varies between states, which no closed-v1 case does |
| D023 | Store the MAT-03 edge coefficients as a deduplicated table of `(eps_r_e, sigma_e, x, Ca, Cb)` entries plus one `uint32` index per E sample, rather than two doubles per edge; count the index, the table, the per-cell map and the retained previous E in every benchmark's `working_bytes_budgeted`, and correct the MAT-01 transient budget, which counted only two field payloads and the mask | At `p=96` the V05-A/V06-A transient is 1.279 GiB instead of 1.639 GiB (payloads 978.8 MiB, mask 30.7 MiB, index 122.6 MiB against 490.5 MiB of per-edge doubles, map 162 MiB), leaving margin under 2 GiB; version-1 fixtures have at most three distinct entries; vacuum stays one entry with no map (V01 `p=96` 1.121 GiB). Confirmed by the owner on 2026-09-22; see D023 detail and the MAT-03 contract | A material description with more than `2^32 - 1` distinct edge pairs or a measured table/index cost that matters (for example a smoothly graded map), or a backend that prefers per-edge arrays |
| D024 | Route every `ReferenceStepper` constructor through one material kernel `Enew = Ca*E + Cb*curl H` with `EdgeCoefficients::vacuum` as the default; validate a `MaterialMap` (per-cell finite `eps_r>=1`, `sigma>=0`, exact shape) and the coefficients (finite, `Cb>0`) before any field copy; keep the vacuum CFL policy; screen initial E by the discrete Gauss law `div(eps_r,e E)=0`; keep the V04 diagnostic expression and add eps-weighted `U`/`Q` and the step dissipation `D` for material cases in the benchmark library; record the V05-C spacing, V05-B line-cadence and S10 clipping errata without changing any limit | Vacuum arithmetic stays bitwise P1 (`Ca=1.0` exactly, `Cb=dt/epsilon0` by the `e_scale` expression, no contraction), so V01–V04 evidence stays valid by construction and is re-checked at zero tolerance; `div E=0` across a dielectric interface is a surface charge, while `div(eps E)=0` is the physical rho=0 state and is identical to P1 in vacuum; see D024 detail and the MAT-03 contract | A magnetic, dispersive or anisotropic material, subcell interface treatment, a material requiring a rederived CFL bound (`eps_r<1`), or a user workflow needing charged initial states |
| D025 | Normalize the V05-B mode-purity residual by `max(abs(a_n), 1e-4 max_n abs(a_n))` (MAT-01 revision 1.5) instead of by `abs(a_n)` alone, and adopt the general rule that a criterion failing only through measurement ill-conditioning is fixed by an absolute floor derived from the roundoff scale, with detection power demonstrated by injected faults and the failing result preserved, never by a looser limit | The version-1 rule demanded precision below binary64 roundoff at carrier zero crossings (failed at 2/7/28 states with the residual at most 1.7e-15 of the record peak); the floor keeps the 1e-9 limit at states with abs(a_n) >= 1e-4 peak (about 58% of states) and bounds the other 42% by 1e-13 of the peak (worst measured 1.58e-11, about 60x margin), which between 2.2e-7 and 1e-4 of the peak is looser than version 1 by up to about 450x (scope stated after review on 2026-09-25); decided by the owner's delegation on 2026-09-23; see D025 detail | A V05-B defect visible only below 1e-4 of the peak, or another relative criterion whose normalizer can vanish |

## Open decisions

Resolve each choice by its need-by point. Record options, selected approach,
numerical implications, validation plan, and maintenance consequences. Routine
choices can be made during authorized implementation; ownership here identifies
responsibility rather than introducing approval requirements.

| ID | Question | Need by | Responsible role / next step |
| --- | --- | --- | --- |
| O005 | Which project license and distribution policy should be used? | Before external distribution | Project owner sets distribution intent; source control and CI are resolved by D016 |
| O006 | Which trusted reference solver/data are accessible, reproducible, and suitable for dipole/patch comparisons? | P4/P6 benchmark specifications | Collaborator inventories accessible references; owner resolves access needs |
| O007 | Which absorbing boundary formulation and supported test envelope will be used? | P3 implementation | Collaborator: method/reference study after P2 gate |
| O008 | Which persistent project schema and large-result format should be used? | Persistent benchmark/user project implementation, no later than P6 | Collaborator: evaluate reproducibility, versioning, partial reads, and data sizes |
| O009 | Which CAD/UI/rendering dependencies are justified? | P10/P11 | Collaborator: evaluate Qt/OpenCASCADE/VTK or alternatives against measured needs and licensing |
| O010 | What CPU/GPU hardware and memory budgets should performance phases target? | P8/P9 planning | Collaborator records measurements; owner supplies target hardware priorities |

Add new decisions when needed. Do not preselect every long-term library during
foundation work.

O001 was resolved by D008/D009 on 2026-09-05. See
[environment observations](ENVIRONMENT.md) and [build evidence](validation/FND-02-build.md).
The local toolchain selection did not settle numerical conventions, benchmark
tolerances (O003), or future CUDA host compatibility.

FND-05 reviewed the remaining open decisions on 2026-09-06: none is due before
P1. The [P0 gate record](validation/FND-05-foundation-gate.md) accepts the
foundation and makes REF-01 ready under D001–D011, without changing architecture
or tolerances. The same-author review and approved-execution limitations remain
explicit; no new numerical capability is claimed.

REF-06 reviewed them again on 2026-09-17: none is due before P2. O007 (absorbing
boundary formulation) is needed for the P3 breakdown that the P2 gate (MAT-05)
must produce, so its method/reference study is due at that gate. The
[P1 gate record](validation/REF-06-reference-propagation-gate.md) passes Phase 1
under D010–D017 without a new decision; it fixes no P2 method or tolerance.
MAT-01 (2026-09-18) adds D018; none of O005–O010 is due before MAT-02.
MAT-02 (2026-09-18) adds D019; none of O005–O010 is due before MAT-03.
MAT-03 (2026-09-23) adds D023, D024 and D025; none of O005–O010 is due before MAT-04.

## D025 detail — V05-B mode-purity normalization (revision 1.5) on 2026-09-23

Status: implemented; the retained raw run was re-analyzed under it and passes.
See the [MAT-01 specification](validation/MAT-01-closed-domain-benchmarks.md)
(V05-B) and the [MAT-03 evidence](validation/MAT-03-dielectric-conductivity.md).

The first V05-B measurement failed the version-1 purity rule in all seven
cases, with a worst value of 1.28e-7 against 1e-9. Every other V05-B limit
passed. The failing states are the few where the TE_1 amplitude at probe 1 is
below 1e-6 of the record peak. Against the peak, the residual is at most
1.7e-15 in every amplitude band, which is roundoff carried by other transverse
modes.

Options considered:

- Evaluate only every 64th state, as the version-1 cadence did. It passes with
  a worst value of 9.1e-10, but the margin depends on where the samples fall.
- Leave MAT-03 open.
- Normalize by `max(abs(a_n), 1e-4 peak)`.

The owner delegated the choice on the condition that it resolve the failure
without lowering the quality bar, and asked that the principle apply to future
work.

Chosen: the floor. It is derived from `eps * peak` with a margin of about 500
for accumulation. The version-1 limit is unchanged at states with
`abs(a_n) >= 1e-4 peak`, and weaker states are bounded by `1e-13` of the peak.
Self-test faults show detection at `2e-9 a_n` for strong states and at
`3e-13 peak` for quiet ones.

Scope, stated after review on 2026-09-25: the floor applies at about 42% of
the recorded states (256 of 612, 513 of 1222 and 1026 of 2442), not only at
the 2, 7 and 28 that failed. Of these, 33, 65 and 129 have exactly zero
amplitude before the pulse arrives. In the band from `2.2e-7` to `1e-4` of the
peak (218, 431 and 856 states) the check is looser than the version-1
relative limit by up to about 450 times. The first text of this record said
the version-1 limit was unchanged "wherever the amplitude is resolvable",
which overstated it. Version 1 also exceeded `1e-9` at a few states above
`2.2e-7` of the peak (at most `5.05e-9`), because the accumulated roundoff,
about `1.7e-15` of the peak, is larger than one rounding. The decision and
the pass stand.

The worst value becomes 1.58e-11. The version-1 value is still reported, and
the failing analysis is retained. The failure-handling section of the
validation plan now states the general rule.

Revisit if a V05-B defect shows up only below `1e-4` of the peak, or if a
future relative criterion has a normalizer that can vanish.

## D024 detail — MAT-03 material stepping, screening and diagnostics on 2026-09-23

Status: implemented; the evidence is in
[MAT-03](validation/MAT-03-dielectric-conductivity.md). See the
[MAT-03 contract](methods/MAT-03-material-update-contract.md). Same-author review.

The API needed a material map that cannot reach the solver in an invalid
state, and a stepper whose vacuum behaviour stays exactly that of P1.

Options considered:

- A separate material stepper alongside the vacuum one. Rejected: the vacuum
  path would no longer exercise the material kernel, and two kernels would
  have to be kept equivalent by hand.
- Per-edge material input instead of per-cell. Rejected: the MAT-01 note fixes
  per-cell assignment with four-cell averaging.
- Keeping the P1 E screening `div E = 0`. Rejected: across a dielectric
  interface that condition describes a surface charge and rejects the
  physical charge-free state.

Chosen:

- One private constructor takes an `EdgeCoefficients`. The vacuum forms pass
  a one-entry table computed by the same formula, so `Ca = 1.0` exactly and
  `Cb = dt/epsilon0` by the `e_scale` expression.
- The `MaterialMap` validates shape and values before storing anything, and
  `uniform` validates before allocating.
- The coefficients are built before the field copy and fail with
  `std::overflow_error` when not finite or when `Cb <= 0`.
- The initial E screening is the discrete Gauss law with each edge's `eps_r,e`.
  In vacuum it multiplies by exactly 1.0, so its arithmetic and decisions are
  those of P1.
- The V04 benchmark diagnostic expression is unchanged, so V04 output stays
  byte-identical.
- Material cases gain eps-weighted `U`/`Q` and the dissipation `D` of each
  step. These are computed in the benchmark library with its own four-cell
  means, differences and compensated sums.
- Three specification errata were recorded before any V05/V06 run:
  - the V05-C spacing follows the audit (`d_b = 2 lambda0/p`, which produced
    every prediction);
  - the V05-B line is recorded at every state, as revision 1.4 requires;
  - S10's clipping applies to the value.

Consequences:

- The MAT-01 formulas are exercised on every run.
- S10 shows a vacuum map equal to the default bitwise, at kernel and stepper
  level. V06-C re-checks the full V01–V03 suites at zero tolerance, and the
  V04 smoke and full suites re-check the mask path.
- Constant `sigma` remains a conductivity, not a loss tangent. The validated
  scope is `x <= 0.045`.

Revisit for magnetic, dispersive or anisotropic media, subcell interfaces,
`eps_r < 1`, or charged initial states.

## D023 detail — MAT-03 coefficient storage on 2026-09-22

Status: implemented; confirmed by the owner before implementation. See the
[MAT-03 contract](methods/MAT-03-material-update-contract.md) and the corrected
budget in the [MAT-01 specification](validation/MAT-01-closed-domain-benchmarks.md).

The time-centred update needs `Ca` and `Cb` per E edge. Two doubles per edge
put the `p=96` V05-A/V06-A transient at 1.639 GiB of the 2 GiB budget:

| Component | MiB |
| --- | --- |
| Two field payloads | 978.8 |
| Mask | 30.7 |
| Per-edge coefficients | 490.5 |
| Per-cell map | 162.0 |
| Overhead | 16 |

The MAT-01 budget sentence had counted only the payloads and the mask.

Options considered:

- Per-edge doubles. Simple, but little headroom.
- Recomputing the coefficients from the per-cell map inside the loop. Rejected:
  it repeats the averaging at every step and makes the kernel depend on the
  map.
- A per-cell-class index. Rejected: the edge classes are what the kernel uses.

Chosen: deduplicate `(eps_r_e, sigma_e)` by exact bit pattern into a table of
48-byte entries, with a `uint32` index per E sample (122.6 MiB at `p=96`). The
peak is then 1.279 GiB. Version-1 fixtures produce one entry (uniform) or
three (vacuum, mean, loaded). The per-entry edge counts are emitted, and the
analyzer checks them against a closed-form classification. The self-test checks
that classification against a brute-force enumeration.

Consequences:

- `working_bytes_budgeted` now counts the index, a table allowance, the map
  and the retained previous E for `D`. `reference-v1` also counts the mask
  that MAT-02 had left out.
- The audit script prints the corrected transient for both layouts and fails
  if the adopted one exceeds 2 GiB.
- A pathological map with more than `2^32 - 1` distinct pairs is a
  `std::length_error`.

## D022 detail — probe-record completeness on 2026-09-22

Status: implemented; the MAT-02 runs were re-analyzed under it and pass. See
[MAT-01 revision 1.4](validation/MAT-01-closed-domain-benchmarks.md) and the
[MAT-02 addendum](validation/MAT-02-pec-cavity.md). Same-author review.

Question: the structural audit checked that every state carried the same
*number* of probe rows, and the revision-1.3 reduction read the prescribed
samples through a defaulting lookup. Neither can see a probe that is missing
from the whole record: the count stays uniform, and the absent samples are read
as the zeros the requirements expect. Deleting all 4,097 samples of the second
prescribed probe from copies of both driven cases left the audit and the full
PEC reduction passing. What should the record be required to contain?

Considered: requiring only a total row count `(steps+1) * probes` (rejected:
it admits a record that compensates one probe's absence with another's
duplicate, and the audit's per-row uniqueness rule is what would have to catch
that). Considered comparing against a fixed per-case expectation in the
analyzer (rejected: the prescribed indices are already in each artifact's own
metadata, and deriving them twice would drift). Chosen: compare the recorded
`(component, index)` key set — identical at every state, and for a source case
exactly equal to the `probe_indices` the artifact declares — and, in the
reduction, require each sample it reads to be present. The audit rule is
expressed as a pure function over the per-state key sets so its faults can be
injected without fabricating an artifact directory. Because that rule compares
an artifact with its own declaration, the V04-C reduction adds the second
layer the review asked for: the specification audit derives the C2/C3 probe
pairs from the fixture (`(10,12,16)`/`(8,10,12)` and `(1,1,1)`/`(9,11,13)`,
with both interior edges confirmed strictly inside the shell and unmasked) and
the reduction requires the declared and recorded sets to equal them, so a run
that also trimmed its `probe_indices` cannot define its own coverage.

Consequences: the rule applies to every closed-v1 case, mode cases included,
and is a completeness statement rather than a tolerance. The retained V04 raw
runs pass unchanged and every tracked value is bit-identical; the only summary
change is the rule version. `reference.closed_analysis` grows from 709 to 726
checks, including the deletion that previously passed and a duplicated sample
standing in for a missing one. Revisit if a case is
added whose recorded probe set legitimately varies between states.

## D021 detail — V04-C component/edge identity and metadata description on 2026-09-22

Status: implemented; the MAT-02 runs were re-analyzed under it and pass. See
[MAT-01 revision 1.3](validation/MAT-01-closed-domain-benchmarks.md), the
[review report](validation/MAT-02-review-2026-09-22.md) and the
[MAT-02 addendum](validation/MAT-02-pec-cavity.md). Same-author review.

Question: revision 1.2 anchored the driven side to a closed-form deposit, but
compared it with the *largest* of the three electric region maxima, and region
maxima are unsigned aggregates over a whole region. Two things therefore
remained unpinned: the component the fixed `J_z` source drives, and the edge it
drives. A separate finding concerned metadata rather than acceptance: every
mode case emitted an `initialization` description carrying the amplitude
`H_s = -C E_s/(mu0 Omega)` where the field written at `-dt/2` is
`H^(-1/2) = -H_s sin(omega_d dt/2)`, the positive form the initializer, the
specification and the independent oracle all use. Reconstructing the fixture
from that description reverses the magnetic field.

Considered for the acceptance: adding a region maximum per component
(rejected: still unsigned and still region-wide, so it fixes the component but
never the edge). Considered recording a new per-edge observable (rejected: C2
and C3 already probe their source edge, so the artifact contains the sample and
no run has to be repeated). Chosen: require the `Ez` region maximum
specifically, require every other component to be zero at state 1 both in the
region and over the whole domain, and check the native source-edge sample
against the *signed* `-(dt/eps0) J0 g_0`, which also fixes the sign convention
of the update equation. Considered for the metadata: rewriting the retained
artifacts (rejected: raw evidence is not edited after the fact) and leaving the
description uncontrolled (rejected: it is the only record of the initial
condition inside a run). Chosen: correct the emitter, pin the description in
the structural audit, and admit the single historical string only together with
the source snapshot `f02fbe47…` that produced it.

Consequences: the analyzer gained a component-explicit excitation check and a
source-probe reduction; `reference.closed_analysis` grows from 684 to 709
checks, including the exact mutation that revision 1.2 accepted. The retained
V04 raw runs pass unchanged and every previously tracked number is bit-identical;
the summary diff is the two new source-probe metrics per driven case and the
rule version. The metadata correction changes `benchmarks/closed.cpp`, so the
source fingerprint moves from `f02fbe47…` to `706af2e4…`; no computed field
changed, and the retained runs keep their own fingerprint and their historical
description. Revisit if a driven case is added whose source component or edge
is not fixed by the specification, or if another historical metadata string
has to be admitted.

## D020 detail — V04-C driven acceptance on 2026-09-22

Status: implemented; the MAT-02 runs were re-analyzed under it and pass. See
[MAT-01 revision 1.2](validation/MAT-01-closed-domain-benchmarks.md) and the
[MAT-02 addendum](validation/MAT-02-pec-cavity.md). Same-author review.

Question: the version-1 V04-C acceptance for the driven cases required the
silent side to be exactly zero and the driven side to be finite. Both halves
are satisfied by a run that injects nothing, so the criterion could not fail
on a dead or decoupled region. What positive requirement should replace
finiteness, and where should it come from?

Considered: leaving the specification alone and treating the existing
coverage as sufficient (rejected: the C1 equivalence and the four-state oracle
cover `pec-c1-*` and `pec-c3-outside` at smoke length only, and
`pec-c2-inside` had no positive-field coverage at any length). Considered a
purely relative check against a previously measured peak (rejected: it would
make the acceptance depend on a solver result rather than on the
specification, and the validation plan requires absolute floors where relative
comparison is ill-conditioned). Considered requiring only the energy invariant
(rejected: it detects a dead region but says nothing about whether the field
that exists is the one the prescribed source deposits). Chosen: an exact
closed-form anchor plus a coarse floor plus the invariant — the first electric
state equals `(dt/eps0) g_0` with the rest of the region exactly zero, the
driven peak reaches 0.1 of the largest single-step deposit, and `Q` is zero at
state 0, positive after the pulse and constant to 1e-12 thereafter. The
deposits are computed by the specification audit from the fixed pulse and time
step, so the acceptance and the specification keep sharing one set of
predictions, as D019 already established for the V04 comparators.

Consequences: no solver, fixture, geometry, cap or identification limit
changed and no recorded measurement changed value; the tracked summary diff is
purely additive. `reference.closed_analysis` grows from 665 to 684 checks and
the smoke path now also verifies the deposit, so a driven case that stops
carrying its pulse fails in CI rather than only in the manual suites. The
`0.1` fraction is a dead-region floor and not an accuracy claim; the state-1
equality is the sharp part. Revisit if a driven closed-domain case is added
whose source is not a single prescribed edge current, or if a valid
implementation orders the first update so that more than the driven edge moves
at state 1.

## D019 detail — MAT-02 PEC mask and V04 evidence decisions on 2026-09-18

Status: implemented with measured V04 evidence. See the
[MAT-02 contract](methods/MAT-02-pec-mask-contract.md) and
[MAT-02 evidence](validation/MAT-02-pec-cavity.md). Same-author review.

Considered: PEC as a zero-coefficient material (rejected in D018), a
separate boundary object applied after each E update (rejected: writes zeros
instead of never touching the sample, and doubles the loop), or a mask
consulted inside the E loop (chosen: masked samples are never written, the
closure-only mask performs the identical arithmetic, and the outer walls
become the special case `pec_shell([0,N))`). Considered validating currents
against the mask in `ElectricCurrent` (rejected: the current object has no
mask; the step rejects a masked target before any mutation and fails
terminally as every other step error). Considered screening H initial data
only on the three named surfaces (rejected in favour of the general rule "all
four surrounding tangential E samples masked", which reduces to those
surfaces for boxes and shells and stays correct for overlapping primitives).
Considered adding the exact-mode and pulse cases to the `reference-v1`
library (rejected: a separate `closed-v1` library keeps the P1 fixtures and
their byte-identical outputs untouched and shares only stream/JSON helpers).
Considered re-deriving the V04 predictions inside the analyzer (rejected: the
analyzer imports the MAT-01 audit's closed-form functions so that the
specification and the acceptance use one set of predictions, while its own
structural audit and reductions remain independent of the solver).

Consequences: one byte per E sample of memory; no change to the H update or
the time-step policy; the V01–V03 evidence remains valid and is re-run at
zero tolerance; V04-A/B/C become permanent regressions through the smoke
suite and the manual closed-v1 suites. Revisit for conductor models outside
full-edge masks or a mask-related V04 failure.

## D018 detail — MAT-01 Phase 2 conventions on 2026-09-18

Status: specified and audited; no P2 implementation and no validated PEC,
material, or spectral capability. See the
[method note](methods/MAT-01-closed-domain-conventions.md),
[specification](validation/MAT-01-closed-domain-benchmarks.md) and
[review](validation/MAT-01-review.md). Same-author review.

Considered: material coefficients stored per edge versus per cell (chose
per-cell assignment with four-cell arithmetic averaging on edges, the
node-aligned interface that Schneider 7.8 shows to be optimal and purely real);
an explicit vacuum code path versus one coefficient kernel (chose one kernel
whose vacuum coefficients are exactly `1` and `dt/epsilon0`, so V01–V03 must
reproduce bitwise); a rederived material CFL versus the vacuum bound (the
eps-weighted dissipation identity shows the vacuum bound suffices for
`eps_r>=1`, `sigma>=0`, `mu=mu0`, so the time-step object is unchanged and
`eps_r<1` is rejected); PEC as zero-coefficient material versus an explicit
edge mask (chose the mask: exact zeros, skipped updates, rejected sources, and
the outer closure becomes a special case); a broadband gated interface
experiment near the guide cutoff versus a taller guide (the audit showed the
former leaks across the gate; the fixture now has cutoff at a quarter of the
carrier, with the record length and gate fixed as part of the fixture);
spectral-only cavity validation versus exact eigenmode phase measurement (both:
V04-A carries the precise resonance claim, V04-B the identification and
resolution claim).

Consequences: P1 evidence remains valid by construction; each P2 observable has
a continuum reference and a closed-form discrete diagnostic, so a failure can be
attributed; the P2 suites cost about five times the P1 suites and stay manual
from clean Release builds while smoke-length cases and synthetic/oracle checks
stay in CTest. Constant conductivity is explicitly not a loss-tangent model and
the supported loss scope is `sigma*dt/(2*eps)<=0.045`. Revisit on any
requirement outside the declared scope or on a P2 measurement failure that
traces to a convention.

## D010 detail — O002 resolved on 2026-09-05

Status: accepted for the reference specification, not numerically validated.
See [method note](methods/FND-03-yee-conventions.md) and
[author review](validation/FND-03-review.md).

Considered common padded arrays versus exact per-component extents; x versus z
contiguous storage; an initially reflecting box versus early periodic/absorbing
boundaries; and equality versus a strict CFL limit. Choose exact component
extents with explicit update ranges to expose staggering and avoid ghost reads.
X-contiguous storage fixes a simple scalar iteration order without claiming a
performance advantage. Binary64 follows the verified toolchain capability and
provides the reference precision for later backend comparisons.

Choose the reflecting closure to bound the initial stencil without expanding
P1 into an absorbing or periodic boundary implementation. Physical PEC validation
still belongs to P2; open-domain capability belongs to P3. The cost is that
FND-04 must demonstrate boundary isolation, including transverse faces and
initial-field mismatch. Normal H starts at zero on the walls and remains there
under the tangential-E constraint; other unconstrained samples evolve normally.

Choose strict dt<dt_max with default 0.99 of the unequal-spacing vacuum bound;
this avoids the marginal equality case without asserting accuracy. Reserve
positive-time phasors and negative-exponent forward transforms; pin a consistent
2022 CODATA vacuum constant set. Validate the mathematical and input contracts
before optimizing or extending them. O003 remains open for FND-04.

## D011 detail — O003 resolved on 2026-09-05

Status: accepted for version-1 reference validation; no achieved accuracy claim.
See [specification](validation/FND-04-reference-benchmarks.md) and
[author review](validation/FND-04-review.md).

Considered unmodified plane-wave initial fields, early periodic/absorbing
boundaries, and a finite compatible curl fixture. Choose the curl fixture with
a zero collar and explicit dependency guards on every face. This preserves
FND-03's initial boundary/divergence constraints and P1 scope. Its cost is a
larger 3D volume and a short measurement window; an enlarged-domain check must
verify its implementation. The finest mesh requires 489.380 MiB for fields;
serial execution and streamed output fit a 2 GiB working-memory budget.

Choose spatial harmonic fits at native locations/times, with temporal phase
advance measured from initial/final E fits and signed complex impedance shifted
using that measured frequency. This avoids a temporal FFT dependency before
MAT-04, fixes signal-floor behavior, and separates continuum dispersion from
discrete implementation error. The three-mesh continuum tolerances follow the
independent h^2 dispersion budget; all six axis/polarization combinations and
time-step/domain/mesh-shape sensitivity are required.

Choose the positive staggered modified-energy invariant for long-time lossless
tests, backed by the finite-grid curl adjoint identity. A naive mixed-time
squared-field norm can oscillate in a stable run; retain it as a bounded
diagnostic instead of requiring monotonicity. Both initial and finite-current
excitations are specified; physical feed/PEC/radiation validation stays in later
phases. Same-author review is explicit. FND-05 still must close the foundation
gate before REF-01, and all physical/structural production checks remain pending.

## D012 detail — REF-01 API decisions on 2026-09-06

Status: implemented and structurally checked on Windows x64; no validated physics.
See [core grid contract](methods/REF-01-core-grid-contract.md) and
[evidence](validation/REF-01-core-grid.md).

Considered permissive unsigned aggregate inputs versus validated integral
construction, and allocating fields immediately versus checking metadata first.
Choose integral-only counts with pre-conversion negative/range checks and const
grid accessors. This prevents accidental floating truncation at the core API
while leaving malformed-text handling with the future CLI. Keep field storage
in REF-02 so all six extents, products, and total bytes can be checked without
allocation. Invalid input uses invalid_argument, size/budget failures use
length_error, and nonrepresentable geometry uses overflow_error; no general
error framework or solver/backend interface is introduced.

Use the real vector<double> per-component limit, optionally lowered by the
caller, plus an aggregate byte cap. Neither default arithmetic limits nor a
passing grid promise available RAM. REF-04 still must account for diagnostic
and fixture overhead under its 2 GiB working-memory budget. Require exact
half-grid indices through N and a conservative coordinate-spacing guard.
Resolvable subnormal geometry is accepted, but coefficients, CFL, and time
representability remain separate REF-03/04 checks. These choices add no
stability or accuracy claim and do not alter the FND-04 acceptance thresholds.

## D013 detail — REF-02 storage decisions on 2026-09-07

Status: implemented and structurally checked on Windows x64; no validated physics.
See [storage contract](methods/REF-02-field-storage-contract.md) and
[evidence](validation/REF-02-field-storage.md).

Considered exposing resizable vectors, generic field/backend abstractions, and
a fixed owner with checked sample access. Choose the fixed owner with six exact
vector<double> arrays, a private grid value, mutable/const at, and const spans.
Disable copy/move/assignment for now so grid/storage correspondence and borrowed
reference lifetime cannot be broken by partial assignment or moved-from arrays.
This avoids implicit large field copies. Transfer/checkpoint semantics can be
specified when a concrete run requirement appears; no backend framework is added.

Put checked positions, offsets, and wall predicates on UniformGrid so metadata
inspection does not allocate fields. Bounds plus the already checked extent
products prove safe offset arithmetic. Every access pays a component/bounds
check in this reference API; performance work requires later profiling and
validation. Coordinates are deterministic binary64 geometry calculations.

Wall predicates classify without zeroing. Raw storage permits writes needed by
local structural fixtures; a future public run must separately reject invalid
initial conditions and enforce the provisional boundary during evolution.
Zero allocation is not divergence, stability, or physical PEC validation. The
S01 access and S02 classification tests pass; actual kernel evolution remains
REF-03. No fixed numerical tolerance or phase gate changed.

## D014 detail — REF-03 stepping decisions on 2026-09-07

Status: implemented with passing equation-level/structural checks on Windows x64.
No physical propagation, impedance, or stability benchmark is claimed. See the
[contract](methods/REF-03-reference-update-contract.md) and
[evidence](validation/REF-03-reference-updates.md).

Considered borrowed mutable fields versus explicit copying into an owned stepper,
and transactional full-field copies versus in-place updates with a failed state.
Choose one explicit initial copy, const field inspection, and complete H then E
family updates. This retains REF-02's fixed owner and prevents external initial
edits from altering a run. Initial construction costs two payloads temporarily;
release fixtures before integration and count this in REF-04's memory budget.
Avoid a field-size rollback copy per step. A failed step is terminal, state does
not advance, and fields/time accessors reject. Previously borrowed views must be
discarded after an exception; C++ cannot revoke them. The error carries the
input state, component, and index. No output writer exists in REF-03.

Initial public states are finite, zero on tangential E/normal H walls, and pass
the declared source-free divergence screening. This API currently represents
rho=0 and J=0; local algebra harnesses can still exercise incompatible affine/
polynomial data through internal kernels. REF-04 must specify current/charge
continuity rather than repurpose unrestricted field writes as a source.

Use the scaled unequal-spacing CFL formula, strict q/dt rejection, checked
binary64 coefficients, and multiplication-derived native times. Reject extreme
inputs whose selected evaluation is not representable even if an alternative
scaling could evaluate them. Retain straightforward divided differences and
checked field accesses; optimize only after physical validation and profiling.

S01–S05 and the source-free part of S06 pass. A separate Fraction axis-permutation
oracle fixes every small-grid half-stage without using production results.
The existing method/threshold records remain unchanged. C02's structural/CFL
review passes; C03/P1 remain open for run facilities and physical measurements.

## D015 detail — REF-04 source and run decisions on 2026-09-10

Status: implemented with structural and end-to-end smoke evidence. See the
[run contract](methods/REF-04-run-contract.md) and
[REF-04 evidence](validation/REF-04-reference-runs.md). Same-author review.

Considered arbitrary mutable field injection, a general source hierarchy, and
a validated sparse current shape. Choose the shape plus a half-time amplitude:
it supports the prescribed V03 pulse without allowing mutation of active fields
or adding a port framework. Preserve rho=0 initialization; later charge follows
discrete continuity, with no stored charge/projection. Initial copying and
terminal update failure remain D014's policy. Count both field payloads and the
source capacity in the 2 GiB run budget.

Keep benchmark generators/diagnostics in a separate library from the solver.
They use independently transcribed permutation differences, with no production
curl calls. Generate compact potentials on demand to avoid extra volumes.
Expose raw signed probes at native coordinates/times; independent Python fits
test the estimator before REF-05 applies it to physical benchmark outputs.

Use built-in v1 suites and an explicitly named smoke subset. Only smoke accepts
step overrides, and its dependency guard still applies. This is a benchmark
artifact format, not the persistent user-project decision O008. Refuse existing
directories; preserve partial files on failure; close all data/metadata before
renaming the temporary completion marker. A complete raw artifact is not a
physical pass. Record source-content fingerprint, compiler, CPU identifier,
units, configuration, fixture checks, memory budget and elapsed time.

Revisit for a real general-run/project requirement, charge observable, source
performance bottleneck, or measured full-suite resource issue. No v1 numerical
threshold, phase sequence, or physical accuracy claim changed.

## D017 detail — REF-05 physical analysis and acceptance policy on 2026-09-16

Status: implemented with measured evidence. See the
[measurement contract](methods/REF-05-measurement-contract.md) and
[REF-05 evidence](validation/REF-05-reference-measurements.md). Same-author review.

Considered evaluating acceptance inside the C++ benchmark runner, adding the full
physical suites to CTest, or a separate reader. Choose a separate standard-library
Python analyzer that reads only emitted artifacts, re-derives the v1 geometry and
enumeration, and applies the fixed limits; it records every failure and exits
nonzero while retaining outputs. Require its reductions to detect injected faults
on synthetic data and to agree with a pure-Python transcription of the update
equations and diagnostics on production smoke output before any physical result
is interpreted. Register that validation in CTest; keep the multi-minute full
suites as a manual clean-build step with a resource-measuring runner, so hosted
CI stays bounded while physical evidence remains reproducible by command.

Consequences: no solver change; the measured V01–V03 pass is bounded to the
axis-aligned vacuum/closed-grid envelope; later phases must extend the synthetic
and oracle coverage whenever they add an observable. Revisit if suite runtime
justifies hosted long runs or a new observable lacks independent validation.

## D016 detail — source control, CI, and durable evidence on 2026-09-11

Status: implemented locally; the first hosted run occurs after the maintenance
commit reaches GitHub. The repository uses its existing GitHub `origin` and a
read-only GitHub Actions workflow for Debug/Release CMake builds and CTest runs on
Ubuntu. Python is pinned by the workflow and required by CMake for every validation
build. The three previously manual analytical audits are now CTest tests, so an
absent interpreter or failed audit cannot produce a reduced successful suite.

Keep numerical implementations and their evidence in coherent commits. Track
compact audit summaries and checksum manifests; keep large raw arrays out of Git.
Hosted runs retain CTest logs, source-snapshot inputs, and smoke outputs as
90-day workflow artifacts. Licensing and public distribution remain O005 and are
not implied by the configured remote or CI workflow. Revisit if runner coverage,
artifact retention, or release policy changes.
