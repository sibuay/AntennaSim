# REF-04 — Reference source, probe, fixture and CLI evidence

2026-09-10. **REF-04 complete; P1 remains open.** This is structural,
equation-level and end-to-end smoke evidence, not a V01–V03 physical pass.
Same collaborator implemented and reviewed; no independent reviewer is claimed.

## Snapshot and method

The reviewed local snapshot was based on `06440a0` and is now preserved by commit
`593064327251a8c408d617e6f0ef3c5ad57883ac`.
[Source/test/script SHA-256 manifest](REF-04-source-sha256.txt) identifies the exact
checked files. The built executable's source-content fingerprint
is `b4d2b807ed49d9efd2f40f7f9810a53c590bfea450a16f5ccdd6f98c5602cb84`.
CMake records its ordered path/hash input in each build's `source-snapshot.txt`;
the fingerprint includes core, benchmark and CLI sources, headers and build files.
Analysis/test scripts have separate entries in the linked manifest.

Equations, impressed-current/charge convention, API, fixture independence,
resource accounting, and pre-implementation acceptance are in the
[REF-04 contract](../methods/REF-04-run-contract.md). The unchanged
[FND-04 v1 specification](FND-04-reference-benchmarks.md) fixes all tolerances.
D015 records the architecture decisions. The solver library contains no CLI,
filesystem, fixture or Python dependence; the benchmark library owns those runs.

## Checks and results

| Check | Measured result | Threshold / outcome |
| --- | --- | --- |
| Debug configure/build/CTest | 8/8 pass, 12.48 s CTest total | Pass; no compiler warnings |
| Release configure/build/CTest | 8/8 pass, 3.88 s CTest total | Pass; no compiler warnings |
| Prior six CTests | All retained and passing | Pass; `reference.vacuum` still has 27013 checks |
| Source/probe/run checks | 3337 checks | Pass |
| S06 impressed current | Three E components, both signs; every field sample checked against initially zero H and `E=-dt*J/epsilon0` | Normalized error <=1e-13; pass |
| Discrete continuity | Independent charge change at both interior endpoints of each driven edge | Relative error <=1e-13; pass |
| Source failures | Nonfinite, duplicate, H, wall, out-of-range, mismatched grid; preflight overflow and finite-increment addition overflow after mutation | Rejected; terminal errors carry state/component/index; failed fields/times inaccessible |
| Initial screening | Nonzero-divergence E remains rejected; existing six-component wall/nonfinite regressions retained | Pass |
| S07 probes | n=0/1/2, all six components and axes, exact integer labels, independent native coordinates/time and signed source values | v1 time/coordinate budget <=5e-15 with floors; pass |
| S07 independent harmonic estimator | Both signs/directions and native offsets/times; worst complex impedance relative error 2.6666e-16 | <=1e-12; pass; zero/weak H, insufficient/nonfinite data and singular fit rejected |
| S08 initial fixture identities | Six orientations on primary p24 grids; four V03 fixture configurations | Worst normalized divergence 1.96348e-16, plateau error 7.54952e-15, both <=1e-11; walls exactly zero |
| Suite preflight | All 36 propagation/four stability configurations generated without allocating their field volumes | Native guards, time and transient allocation budget pass; invalid smoke guard rejected |
| End-to-end smoke | Three cases, two steps, native raw samples including initial negative H time | Independent JSON/CSV checks pass |
| Reproducibility/output lifecycle | Both raw CSV files for each smoke case identical across repeated runs | Byte-for-byte pass; existing output unchanged on rejected rerun; malformed/incomplete artifacts rejected |
| Prior independent audits | Yee convention audit, benchmark analytical audit, 513-sample/five-stage Fraction oracle | All pass; deterministic calculations, not measured physics |

The Python harmonic estimator is an independent measurement implementation;
the synthetic tests use prescribed frequencies, not production solver output.
The fixture generator and energy diagnostic use axis-permutation differences
separate from the production curl kernel. REF-05 still needs independent
diagnostic reduction checks and full physical measurements before accepting U/Q
traces, dispersion, impedance or refinement results.

## Raw artifacts and resource measurements

