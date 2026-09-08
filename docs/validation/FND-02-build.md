# FND-02 — Build foundation evidence

Date: 2026-09-05. Status: **pass for infrastructure only**.
Code identity: local foundation scaffold snapshot; no Git revision exists yet.
Source-file SHA-256 identities are recorded in
[FND-02-source-sha256.txt](FND-02-source-sha256.txt).
Environment: [verified local toolchain](../ENVIRONMENT.md).

## Scope and results

Created a C++20 static core library, a CLI linked to that library, CMake presets,
a build helper, and CTest checks. The core currently exposes build metadata only.
The CLI supports help/version and explicitly fails unsupported simulation requests.
Version `0.0.0` identifies a scaffold, not an engineering release.

| Check | Debug | Release |
| --- | --- | --- |
| Configure from an absent build directory | Pass | Pass |
| Build core library and both executables | Pass; no reported compiler warnings | Pass; no reported compiler warnings |
| foundation.toolchain: concepts, span, binary64 capability, library linkage | Pass | Pass |
| foundation.cli_help: explicit unimplemented-solver notice | Pass | Pass |
| foundation.cli_contract: version and unsupported-request error contract | Pass | Pass |
| CTest summary | 3/3 passed, 0.25 s wall time | 3/3 passed, 0.22 s wall time |

Commands:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

CTest logs are generated in each build directory under `Testing/Temporary/`.
Numerical/physical benchmarks run: **none**. This evidence does not validate
Maxwell updates, stability, wave propagation, or antenna quantities.

## Build policies

- C++20 features required on each target; compiler extensions disabled.
- Warnings enabled for the supported compiler families.
- Clang/GCC targets explicitly disable fast math and floating-point contraction;
  the MSVC branch selects strict floating-point mode but remains untested.
- CTest presets fail when no tests are discovered.
- No fetched C++ dependency or unit-test framework is needed for this scaffold.
- Checks use explicit failure returns, so they remain effective in Release builds.

This floating-point policy is an initial reproducibility precaution, not proof of
bitwise consistency across future platforms. Numerical precision/conventions are
still the subject of FND-03.

## Issues encountered and resolution

- Visual Studio installation metadata overstated the available compiler files:
  inspection found no usable compiler. Selected a complete portable LLVM-MinGW
  toolchain instead of treating the partial installation as usable.
- Initial pip network attempt failed in the sandbox; approved execution installed
  the pinned packages locally.
- The Ninja wheel places its executable in `bin/`, not `ninja/data/bin/`; corrected
  the preset before configuring.
- The sandbox denied launching Clang; approved build execution passed in both
  configurations.

Review: performed by the same implementation collaborator; no independent human
or second-agent review. FND-01 and FND-02 are complete. The Phase 0 gate remains
open pending FND-03 conventions, FND-04 benchmark specifications, and FND-05 review.
