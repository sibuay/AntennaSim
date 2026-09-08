# FND-05 — Foundation gate review

Date: 2026-09-06. Decision: **PASS for P0; REF-01 ready.**
Phase 1 implementation and its numerical gate remain pending.

Reviewer: Codex, the same implementation collaborator responsible for the prior
records. No independent human or second-agent review occurred. Independent
mathematical comparators do not make this an independent review.

Identity: local snapshot; this directory is still not a Git repository. Before
editing status records, all nine FND-02 and all nine FND-04 manifest entries
matched their saved SHA-256 values. No C++ source, build configuration, test,
method note, benchmark specification, or analytical audit was changed.
[Snapshot identities](FND-05-source-sha256.txt) identify the reviewed inputs,
final records, and retained local build logs; older manifests are preserved.

## Gate acceptance matrix

The required criteria are the P0 exit conditions in the
[project plan](../PROJECT_PLAN.md), evaluated under the
[workflow](../WORKFLOW.md) and [validation policy](../VALIDATION.md).

| Required criterion | Reviewed or measured result | Evidence | Verdict |
| --- | --- | --- | --- |
| Working C++20 toolchain and build/test presets | Pinned Clang 20.1.7; fresh Debug and Release configurations compile and link the library, CLI, and toolchain check | [Environment](../ENVIRONMENT.md), clean runs below | Pass |
| Clean configure/build/test reproduced | Both approved build directories were absent before configure; all six Ninja build steps ran per configuration; CTest passed 3/3 each | Clean-run matrix and retained logs below | Pass in approved execution environment |
| Mathematical conventions reviewed | Six component extents, twelve curl terms, signs, native space/time placement, boundary constraints, SI constants, strict CFL and invalid-input contracts are consistent with the declared P1 scope | [FND-03 method](../methods/FND-03-yee-conventions.md), [review](FND-03-review.md), reproduced audit below | Pass for specification |
| Independent validation specifications reviewed | V01–V03 and S01–S08 define fixtures, external analytical comparators, fixed thresholds, refinement and sensitivity checks, failure policy, future commands, and resource budgets | [FND-04 specification](FND-04-reference-benchmarks.md), [review](FND-04-review.md), reproduced audit below | Pass for specification |
| No open decision blocking P1 | O001–O003 resolved; remaining O005–O010 have later need-by points; concrete core error/API choices belong to REF-01/03 | [Decision log](../DECISIONS.md) | Pass |
| Next implementation item bounded and evidence assigned | REF-01 selected; storage, stepping, sources, and physical results retain their separate dependencies | Next action below and [backlog](../BACKLOG.md) | Pass |

The gate passes because the required foundation evidence exists and was
reproduced. It does not pass on the basis of elapsed time or code presence.
There is **no validated electromagnetic capability**.

## Clean build and infrastructure regression

Environment: Windows x64 and project-local LLVM-MinGW 20250613 UCRT toolchain
as recorded in FND-01/02. This run verified Clang 20.1.7 from clean compiler
detection, CMake/CTest 3.31.10, Ninja 1.11.1.git.kitware.jobserver-1, and Python
3.9.7. Hardware inventory was not repeated; no performance-phase claim is made.

| Run | Configure | Build | CTest | Measured duration |
| --- | --- | --- | --- | --- |
| Sandbox Debug, fresh directory | Fail: compiler child `clang-20: Permission denied` | Not run | Not run | Not used as passing evidence |
| Sandbox Release, fresh directory | Same failure | Not run | Not run | Not used as passing evidence |
| Approved Debug, separate fresh directory | Pass | Pass; six steps, no compiler warnings reported | 3/3 pass; 0.28 s | 11.20 s configure/build/test total |
| Approved Release, separate fresh directory | Pass | Pass; six steps, no compiler warnings reported | 3/3 pass; 0.25 s | 4.24 s configure/build/test total |

Passing tests were `foundation.toolchain`, `foundation.cli_help`, and
`foundation.cli_contract`. They check C++20/binary64/library linkage and the
CLI help/version/unsupported-request contract. They do not exercise Maxwell
updates. Verbose builds show `-std=c++20`, warnings, `-fno-fast-math`, and
`-ffp-contract=off` on all three compiled targets in both configurations.
Release uses explicit test failure returns despite `-DNDEBUG`.

The sandbox failures reproduce the previously documented compiler execution
restriction. Unlike FND-03/04's incremental runs, these attempts failed during
fresh compiler detection, before any project test. No CLI startup failure was
measured in these failed attempts. Identical sources and presets passed through
approved execution. The precise access/runtime mechanism remains unisolated;
this gate requires the demonstrated working execution environment, not a claim
that sandbox builds work. No toolchain or floating-point policy was altered.

Commands used from the project root, with `debug` and `release` in turn:

```powershell
$taskConfig = 'debug' # Repeat for 'release'.
$taskPreset = "windows-local-$taskConfig"
$taskBuild = "build/FND-05-$taskConfig-approved"
if (Test-Path -LiteralPath $taskBuild) { throw 'Use an absent build directory.' }
& ./.tools/cmake/cmake/data/bin/cmake.exe --preset $taskPreset -B $taskBuild
if ($LASTEXITCODE -ne 0) { throw 'Configure failed.' }
& ./.tools/cmake/cmake/data/bin/cmake.exe --build $taskBuild --verbose
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
& ./.tools/cmake/cmake/data/bin/ctest.exe --preset $taskPreset --test-dir $taskBuild
if ($LASTEXITCODE -ne 0) { throw 'CTest failed.' }
```

