# REF-01 — Core types and checked grid evidence

Date: 2026-09-06. Decision: **REF-01 complete; REF-02 ready; P1 remains open.**
Scope: production grid metadata and structural/input validation, not field
storage, time integration, or electromagnetic accuracy.

Identity: local snapshot, no Git repository/revision.
[SHA-256 manifest](REF-01-source-sha256.txt) identifies source, tests, specification,
project records, and retained logs. The FND-03 method, FND-04 version-1 benchmark
specification, both analytical audits, and existing foundation test/CLI sources
are unchanged. CMake now compiles the grid into the core and registers its test.

Review: same implementation collaborator; no independent human or second-agent
review. The expected small-grid values and integer boundary calculations are
independent comparators, but the reviewer is not independent.

## Implementation and acceptance matrix

The [API/acceptance contract](../methods/REF-01-core-grid-contract.md) was written
before implementation under [FND-03](../methods/FND-03-yee-conventions.md) and
[FND-04 S01/V03](FND-04-reference-benchmarks.md). No electromagnetic equations or
fixed numerical thresholds were changed.

| Obligation | Implemented behavior and evidence | Result |
| --- | --- | --- |
| Core types with safe count conversion | Integral-only `CellCounts`; signed negative/zero/one and unsigned zero/one rejected on all axes before conversion; floating and bool arguments unavailable at compile time | Pass on Windows x64 |
| Six Yee extents | `UniformGrid` holds exact per-component extents/counts; literal tables on (2,2,2), (2,3,4), (5,4,3) match every component | Pass, exact integers |
| SI domain metadata | Unequal spacings (2,3,5) preserved; domain lengths exactly match (4,6,10), (4,9,20), (10,12,15) | Pass, exact fixture values |
| Safe allocation arithmetic | Checked N+1, extent products, total samples, and binary64 bytes; size_t-derived overflow cases on all three axes; safe arithmetic boundaries and zero products tested | Pass without field allocation |
| Container and caller limits | Effective per-component cap cannot exceed `vector<double>::max_size()`; exact 48-element/1848-byte caps accepted, one-too-small and zero caps rejected | Pass |
| Spacing/input errors | Zero, negative zero, negative, NaN, and both infinities rejected on every axis; invalid component enum selectors rejected | Pass |
| Geometry representability | Overflowing lengths, underflowed half spacings, counts beyond 2^52, and unresolved half coordinates rejected; resolvable subnormal and largest-finite endpoints accepted | Pass for documented conservative policy |
| Core isolation | Metadata-only library API; no solver, field arrays, UI, AI, parsing, or new third-party dependency | Pass by source review |
| Existing infrastructure | Help/version/unsupported-request behavior and toolchain check retained in Debug/Release | 3/3 prior checks pass in each |

Production files:
[grid.hpp](../../include/antennasim/grid.hpp),
[grid.cpp](../../src/grid.cpp),
[checked_size.hpp](../../include/antennasim/detail/checked_size.hpp).
Tests: [grid_check.cpp](../../tests/grid_check.cpp), registered as `reference.grid`
with `fast;reference_structural` labels and a ten-second timeout.

The three small fixtures produce respectively 90/231/513 field samples and
720/1848/4104 bytes. These are deterministic storage calculations, not measured
solver memory or simulated data. Large limit-derived fixtures construct metadata
only; no enormous allocations are attempted. A valid grid does not reserve RAM
or guarantee that later field/fixture allocations fit available memory.

## Checks and actual results

Environment: the established Windows x64 toolchain, Clang 20.1.7 from LLVM-MinGW
20250613 UCRT, CMake/CTest 3.31.10, Ninja 1.11.1.git.kitware.jobserver-1, and
Python 3.9.7. Build/test used the approved execution route demonstrated at the
[P0 gate](FND-05-foundation-gate.md); the known sandbox compiler restriction was
not retried. These are incremental builds, not a new clean-build gate claim.

Executed commands from the project root:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
```

| Run | Compile | CTest | Grid checks | CTest wall time |
| --- | --- | --- | --- | --- |
| Initial Debug | Pass with one test-source warning | 4/4 pass | 136, zero failures | 1.70 s |
| Initial Release | Pass with same warning | 4/4 pass | 136, zero failures | 0.61 s |
| Final Debug after warning fix | Pass, no warnings reported | 4/4 pass | 136, zero failures | 0.22 s |
| Final Release after warning fix | Pass, no warnings reported | 4/4 pass | 136, zero failures | 0.25 s |

Final `reference.grid` runtimes were 0.08 s Debug and 0.07 s Release. Final
configure/build/test sequences took 2.68 s and 2.85 s respectively. All runtime
checks use explicit failure returns and remain active with Release's NDEBUG.

The initial warning was `-Wtautological-compare`: on this platform uintmax_t
and size_t alias the same type, making a non-template portability check compare
the same static constant. Moving that conditional test into a type-dependent
helper removed the warning without changing production code, assertions, or
accepted inputs. Both configurations were rebuilt and retested. No test failed
and no tolerance was adjusted.

Both existing analytical audits passed with the earlier results: twelve
derivative midpoint/axis checks, six affine curls, 676 in-bounds stencil reads,
fixed dispersion/refinement budgets, signed synthetic fits, eighteen exact
modal invariant identities, and two exact weighted-adjoint identities. These
scripts still do not exercise a production electromagnetic kernel. Their output
is specification evidence, not physical validation.

Retained ignored local logs:

- `build/REF-01-{Debug,Release}-build-test.log` and
  `build/REF-01-{Debug,Release}-initial-LastTest.log` preserve the initial warning
  and passing checks.
- `build/REF-01-{Debug,Release}-final-build-test.log` and
  `build/REF-01-{Debug,Release}-final-LastTest.log` identify the final runs.
- `build/REF-01-conventions-audit.log` and `build/REF-01-benchmarks-audit.log`
  preserve analytical output.

## Limits and handoff

REF-01 completes only the grid/size/input subset of S01/V03. Native component
coordinates, flattening, bounds-checked indexing, field allocation, stencil
reads, and wall enumeration remain REF-02/03 work. Fractional/malformed text
parsing, run steps, sources, probes, initial fields, and timestamps remain with
their REF-03/04 owners. Passing metadata validation does not validate CFL or
coefficients, particularly for the extreme spacings in structural tests.

No V01–V03 physical benchmark, field evolution, long-time stability, or measured
runtime/peak-memory benchmark was run: no solver exists. The uintmax_t-wider-than-
size_t branch is inapplicable on this 64-bit platform and was not exercised;
32-bit systems, MSVC, Linux, macOS, and CUDA remain untested.

Decision D012 records the concrete value/error/limit policy. P1 and C02 remain
open. **Next exact action: REF-02**, implementing six binary64 field arrays,
component-native positions, x-contiguous checked indexing, and the corresponding
S01/S02 extent/access/boundary-enumeration tests. Build on the validated grid;
preserve all three foundation regressions and `reference.grid`. Complete storage
and indexing evidence before moving to CFL handling and updates in REF-03.