The durable compact result is the tracked
[REF-04 audit summary](REF-04-audit-summary.json). Its source commit, fingerprint,
measured results, and limitations correspond to the manifest above. The original
local raw Release audit was generated under `build/evidence/REF-04/` and contained
`first/`, `repeat/`, and `audit.json`. Both successful runs include three case directories, each with
`configuration.json`, `metadata.json`, `probes.csv`, and `diagnostics.csv`; propagation diagnostics
are header-only because its required observable is the native line. The suite's
`COMPLETE.json` appears only after all streams close and the temporary marker
is renamed. Invalid/incomplete audit fixtures are deliberately retained too.

| Resource | First run | Repeat |
| --- | --- | --- |
| Process elapsed time | 0.5339 s | 0.5362 s |
| Observed Windows peak working set | 20,070,400 bytes | 20,078,592 bytes |
| p24 propagation declared working budget | 33,152,128 bytes | Same |
| Overall run limit | 2,147,483,648 bytes | Same |

Peak working set was sampled using psutil's Windows high-water counter at 10 ms
polls; this is process resident memory, not a heap-allocation proof. Field
construction separately accounts for two payloads, maximum source capacity,
probe storage and 16 MiB overhead before allocation. The largest planned p96
payload remains 489.380 MiB per field owner (two owners at construction); actual
full-suite peak memory and elapsed time remain REF-05 measurements.

Environment: Windows x64, AMD Ryzen 5 3600 / 12 logical threads (runtime identifier
`AMD64 Family 23 Model 113 Stepping 0, AuthenticAMD`), project-local LLVM-MinGW
20250613 / Clang 20.1.7, CMake/CTest 3.31.10, strict binary64 without fast math
or contraction. See [environment record](../ENVIRONMENT.md). CTest discovered
Python 3.10; its standard-library artifact checks passed, but psutil was absent
there and memory was reported unavailable. The separate final audit used the
existing Anaconda Python 3.9.7 with psutil; no package installation was needed.
Runs/builds overlapped during validation, so timings are observations, not a
performance baseline or projected schedule.

## Reproduction

From the repository root, using fresh output locations:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
python scripts/generate_reference_steps.py
$env:PATH = (Join-Path (Get-Location) '.tools/llvm-mingw-20250613-ucrt-x86_64/bin') + ';' + $env:PATH
python scripts/check_reference_runs.py --app build/windows-local-release/antennasim.exe --output-root build/evidence/REF-04
```

The last command creates a unique audit subdirectory, runs the CLI twice, tests
its rejection paths, and retains evidence. CTest runs the same audit under
`reference.run_artifacts`; Python is required for validation builds. Direct CLI syntax and its
runtime PATH requirement are documented in the root README. Full fixed suites
are implemented but not executed here; their physical analyzer remains REF-05.

Local raw logs remain reproducible build output rather than repository evidence.
The tracked summary and source manifest preserve the compact durable record;
GitHub CI retains CTest logs and smoke artifacts for each hosted run.

## Failures, limits, and next action

- The sandbox denied starting the compiler, matching the recorded environment
  constraint. Approved execution completed both configurations.
- The golden script was first invoked with unsupported `--check`; its documented
  no-argument check then passed. No fixture was regenerated to fit solver output.
- A standalone smoke audit without compiler runtime PATH stalled at startup;
  only that launched process was stopped. Supplying the runtime PATH resolved it;
  CTest already inherited that path. The audit now bounds subprocess duration.
- A signedness warning in JSON escaping was corrected explicitly. Final builds
  have no warnings. No numerical test failed or tolerance was loosened.
- Only six primary p24 initial fixtures and the V03 shapes were structurally
  executed; the full runner checks S08 on each larger case before stepping.
  Full 36-case propagation, enlarged-domain comparison, three-mesh refinement,
  source cutoff/20,000-step stability, clean Release physical reproduction,
  sanitizer, other compiler and cross-platform checks were not run here.

Next: REF-05's independent artifact analyzer, diagnostic/measurement checks,
full physical runs, resource observations and retained pass/failure reports.
Keep all eleven current CTests (the original eight plus three integrated audits).
C03 awaits a measured physical report and P1 awaits its evidence gate. No
antenna/port capability is implied.
