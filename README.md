# AntennaSim

Antenna-focused electromagnetic simulation and design software. The product
direction and scientific principles are defined in [VISION.md](VISION.md).

**Current status:** C++20 reference kernel with checked grid/field storage,
strict CFL selection, H-then-E updates, per-cell isotropic `eps_r`/constant
`sigma` materials with the time-centred lossy update (vacuum by default,
bitwise identical to the P1 arithmetic), explicit E-edge PEC masks (outer
closure plus interior `pec_box`/`pec_shell` primitives), impressed currents,
native probes, reproducible benchmark CLI/output, and independent analyzers.
Debug and Release pass twenty CTest tests, including independent
equation-level, analytical, fixture, sampling, artifact, mask and reduction
checks. The version-1 free-space propagation, impedance, refinement and
closed-grid stability benchmarks (V01–V03) passed on 2026-09-16 from a clean
Release build, were reproduced exactly at the Phase 1 gate on 2026-09-17, and
again through the mask-capable kernel on 2026-09-18. The version-1 PEC cavity
benchmarks (V04: exact eigenmode resonance and refinement, driven spectrum
identification and resolution, interior shell enforcement) passed on
2026-09-18 from a clean Release build (MAT-02), and were re-confirmed on
2026-09-22 under specification revisions 1.2 to 1.4, which strengthened the
V04-C driven acceptance after review.

The version-1 material benchmarks passed on 2026-09-23 from a clean Release
build (MAT-03):

- V05: homogeneous dielectric eigenwave, TE-mode interface reflection and
  transmission, slab-loaded cavity.
- V06: lossy eigenwave decay and phase for `sigma dt/(2 eps) <= 0.045`, and
  the closed-grid dissipation identity. V01–V04 were reproduced at zero
  tolerance.

A constant conductivity is not a loss-tangent model. No spectral production,
open-boundary, port or antenna accuracy claim is established.
The foundation gate passed on 2026-09-06 and the reference-propagation gate on
2026-09-17; Phase 2 (materials and closed domains) is in progress.

## Project records

| Record | Purpose |
| --- | --- |
| [Project plan](docs/PROJECT_PLAN.md) | Architecture, phases, dependencies, and completion gates |
| [Work schedule](docs/SCHEDULE.md) | Planning cadence, first six cycles, and replanning rules |
| [Backlog and status](docs/BACKLOG.md) | Current work, next actions, blockers, and completed items |
| [Development routines](docs/WORKFLOW.md) | Session routine, numerical feature process, and review templates |
| [Validation plan](docs/VALIDATION.md) | Required evidence, benchmark register, and acceptance policy |
| [Decision log](docs/DECISIONS.md) | Accepted decisions and unresolved choices |
| [Development environment](docs/ENVIRONMENT.md) | Toolchain inventory, pinned tools, and reproduction instructions |
| [Build evidence](docs/validation/FND-02-build.md) | Foundation checks and their limits |
| [Yee-grid conventions](docs/methods/FND-03-yee-conventions.md) | Reference equations, units, indexing, time stepping, and boundary contract |
| [Convention review](docs/validation/FND-03-review.md) | Mathematical audit, infrastructure regression, and remaining foundation work |
| [Initial benchmark specifications](docs/validation/FND-04-reference-benchmarks.md) | V01–V03/S01–S08 fixtures, independent comparisons, fixed thresholds, and resource budgets |
| [Benchmark specification review](docs/validation/FND-04-review.md) | Analytical calculations, infrastructure regression, and FND-05 handoff |
| [Foundation gate](docs/validation/FND-05-foundation-gate.md) | P0 acceptance matrix, clean-build reproduction, limitations, and REF-01 scope |
| [Core grid contract](docs/methods/REF-01-core-grid-contract.md) | Validated metadata API, errors, representability, and allocation limits |
| [Core grid evidence](docs/validation/REF-01-core-grid.md) | REF-01 structural checks, Debug/Release results, and REF-02 handoff |
| [Field storage contract](docs/methods/REF-02-field-storage-contract.md) | Ownership, checked indexing, coordinates, wall classification, and acceptance |
| [Field storage evidence](docs/validation/REF-02-field-storage.md) | REF-02 structural checks, Debug/Release results, and REF-03 handoff |
| [Reference update contract](docs/methods/REF-03-reference-update-contract.md) | CFL, time levels, initialization, kernel equations, and failure policy |
| [Reference update evidence](docs/validation/REF-03-reference-updates.md) | REF-03 structural/half-stage comparisons, builds, and REF-04 handoff |
| [Reference run contract](docs/methods/REF-04-run-contract.md) | Impressed current/charge, native probes, fixed suites and output lifecycle |
| [Reference run evidence](docs/validation/REF-04-reference-runs.md) | REF-04 source/fixture/sampling checks, deterministic CLI smoke and resource measurements |
| [Measurement contract](docs/methods/REF-05-measurement-contract.md) | V01–V03 reductions, independence, reduction validation and acceptance mapping |
| [Physical measurement evidence](docs/validation/REF-05-reference-measurements.md) | REF-05 propagation/impedance/refinement/stability results, resources and limits |
| [Reference-propagation gate](docs/validation/REF-06-reference-propagation-gate.md) | P1 acceptance matrix, supported limits, clean-build reproduction, risk review, and P2 breakdown |
| [Closed-domain conventions](docs/methods/MAT-01-closed-domain-conventions.md) | PEC edge masks, isotropic dielectric/conductivity update, dissipation identity, spectral conventions, closed-form discrete references |
| [Closed-domain benchmark specifications](docs/validation/MAT-01-closed-domain-benchmarks.md) | V04–V07 fixtures, comparators, fixed thresholds, S09–S14, analyzer coverage, and resource budgets |
| [Closed-domain specification review](docs/validation/MAT-01-review.md) | MAT-01 audit calculations, fixture corrections, clean-build regression, and MAT-02 handoff |
| [PEC mask contract](docs/methods/MAT-02-pec-mask-contract.md) | Mask representation, stepper integration, closed-v1 fixtures/CLI, independent V04 analysis and its validation |
| [PEC cavity evidence](docs/validation/MAT-02-pec-cavity.md) | MAT-02 S09 checks, V04-A/B/C measurements, V01–V03 zero-tolerance regression, resources, limits, and MAT-03 handoff |
| [Material update contract](docs/methods/MAT-03-material-update-contract.md) | Material map, deduplicated edge coefficients (D023), lossy kernel and Gauss screening, closed-v1 material suites/CLI, independent V05/V06 analysis and its validation |
| [Dielectric and conductivity evidence](docs/validation/MAT-03-dielectric-conductivity.md) | MAT-03 S10–S13 checks, V05-A/B/C and V06-A/B measurements, V05-B purity revision 1.5, V01–V04 zero-tolerance regression, resources, limits, and MAT-04 handoff |

