# Development environment

Inspected and exercised on 2026-09-05 for FND-01/FND-02.

## Observed machine

| Component | Observation |
| --- | --- |
| OS | Windows 10, build 19045, x64 |
| CPU | AMD Ryzen 5 3600; 6 physical cores / 12 logical processors |
| Physical memory | 17,125,847,040 bytes reported by psutil (approximately 15.95 GiB usable physical RAM) |
| GPU | NVIDIA GeForce RTX 2060, 6144 MiB VRAM; driver 560.94 |
| Python on PATH | Anaconda Python 3.9.7; pip 21.2.4; psutil available |
| Git on PATH | 2.46.2.windows.1; this directory is not yet a Git repository |

CIM hardware queries were denied in the execution sandbox. CPU information was
read from the processor registry key and psutil; memory from psutil; GPU details
from `nvidia-smi`. CUDA development tools and GPU compute were not tested.

Visual Studio Community 2019 16.10.4 and Enterprise 2019 16.3.5 have installation
records. The inspected Community MSVC 14.29 directory contains auxiliary/library
files but no compiler executable or headers. No usable `cl.exe` was found in the
Visual Studio trees. Treat installation records as insufficient proof of a working
toolchain. No Visual Studio repair was performed.

MATLAB R2023b contains CMake 3.25.0 and Ninja 1.10.2, but the inspected CMake bin
directory has no CTest. These application-owned copies are not the selected tools.

## Selected local toolchain

| Tool | Pinned distribution / verified binary | Location relative to project |
| --- | --- | --- |
| Compiler and C++ standard library | LLVM-MinGW 20250613 UCRT x64; Clang 20.1.7, target x86_64-w64-windows-gnu | `.tools/llvm-mingw-20250613-ucrt-x86_64/bin/` |
| CMake and CTest | PyPI package cmake 3.31.10; binaries report 3.31.10 | `.tools/cmake/cmake/data/bin/` |
| Build runner | PyPI package ninja 1.11.1.4; binary reports 1.11.1.git.kitware.jobserver-1 | `.tools/cmake/bin/ninja.exe` |
| Test harness | CTest plus a small standalone C++ executable and CMake CLI checks | Source in `tests/` |

The tools live entirely under the ignored `.tools` directory. Project presets
provide the compiler runtime DLL search path to configure/build/test subprocesses.
`.tools/cmake/bin/cmake.exe` and `ctest.exe` are pip console launchers that need
the installing Python on PATH and fail elsewhere with a `No module named 'cmake'`
traceback; invoke the real binaries under `.tools/cmake/cmake/data/bin/` instead.
The `ninja.exe` launcher in `.tools/cmake/bin/` is self-contained and is the one
the presets use.
No global PATH, system compiler installation, or global Python package was changed.
The existing Python environment emitted a pre-existing invalid-distribution `-ffi`
warning during pip use; package installation still succeeded.

This is a CPU foundation toolchain. A future CUDA build may require a supported
MSVC host toolchain; today's choice does not establish CUDA compatibility.

## Recreate the tools on Windows x64

Run from the project root with Python/pip available and network access, using a
fresh `.tools` location. These are the pinned packages and archive used here:

```powershell
python -m pip install --target .tools/cmake --no-cache-dir --disable-pip-version-check --only-binary=:all: cmake==3.31.10 ninja==1.11.1.4
if ($LASTEXITCODE -ne 0) { throw 'Build-tool download failed' }
$taskCompilerUrl = 'https://github.com/mstorsjo/llvm-mingw/releases/download/20250613/llvm-mingw-20250613-ucrt-x86_64.zip'
Invoke-WebRequest -Uri $taskCompilerUrl -OutFile .tools/llvm-mingw-20250613-ucrt-x86_64.zip
$taskDigest = (Get-FileHash -LiteralPath .tools/llvm-mingw-20250613-ucrt-x86_64.zip -Algorithm SHA256).Hash
if ($taskDigest -ne '45145c035d9246e1de16f1873aa9afa863d93909f4a8f363e2eb38a04031d3c3') { throw 'Compiler archive digest mismatch' }
Expand-Archive -LiteralPath .tools/llvm-mingw-20250613-ucrt-x86_64.zip -DestinationPath .tools
```

The compiler archive is 152,446,205 bytes. Its SHA-256 matched the digest returned
by the official release API. The saved local asset metadata is
`.tools/llvm-mingw-asset.json`. Do not commit downloaded tools or archives.

Sources: [LLVM-MinGW release](https://github.com/mstorsjo/llvm-mingw/releases/tag/20250613),
[CMake package](https://pypi.org/project/cmake/3.31.10/),
[Ninja package](https://pypi.org/project/ninja/1.11.1.4/), and
[CMake preset documentation](https://cmake.org/cmake/help/v3.31/manual/cmake-presets.7.html).

## Verified build and test entry point

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

The helper runs configure, build, and CTest in order and fails at the first failed
stage. Both commands passed from initially absent build directories. Generated
outputs live under `build/windows-local-debug` and `build/windows-local-release`.

For individual steps, invoke the local tools from the root:

```powershell
& ./.tools/cmake/cmake/data/bin/cmake.exe --preset windows-local-debug
& ./.tools/cmake/cmake/data/bin/cmake.exe --build --preset windows-local-debug
& ./.tools/cmake/cmake/data/bin/ctest.exe --preset windows-local-debug
```

The execution sandbox denied starting the portable compiler during P0. The build
commands then succeeded through approved elevated tool execution; this was an
environment access constraint, not an observed compiler failure. On 2026-09-16 the
compiler, CTest, and the full benchmark suites ran inside the ordinary session
sandbox without approval. Network access previously required approved execution.
Ordinary local terminal use may not have these restrictions.

Generic `debug` and `release` presets also exist for an independently configured
C++20 compiler and Ninja on PATH. Those combinations, MSVC, Linux, and macOS have
not been tested. See [foundation evidence](validation/FND-02-build.md).

## Hosted validation

GitHub is the selected source-control and CI host as of 2026-09-11. The workflow
in `.github/workflows/ci.yml` configures independent Debug and Release builds on
`ubuntu-latest`, pins Python 3.13, runs the complete CTest suite, and retains test
logs, source-snapshot inputs, and smoke-audit outputs for 90 days. It uses read-only
repository permissions. The first hosted result is pending the workflow commit
reaching GitHub; until then this is configured coverage, not a recorded CI pass.

Python is a required dependency whenever `BUILD_TESTING=ON`. CMake configuration
fails if the interpreter is unavailable, and all convention, benchmark-specification,
golden-state, and CLI artifact audits are registered in CTest. This prevents a
reduced validation suite from being reported as a successful full run.
