# AntennaSim

Antenna-focused electromagnetic simulation and design software. The product
direction and scientific principles are defined in [VISION.md](VISION.md).

**Current status:** C++20 vacuum reference kernel with checked grid/field storage,
strict CFL selection, H-then-E updates, impressed currents, native probes, and
reproducible reference benchmark CLI/output, and an independent analyzer. Debug
and Release pass twelve CTest tests, including independent equation-level,
analytical, fixture, sampling, artifact and reduction checks. The version-1
free-space propagation, impedance, refinement and closed-grid stability
benchmarks (V01–V03) passed on 2026-09-16 from a clean Release build and were
reproduced exactly from a second clean build at the Phase 1 gate on 2026-09-17.
No PEC, material, open-boundary, port or antenna accuracy claim is established.
The foundation gate passed on 2026-09-06 and the reference-propagation gate on
2026-09-17; Phase 2 (materials and closed domains) is ready to start.

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

Start each development session with the backlog and the relevant phase gate.
Update the records at the end of the session. See [AGENTS.md](AGENTS.md) for
repository working instructions.

## Immediate objective

Begin MAT-01: write the Phase 2 method notes and V04–V07 benchmark specifications
(explicit PEC surfaces, isotropic dielectric and constant-conductivity updates,
spectral processing conventions) with fixed, justified tolerances before any P2
solver code. P0, P1, and REF-01 through REF-06 are complete.

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
Output includes metadata JSON, signed native probe CSV, stability diagnostics
CSV, and a final `COMPLETE.json` marker. Completion means raw output finished;
it does not mean physical acceptance passed. No port or antenna metrics exist.

These documents record a work schedule; they do not start background jobs,
calendar events, or recurring notifications.
