# MNT-01 — Repository and validation hardening

2026-09-11, updated 2026-09-15. **Complete locally; commits pushed; first hosted
CI result pending.** This maintenance
item changes validation enforcement, source-control traceability, and evidence
retention. It does not change solver equations, benchmark thresholds, or physical
acceptance status.

## Changes

- Preserved the reviewed REF-04 source and documentation as commit
  `593064327251a8c408d617e6f0ef3c5ad57883ac` on `main`.
- Required Python whenever `BUILD_TESTING=ON`; missing Python now fails CMake
  configuration.
- Registered the Yee-convention, benchmark-specification, and exact golden-step
  scripts in CTest alongside the existing eight tests.
- Added read-only GitHub Actions Debug/Release validation on Ubuntu with Python
  3.13 and 90-day retention of CTest logs, source-snapshot inputs, and smoke output.
- Added a tracked [REF-04 compact audit summary](REF-04-audit-summary.json) and
  retained its exact [source manifest](REF-04-source-sha256.txt).
- Updated D016 and O005: GitHub source control/CI is resolved; licensing and public
  distribution remain an owner decision.

## Local checks

| Check | Result |
| --- | --- |
| Windows LLVM-MinGW Debug configure/build/CTest | 11/11 pass; 13.59 s; no compiler warnings |
| Windows LLVM-MinGW Release configure/build/CTest | 11/11 pass; 4.48 s; no compiler warnings |
| Windows Clang AddressSanitizer + UndefinedBehaviorSanitizer CTest | 11/11 pass; 54.53 s |
| Validation configure with `CMAKE_DISABLE_FIND_PACKAGE_Python3=TRUE` | Expected failure at required `find_package(Python3)`; pass |
| Git diff whitespace check | Pass |
| Local branches/worktrees | Only normal `main` checkout/branch observed |

The GitHub workflow was checked against the current official major versions of
`actions/checkout`, `actions/setup-python`, and `actions/upload-artifact`. A local
Windows run cannot establish the Ubuntu result; record the first hosted outcome
after the commit is pushed. No check was skipped or treated as a pass.

## Hosted run

| Date | Event | Result |
| --- | --- | --- |
| 2026-09-15 | `main` at `3043b39` (with `5930643`) pushed to `origin`; workflow trigger expected for that push | Pending: record the Debug and Release outcomes and run URL here |

A follow-up commit on 2026-09-15 removed an unused `<numeric>` include from
`benchmarks/reference.cpp` and documented the pip launcher shim in the environment
record; local clean Debug/Release builds pass 11/11 without warnings after it.
This item is Done only after the hosted run above is recorded as passing.

## Remaining limits and next action

GitHub branch protection and required-status settings are repository-host controls,
not source files, and were not changed. O005 still requires a license/distribution
decision before external distribution. REF-05 remains next: run and independently
analyze the full V01–V03 physical suites before any accuracy claim.