The sandbox attempts used the suffix `-sandbox` instead of `-approved`.
For another clean reproduction choose new absent directory names; do not
overwrite the retained evidence. The `-B`/`--test-dir` overrides keep the pinned
presets and their test runtime PATH while preserving previous compiled outputs.
Stage output was captured with `Tee-Object`; a stopwatch measured each successful
configure/build/test sequence. Local logs are retained under ignored `build/`:

- `FND-05-{debug,release}-sandbox-configure.log`, plus each failed tree's
  `CMakeFiles/CMakeConfigureLog.yaml`.
- `FND-05-{debug,release}-approved-{configure,build,test}.log`.
- `FND-05-{debug,release}-approved-LastTest.log`.

Evidence collection found that this CTest preset/`--test-dir` combination
writes `LastTest.log` under the preset's original
`build/windows-local-{debug,release}/Testing/Temporary/` directory. Those logs
were inspected: all three test commands and working directories point to the
fresh `FND-05-*-approved` trees, confirming that the newly built executables
were tested. Copies were saved at the stable FND-05 names above. The original
preset's latest test logs were replaced by CTest; prior reports and separately
preserved historical failure logs remain intact.

## Specification review and reproduced calculations

Re-read the complete FND-03/04 method, benchmark contract, review evidence, audit
scripts, and foundation source/build/test files. Rechecked the published
dispersion and impedance basis in Schneider's
[chapter 7, sections 7.3–7.5](https://eecs.wsu.edu/~schneidj/ufdtd/chap7.pdf)
and the unequal-spacing stability bound in
[chapter 9, equation 9.53](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf)
on 2026-09-06. The project's signed Cartesian ratios, strict margin below
the stability bound, finite curl fixtures, energy diagnostic, and acceptance
budgets remain explicit project derivations and decisions.

Review checked the curl-potential signs (`u cross w=-v`), native H startup
time, all-face plateau/dependency guard, phase-fit sign, and separation of
continuum error from agreement with the discrete dispersion relation. It also
checked that the stability diagnostic uses the documented half-time pairing
and requires the production adjoint check before interpreting its invariant.
No specification inconsistency requiring a version or tolerance change was
identified. Actual fixture and kernel correctness remain implementation tests.

Executed successfully using the existing standard-library-only Python scripts:

```powershell
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
```

| Deterministic calculation | Reproduced result |
| --- | --- |
| Derivative geometry and affine curl | 12 midpoint/axis checks and six curl increments pass |
| Small-grid extents/offsets/stencils | 90 and 231 samples; 676 endpoint reads in bounds; unique contiguous offsets |
| Predicted phase-speed errors at p=24/48/96 | 0.00120829246432 / 0.000301257333745 / 0.0000752634589699, below fixed caps |
| Predicted refinement orders | 2.003901430 and 2.000974863, within [1.8,2.2] |
| q=0.5 and cubic sensitivity predictions | 0.00243512003878 and 0.00192599561389, each below 0.003 |
| Native-event synthetic signed impedance fit | Maximum normalized error 1.43e-15 |
| Modified-energy algebra | 18 exact modal identities pass |
| Finite-grid weighted adjoint | Exact matching dot products -52411/30 and -27929/6 on the two specified grids |
| Resource calculations | Finest field storage 489.380127 MiB; 865,603,584 propagation and 215,083,008 stability cell-steps |

These are analytical/specification calculations, not simulated measurements or
observed convergence. The scripts share a handwritten stencil transcription;
they neither parse the method note nor execute a production kernel. The 2 GiB
working-memory budget remains a future measurement obligation, not measured
memory use. No additional numerical accuracy is established by repeating them.

## Limits, open decisions, and next action

- Physical V01–V03, production S01–S08, long-time integration, actual 3D fixture
  checks, and runtime/peak-memory validation: **not run; no solver exists**.
- Linux, macOS, MSVC, generic PATH presets, and CUDA: **not tested**.
- O005 hosting/license/CI is due before external distribution; O006 reference
  access before P4/P6; O007 absorbing method before P3; O008 persistence by P6;
  O009 CAD/UI by P10/P11; O010 performance hardware by P8/P9. None blocks P1.
- Same-author review and sandbox access remain recorded limitations. Later
  benchmark failures keep the relevant numerical gate open; this foundation
  decision never substitutes for those results.

**Next exact action: REF-01.** Implement the minimal core types and checked
uniform-grid description using FND-03. Cover per-axis cell-count/spacing
validation, six component extents, domain representability, checked additions,
products, total/byte counts, and container limits before allocation. Use S01's
small-grid independent expected values and V03's applicable invalid-input
matrix, including limit-derived failures without huge allocations. Document
concrete error types and allocation limits; preserve the CPU reference design.
Record evidence in `docs/validation/REF-01-core-grid.md`, build/test both
configurations, and then make REF-02 ready. Field storage/indexing is REF-02;
CFL selection and updates are REF-03; parsing and run/probe/source policies are
completed with their owning REF items rather than claimed by a grid-only API.

P0 and cycle C01 are complete. P1/C02 is ready to start with REF-01. No phase
sequence, dates, durations, dependency choices, or numerical thresholds changed.
