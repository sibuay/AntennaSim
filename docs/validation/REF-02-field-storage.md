# REF-02 — Staggered field storage evidence

Date: 2026-09-07. Decision: **REF-02 complete; REF-03 ready; P1/C02 remain open.**
Scope: production field storage, index/coordinate access, and wall classification.
No electromagnetic update, physical benchmark, or stability claim is included.

Identity: local snapshot, no Git repository/revision. The
[SHA-256 manifest](REF-02-source-sha256.txt) identifies source, tests, contracts,
project records, and retained build/audit logs. The fixed FND-03/FND-04
specifications, analytical scripts, foundation checks, and reference.grid test
source are unchanged from REF-01.

Review: same implementation collaborator; no independent human or second-agent
review. Literal coordinate/extent tables, enumerated offsets, physical-face
comparisons, and the test-only stencil specification are independent comparators
to production routines; this does not make the reviewer independent.

## Implementation and acceptance

The [storage contract](../methods/REF-02-field-storage-contract.md) was recorded
before implementation, using the existing FND-03 conventions and fixed S01/S02
requirements. Literal wall totals were corrected during pre-test arithmetic
review by subtracting interior-edge counts from full extents. No benchmark
threshold was changed, and no solver output was used as a reference.

Production files: [grid.hpp](../../include/antennasim/grid.hpp),
[grid.cpp](../../src/grid.cpp), [fields.hpp](../../include/antennasim/fields.hpp),
and [fields.cpp](../../src/fields.cpp). The standalone
[fields_check.cpp](../../tests/fields_check.cpp) is registered as
`reference.fields`, labels `fast;reference_structural`, timeout ten seconds.

| Obligation | Evidence | Result |
| --- | --- | --- |
| Six exact binary64 arrays | All six sizes and every initial positive-zero value on (2,2,2), (2,3,4), (5,4,3); actual allocation at exact 48-element/1848-byte caps | Pass, exact |
| Native positions and flattening | Every coordinate compared with literal node/half-coordinate sequences at spacing (2,3,5); every offset equals the sequential enumeration counter | Pass, exact |
| Contiguous and independent storage | Mutable/const sample addresses match component base plus ordinal; component-distinct markers survive filling all six arrays; separate owner starts at zero and does not alias | Pass |
| Bounds and selectors | One-past and size_t maximum on each axis for all components through offset, position, both wall predicates, mutable/const access; invalid selectors through every new API; all markers unchanged afterward | Pass with out_of_range / invalid_argument respectively |
| Wall geometry | Every sample classified against physical zero/endpoint coordinates; all endpoint planes and allocated edge intersections included; literal union counts checked without duplicate counting | Pass, exact |
| No implicit boundary enforcement | Classification and read/error paths preserve every nonzero marker, including wall samples | Pass for storage only |
| Stencil access geometry | Every four-read stencil in all six prescribed ranges uses production checked storage; both pair midpoints match target and separation matches derivative axis/spacing | Pass: 168 / 508 / 1300 reads on the three grids, 1976 total |
| Extreme accepted geometry | Every coordinate finite, in domain, and strictly ordered at resolvable subnormal and largest-finite spacings on each axis; first half coordinates and node endpoints checked | Pass without large allocation |
| Owner invariant | No public resizing/mutable grid; compile-time checks for const views, mutable/const references, disabled copy/move/assignment | Pass; D013 documents deliberate initial scope |
| Prior regressions | Three foundation tests and 136 runtime grid checks retained | Pass in both configurations |

No field sample lies at a geometric box corner under these Yee placements.
The exhaustive native-sample enumeration covers the allocated faces and edge
intersections instead of inventing collocated corner fields. The storage totals
are 90/231/513 samples and 720/1848/4104 payload bytes: deterministic counts,
not measured peak memory or solver performance.

Offset safety review: with i<sx, j<sy, k<sz, `j+sy*k < sy*sz` and the final
offset is below sx*sy*sz. All extents are positive and that product was checked
in REF-01, so these intermediates fit size_t. Bounds are checked before any
offset arithmetic; signed test stencil shifts are checked before conversion.
Component validation precedes vector or half-offset table access. Construction
uses vector RAII; allocation failure propagates without a partially usable owner.

## Executed checks

Environment: established Windows x64 LLVM-MinGW 20250613 UCRT / Clang 20.1.7,
CMake/CTest 3.31.10, Ninja 1.11.1.git.kitware.jobserver-1, Python 3.9.7.
Incremental Debug/Release configure/build/test used approved execution outside
the sandbox, following the documented compiler restriction. This is not a new
clean-build gate or a claim that the compiler works inside the sandbox.

Commands from the project root:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
```

| Configuration | Compile | CTest | Field-storage checks | Field-test time | CTest total |
| --- | --- | --- | --- | --- | --- |
| Debug | Pass, no warnings reported | 5/5 pass | 23838, zero failures; 1976 reads | 0.11 s | 0.58 s |
| Release | Pass, no warnings reported | 5/5 pass | 23838, zero failures; 1976 reads | 0.07 s | 0.42 s |

Assertions are explicit runtime failure checks and remain active in Release.
Both analytical audits pass unchanged: twelve midpoint/axis and six affine curl
checks, 676 specification-only stencil reads, fixed analytical dispersion and
refinement budgets, signed synthetic fits, eighteen exact modal invariant
identities, and two weighted-adjoint identities. These audits do not run a solver.

Retained local logs:

- `build/REF-02-{Debug,Release}-build-test.log`
- `build/REF-02-{Debug,Release}-LastTest.log`
- `build/REF-02-conventions-audit.log`
- `build/REF-02-benchmarks-audit.log`

No build/test failures or compiler warnings occurred. No numerical tolerance
was loosened. Source review after the passing runs found no required code change.

## Limits and next action

S01's storage/access obligations are satisfied. Its stencil coverage uses a
test-only range/stencil harness; REF-03 must exercise actual update loops and
all twelve signed derivative contributions, retaining these storage regressions.
S02's classification/default-zero subset passes, but normal-H preservation,
boundary enforcement, and nonzero unconstrained evolution need the REF-03 kernel.

Raw storage accepts arbitrary double writes; it is not a run validator and
does not silently repair invalid initial data. Non-finite fields, wall and
divergence compatibility, CFL/coefficient/time representability, source/probe
rules, and run/CLI validation remain REF-03/04 work as applicable.

Not run: physical V01–V03, field evolution, long-time stability, runtime/peak-memory
benchmarks (no update kernel yet), allocation-failure injection, sanitizers,
other platforms/compilers, or 32-bit builds. Available-RAM success and allocation
failure recovery are not established by the small fixtures. Same-author and
Windows-x64-only review limitations remain explicit.

**Next exact action: REF-03.** Write its concrete time-step/coefficient/update
API and independent S02–S06 acceptance contract under the existing fixed
specifications before implementation. Add strict CFL selection, reference H-then-E
updates and boundary handling; preserve all five CTest checks and both analytical
audits. Source/probe/CLI work remains REF-04, physical measurements REF-05.
