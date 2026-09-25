# Phased project plan

Baseline: 2026-09-05. Source of product scope: [VISION.md](../VISION.md).
Execution status lives in [BACKLOG.md](BACKLOG.md); work sequencing lives in
[SCHEDULE.md](SCHEDULE.md).

## Planning principles

1. Correctness and reproducibility control delivery. No dates or durations are assumed.
2. Implement a minimal, inspectable CPU reference first. Performance work follows
   validated physics.
3. Limit early scope to antenna engineering and a uniform Cartesian 3D Yee grid.
4. Every numerical capability needs documented assumptions, independent evidence,
   and regression coverage.
5. AI orchestrates and explains engineering work; it never supplies fabricated
   numerical results.
6. Define interfaces when a real use case requires them. Do not implement all
   long-term subsystems during scaffolding.

## Responsibilities

- **Project owner (Sina):** product priorities,
  commercial reference access, and consequential scope or resource choices.
- **Implementation collaborator (Codex):** focused implementation, method notes,
  tests, reproducible evidence, and maintenance of these project records.
- **Technical review role:** inspect numerical assumptions, reference provenance,
  and phase evidence. This role is not yet independently staffed. If the same
  collaborator performs it, record that limitation rather than claiming an
  independent review.

Routine implementation choices proceed within the agreed scope. Escalate actual
ambiguities or commitments that cannot be resolved from the project records.

## Architecture direction

The first executable will run reproducible, headless benchmarks. Proposed
structure, to be established in Phase 0:

```text
CMakeLists.txt
CMakePresets.json
include/antennasim/      public core types and supported interfaces
src/                    reference numerical implementation
apps/                   command-line benchmark entry points
tests/                  small deterministic unit and numerical tests
benchmarks/             case definitions and reference metadata
scripts/                analytical checks, plotting, and result comparison
docs/methods/           equations, conventions, and discretization notes
docs/validation/        benchmark specifications and evidence reports
```

Build products and generated large field datasets stay outside tracked source.
Track small reference inputs, benchmark definitions, and summary evidence.

Introduce project schemas, geometry adapters, meshing, post-processing, and
compute backends when their phase requires them. Project descriptions will be
versioned and human-readable; large results will use an appropriate binary
format. Record units and conventions explicitly. Keep UI and AI independent of
the numerical core. Select the initial serialization and result formats through
a decision record before persistent user projects are introduced.

## Phases and completion gates

Phase 0 is **complete**, with the [foundation gate passed on 2026-09-06](validation/FND-05-foundation-gate.md).
Phase 1 is **complete**, with the
[reference-propagation gate passed on 2026-09-17](validation/REF-06-reference-propagation-gate.md):
[REF-01 grid](validation/REF-01-core-grid.md),
[REF-02 storage](validation/REF-02-field-storage.md),
[REF-03 CFL/reference-update structural checks](validation/REF-03-reference-updates.md),
[REF-04 sources/probes/fixtures/CLI and raw artifact checks](validation/REF-04-reference-runs.md),
and [REF-05 physical measurements](validation/REF-05-reference-measurements.md)
pass, and the gate reproduced the V01–V03 measurements exactly from a clean
build. The gate record states the supported limits: axis-aligned vacuum
eigenwaves in a reflecting box at the declared grids and durations. Phase 2 is
**in progress**: MAT-01 fixed the P2 conventions and the V04–V07 specifications
([method note](methods/MAT-01-closed-domain-conventions.md),
[specification](validation/MAT-01-closed-domain-benchmarks.md),
[audit review](validation/MAT-01-review.md)); MAT-02 implemented the explicit
E-edge PEC mask and passed the V04 cavity benchmarks
([contract](methods/MAT-02-pec-mask-contract.md),
[evidence](validation/MAT-02-pec-cavity.md)); MAT-03 implemented per-cell
dielectric and constant-conductivity updates and passed V05/V06
([contract](methods/MAT-03-material-update-contract.md),
[evidence](validation/MAT-03-dielectric-conductivity.md)); MAT-04 is ready.
All later phases are **not started**. PEC and material accuracy are
established only for the declared cavity, interface, slab and homogeneous
lossy envelopes (`x <= 0.045`). Spectral-production, open-boundary and antenna
accuracy remain unvalidated.
The milestone column maps this plan to the original vision. Later phases are
broken into detailed work items only when their prerequisites are understood.

