# AntennaSim

Antenna-focused electromagnetic simulation and design software. The product
direction and scientific principles are defined in [VISION.md](VISION.md).

**Current status:** C++20 vacuum reference kernel with checked grid/field storage,
strict CFL selection, native time levels, and H-then-E updates. Debug and Release
pass six CTest tests, including independent equation-level and exact-rational
two-step comparisons. No physical benchmark or antenna accuracy claim is established.
The foundation gate passed on 2026-09-06; P1 remains open. Minimal sources, probes,
run configuration, and simulation CLI/output are next (REF-04).

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

Start each development session with the backlog and the relevant phase gate.
Update the records at the end of the session. See [AGENTS.md](AGENTS.md) for
repository working instructions.

## Immediate objective

Begin REF-04: specify and implement minimal current coupling, run configuration,
native probes, and reference benchmark CLI/output. P0 and REF-01 through REF-03
are complete; physical benchmark measurements follow in REF-05. P1 remains open.

## Build and check

The project-local Windows toolchain is set up in this workspace. From the root:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

Both commands configure, build, and run CTest. See the environment record to recreate
the tools. The CLI currently provides only `--help` and `--version`; simulation
requests return an error. Build outputs and local tools are ignored by Git rules.

These documents record a work schedule; they do not start background jobs,
calendar events, or recurring notifications.