Start each development session with the backlog and the relevant phase gate.
Update the records at the end of the session. See [AGENTS.md](AGENTS.md) for
repository working instructions.

## Immediate objective

Begin MAT-04: specify and implement production spectral processing (the
`exp(-i omega t) dt` direct sum at requested frequencies with native E/H times,
rectangular and Hann windows, the S14 running DFT), validate it on the V07
synthetic signals, and reproduce the independently analysed V04-B cavity
spectrum and the V04-B/V05-B direct sums, keeping all twenty CTests and the
V01–V06 suites passing. P0, P1, REF-01 through REF-06, and MAT-01 through
MAT-03 are complete.

## Build and check

The project-local Windows toolchain is set up in this workspace. From the root:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

Both commands configure, build, and run CTest. See the environment record to recreate
the tools. Python 3 is a required validation dependency; configuration fails instead
of silently omitting the independent audits. Build outputs and local tools are ignored
by Git rules.

GitHub Actions runs the same required CMake/CTest validation in Debug and Release
on Ubuntu for pushes and pull requests targeting `main`. Each run retains its CTest
logs, source fingerprint input, and smoke-audit outputs as workflow artifacts.

Run the verified smoke command from a PowerShell session with the local compiler
runtime on its process PATH (the CMake presets already provide this for tests):

```powershell
$env:PATH = (Join-Path (Get-Location) '.tools/llvm-mingw-20250613-ucrt-x86_64/bin') + ';' + $env:PATH
& ./build/windows-local-release/antennasim.exe --benchmark reference-v1 --suite smoke --output build/evidence/reference-smoke
```

Choose a fresh output directory each time. Smoke runs two steps of p=24 x/y
propagation and the two q=.99 stability fixtures; `--steps N` is allowed only for
smoke and must satisfy its isolation guard. `propagation` and `stability` select
the full fixed v1 suites; `scripts/run_reference_benchmarks.py` runs them with
resource measurement, `scripts/analyze_reference_benchmarks.py` evaluates the
v1 acceptance independently, and `scripts/compare_reference_analysis.py` compares
a re-run's summary with the tracked one for reproduction evidence.
`--benchmark closed-v1` selects the closed-domain suites:

- `cavity|cavity-spectrum|pec`: the PEC cavity suites (30 exact eigenmode
  cases, the driven spectrum, and five interior-shell cases).
- `dielectric|interface|slab-cavity|lossy|dissipation`: the material suites
  (18 dielectric eigenwaves, 7 interface cases, 18 slab-cavity modes, 26 lossy
  eigenwaves and 2 dissipation cases).
- `smoke`: nine short cases.

They run with `scripts/run_reference_benchmarks.py --benchmark closed-v1` and
are evaluated by `scripts/analyze_closed_benchmarks.py` (`--suite v04` or
`materials` selects a group).
Output includes metadata JSON (with the PEC primitives, masked-edge counts,
the material summary and the solver's edge-coefficient table),
signed native probe CSV, diagnostics CSV (energies, component and region
maxima and the step dissipation where recorded), and a final `COMPLETE.json`
marker. Completion means raw output finished; it does not mean physical
acceptance passed. No port or antenna metrics exist.

These documents record a work schedule; they do not start background jobs,
calendar events, or recurring notifications.