| Phase | Vision milestone | Deliverables | Evidence required to exit |
| --- | --- | --- | --- |
| 0. Foundation | Preparation for M1 | Working C++20/CMake toolchain, build/test presets, conventions, benchmark specifications, basic test execution | Clean configure/build/test reproduced; mathematical and validation specifications reviewed; no open decision blocking Phase 1 |
| 1. Reference propagation | M1 | Grid and staggered field storage, CFL handling, reference update loop, simple excitation, probe output, minimal CLI | Free-space propagation and stability checks meet recorded criteria; component/indexing and invalid-input tests pass; reproduce a run from a clean build |
| 2. Materials and closed domains | M2 | Explicit PEC handling, isotropic dielectric and conductivity model, probes, spectral processing | PEC cavity, dielectric propagation, lossy-material, and spectral checks pass; Phase 1 evidence remains valid |
| 3. Absorbing boundaries | M3 | A documented CPML implementation or justified high-quality alternative; face, edge, and corner handling | Measured reflection across the declared test envelope meets criteria; late-time stability and existing regressions pass |
| 4. Antenna excitation | M4 | One lumped/discrete port with documented voltage/current sampling; impedance and S11 extraction | Extraction pipeline passes independent checks; antenna input results compared with trusted references and mesh/time convergence; signs and power conventions recorded |
| 5. Radiation processing | M5 | Near-field capture, NF2FF, patterns, directivity, gain, and efficiency with explicit power definitions | Dipole radiation benchmark and normalization/power checks pass; angular, domain, time, and mesh sensitivity documented |
| 6. Basic antenna simulator | M6 | Parameterized patch case, reproducible project/results persistence, initial deterministic setup audit, comparison reports | Patch input and radiation results compared with a trusted solver or measured reference of known provenance; convergence and supported limitations documented |
| 7. Mesh capability | M7 | Nonuniform Cartesian grid, material/feed-aware sizing, deterministic mesh checks, convergence workflow | Nonuniform formulation validated; uniform-grid regressions retained; benefits and errors measured on dipole and patch cases |
| 8. CPU performance | M8 | Profile-driven multithreading and explicit backend selection | Reference equivalence within justified tolerances; reproducible speed/memory measurements; thread-related regressions pass |
| 9. GPU performance | M9 | CUDA backend while retaining CPU reference | CPU/GPU numerical comparisons pass; device memory estimates and failure behavior tested; measured hardware-specific benefit |
| 10. Desktop engineering workflow | M10 | Parameterized antenna CAD, materials/ports/mesh controls, project tree, simulation controls, expert access | End-to-end project create/save/load/run workflow; geometry and schema tests; results traceable to actual solver runs |
| 11. Visualization | M11 | Professional field, mesh, current, and radiation views; iteration comparison | Visual quantities agree with saved numerical data; units, scales, phase, and normalization are explicit; representative projects usable |
| 12. Optimization and guided design | M12 plus AI goals | Recorded design intent, sweeps, bounded optimization, deterministic audits, AI setup and interpretation | Reproducible objective history; all reported metrics trace to runs; constraints enforced; generated setup inspectable and editable; hypotheses labeled |
| 13. Additional solver | M13 | A justified MoM scope, common solver interface, later automatic recommendation | Dedicated analytical/reference validation and cross-solver comparisons; supported geometry and limitations stated; selection reasons visible |

Phase 1 must document its provisional outer-boundary behavior. Use a benchmark
time window that isolates propagation from boundary returns. Phase 2 formalizes
and validates PEC behavior; Phase 3 establishes the open-domain capability.

Early scaffolding may include parameter structs and geometry fixtures; full CAD
waits until Phase 10. Minimal plots for validation are necessary from Phase 1;
professional visualization waits until Phase 11. Constant conductivity must not
be presented as a validated broadband constant-loss-tangent material model.
Define the supported material model and frequency scope before claiming loss
tangent support.

## Dependencies and scope controls

Default dependency chain: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P9
→ P10 → P11 → P12 → P13.

This is a development order, not a claim that every item is a physics dependency.
For example, CUDA is not required for a GUI. A measured hardware constraint or
product need can justify resequencing; record the reason and affected gates.
Do not quietly skip a validation dependency.

Later add a horn benchmark when waveguide excitation and supporting geometry are
implemented. Multi-port networks, dispersive models, advanced port types, surface
MoM, and MLFMM require separately planned scope; they are not implicit early
deliverables. General multiphysics and broad industrial EM remain out of scope.

## Release checkpoints

- **Reference kernel:** Phases 0–2, numerical research capability with explicit
  closed-domain limitations.
- **Antenna research preview:** Phases 3–5, validated simple antenna cases within
  a declared operating envelope.
- **Basic simulator:** Phase 6, reproducible dipole and patch workflows. This is
  not a claim of accuracy for every geometry or material.
- **Scalable engine:** Phases 7–9, demonstrated mesh and backend capabilities.
- **Engineering workspace:** Phases 10–12, integrated inspectable workflow.
- **Multiple solvers:** Phase 13, only after FDTD is reliable.

Assign version numbers when release packaging is real. Each release lists the
validated cases, numerical criteria, reproducibility instructions, and known
limitations.

## Risk register

| Risk | Early detection | Response / owner |
| --- | --- | --- |
| Incorrect staggering, signs, or indexing | Component-level checks and independent propagation/cavity cases | Stop dependent work; implementation collaborator investigates equations and indexing |
| Unstable or inaccurate boundaries/ports | Reflection, long-run stability, and reference comparisons | Keep these as dedicated phases; do not compensate by hiding failed results |
| Mesh-driven cost exceeds available memory | Record cell counts, memory, and runtime on every benchmark | Reduce benchmark scope or revise mesh strategy with documented accuracy consequences |
| Reference data unavailable or ambiguous | Identify geometry, feed, material, licensing, and conventions before comparison | Owner resolves access where needed; choose an accessible trusted reference without inventing data |
| GPU or commercial tools unavailable | Inventory hardware and tool access before committing relevant work | Preserve CPU route; revise sequence and record blocked scope |
| UI/AI scope displaces numerical work | Review active backlog against phase gate | Defer unrelated features; owner resolves priority changes |
| Same author and reviewer miss a numerical error | Track independent analytical and solver evidence separately | Seek independent review at major gates where practical; record review limitations |
| Work advances without adequate evidence | Compare completed evidence with the active gate | Keep the gate open and resolve missing validation |

Review this register at phase exit and whenever new evidence changes a risk.
