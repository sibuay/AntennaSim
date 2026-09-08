# FND-03 — Numerical convention review evidence

Date: 2026-09-05. Decision: **FND-03 complete; P0 remains open**.
Scope: [version 1 method note](../methods/FND-03-yee-conventions.md) and its
[exact-arithmetic audit](../../scripts/check_yee_conventions.py).
Identity: local snapshot, no Git repository/revision. The nine source/build files
in [FND-02 identities](FND-02-source-sha256.txt) were checked and remain unchanged.
The new method/audit identities are in [FND-03 identities](FND-03-source-sha256.txt).

Review performed by the same implementation collaborator. No independent human
or second-agent review occurred. Published equations and a continuous affine
curl provide external mathematical comparators; this does not make the reviewer
independent. The audit transcribes the method note rather than parsing it and
does not exercise a production solver.

## Completion matrix

| Requirement | Evidence / result | Status |
| --- | --- | --- |
| Exact references and assumptions | Author-hosted Schneider chapters 7/9 and pinned NIST constant provenance, with section/equation locators in the method note | Pass for specification |
| Units, constants, precision, signs | SI E/H/J; derived consistent epsilon0/eta0; binary64; right-handed axes and signed plane-wave checks | Pass for specification |
| Locations, extents, layout | Six edge/face arrays, x-contiguous offsets, checked arithmetic, smallest supported cells declared | Pass for specification |
| Time stepping and equations | Six explicit curls, all twelve derivatives, current sign and half-step placement, startup/probe times, update ranges | Pass for specification |
| Boundary behavior | All six faces, edge/corner union, normal H startup constraint, reflecting nature, and isolation obligations documented | Pass for specification |
| Stability and failure policy | Unequal-spacing bound, strict q<1, default q=0.99, representability and non-finite rejection requirements | Pass for specification |
| Sampling and expected errors | Native samples distinguished from collocation; interpolation bias, dispersion, energy-diagnostic limits, and cost described | Pass for specification |
| Independent benchmark readiness | V01–V03 and structural obligations identified; geometry and tolerances remain FND-04 | Not yet a benchmark specification |
| Solver accuracy / phase gate | No electromagnetic implementation or measured physical results | Not run; P0 gate open |

## Mathematical audit

Reproduce from the project root with the existing Python 3.9.7 environment:

```powershell
python scripts/check_yee_conventions.py
```

The audit uses exact rational arithmetic and unequal spacings `(2,3,5)`.
These are deterministic calculations, not simulation outputs:

```text
PASS: 12 derivative midpoints/axes; six affine curl increments
PASS: cells=(2, 2, 2), fields=90, binary64 bytes=720
PASS: cells=(2, 3, 4), fields=231, binary64 bytes=1848
PASS: 676 stencil endpoint reads in bounds; contiguous unique offsets
LIMIT: specification audit only; no time integration or physical validation
```

The independent affine field is
`F=(2x+3y+5z, 7x+11y+13z, 17x+19y+23z)`, for which the continuous curl is
`(6,-12,4)`. E's normalized increment is that curl; H's is its negative.
All twelve difference-pair midpoints coincide with their target field location,
and each separation matches the stated derivative axis and spacing exactly.
The two grids exhaustively exercise the transcribed update-region endpoint
reads and offset bijections. Hand review checked that the note's half-open E
ranges equal the complement of its tangential-face constraints, while H updates
cover the entire allocated shape. No tolerance was needed or tuned.

The affine example is a local derivative check, not compatible initial data
for a reflecting-box physical run. The audit does not establish time-integration
accuracy, divergence preservation of an implemented kernel, source coupling,
boundary reflection accuracy, or long-time stability. Those remain P1/P2 work.

## Existing infrastructure regression

Commands repeated against the existing build trees:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

| Execution | Configure/build | CTest | Interpretation |
| --- | --- | --- | --- |
| Sandbox, Debug | Pass; Ninja had no work | 1/3 pass; CLI help/contract fail with startup code 0xc0000135 | Preserve failure; not a successful regression |
| Sandbox, Release | Pass; Ninja had no work | 1/3 pass; same CLI failures | Same execution restriction observed |
| Approved execution, Debug | Pass; Ninja had no work | 3/3 pass, 0.12 s | Existing infrastructure passes outside sandbox |
| Approved execution, Release | Pass; Ninja had no work | 3/3 pass, 0.12 s | Existing infrastructure passes outside sandbox |

The identical source/build configuration succeeds when execution leaves the
sandbox. This supports an environment-specific startup failure; the particular
DLL/access mechanism was not isolated. No C++ or build-policy change was needed.
The initial failure logs are retained locally as
`build/FND-03-debug-sandbox-LastTest.log` and
`build/FND-03-release-sandbox-LastTest.log`; successful logs are in each build
tree's `Testing/Temporary/LastTest.log`. Generated logs are not tracked evidence
artifacts; the failure and successful retry summaries above are preserved here.

This was an incremental build regression, not a new clean-build claim. FND-02
retains its earlier clean-build evidence. No physical benchmark was run because
no solver exists. Local Markdown file links were checked after the record updates.

## Decisions and exact next action

Decision D010 resolves O002; see [decision log](../DECISIONS.md).
FND-03 satisfies its documentation acceptance criterion. FND-04 is now ready:
write concrete V01–V03 and structural acceptance specifications using this
contract. Fix geometry, source/initial data, all-face boundary isolation,
native sample times/alignment, refinement sequence, independent comparators,
justified tolerances and review status, commands, resources, and evidence outputs.
In particular, a transversely uniform plane wave cannot be assumed compatible
with the reflecting box for arbitrarily long measurements.

FND-05 must then review the foundation gate. REF-01 stays planned until it
passes. There is no validated numerical capability and no change to the
milestone-based schedule or later phase scope.
