# REF-01 — Core grid API and structural acceptance

Date: 2026-09-06. Recorded before implementation. Scope: metadata and validation;
no electromagnetic update, field allocation, or numerical accuracy claim.

## Basis and API choices

Use [FND-03](FND-03-yee-conventions.md) for the six Yee extents, SI spacings,
minimum two cells per axis, binary64, and checked allocation arithmetic.
The independent acceptance basis is S01 and the applicable input-policy part
of V03 in [FND-04](../validation/FND-04-reference-benchmarks.md). Their fixed
thresholds are unchanged. No new electromagnetic equation is introduced.

- `CellCounts(x,y,z)` accepts integral C++ arguments except bool, rejects values
  below two before unsigned conversion, and checks the size_t range. Floating
  arguments are unavailable at compile time; malformed/fractional text is
  REF-04 parsing work. Counts are immutable through the public interface.
- `UniformGrid` owns validated counts, three spacings in metres, domain lengths,
  six component layouts (extents and element counts), aggregate field elements,
  and aggregate binary64 bytes. It allocates no fields and exposes const data.
  `FieldComponent` selects a layout; an invalid enum value fails explicitly.
- Use `std::invalid_argument` for unsupported counts, invalid spacings, and
  component selectors; `std::length_error` for size arithmetic, container limits,
  and user allocation caps; `std::overflow_error` for nonrepresentable geometry.
  Tests assert categories, not prose. Failed construction produces no grid.
- `AllocationLimits` can lower maximum elements per component and aggregate
  field bytes. Defaults impose size_t arithmetic and the real empty
  `std::vector<double>::max_size()` limit; a supplied larger component cap cannot
  raise the container limit. Zero caps reject nonempty grids. These are storage
  feasibility bounds, not available-RAM promises. Later field allocation can
  still throw `std::bad_alloc`; the REF-04 working-memory budget also includes
  fixture, diagnostic, and output overhead.
- Checked size addition/multiplication live in a small internal detail header.
  Compute all extent additions, each two-stage extent product, total elements,
  and byte product before checking container/caller limits and geometry.
  The order lets structural tests distinguish arithmetic failures from later
  representability checks without allocating memory.

## Geometry representability

For each axis require finite positive d and finite positive L=N*d. Require
N<=2^52 so every required integer/half index through N is exactly representable
in binary64. Also require d/2>0 and

```text
d/2 >= L - nextafter(L, 0)
```

The right side is the largest binary64 spacing below the positive endpoint L.
This conservative guard keeps successive half-grid locations resolvable across
the domain; rejecting a grid can be stricter than checking a few endpoints.
All component coordinates lie between zero and L. Subnormal spacings are not
blanket-rejected: they must meet these geometry checks. A grid that passes them
still needs independent coefficient, CFL, and timestamp validation in REF-03/04.
No stability capability follows from a geometry-only API.

## Independent checks fixed for REF-01

| Fixture | Expected component element counts, Ex/Ey/Ez/Hx/Hy/Hz | Aggregate bytes |
| --- | --- | --- |
| Cells (2,2,2) | 18,18,18,12,12,12 | 720 |
| Cells (2,3,4) | 40,45,48,36,32,30 | 1848 |
| Cells (5,4,3) | 100,96,90,72,75,80 | 4104 |

Compare all six extents against separately written literal tables. With spacings
(2,3,5), domain lengths must equal (4,6,10), (4,9,20), and (10,12,15) exactly.
Use unequal spacings and all three axis permutations for invalid inputs.

Required failure coverage: negative/zero/one counts; floating and bool count
construction unavailable; zero/negative/NaN/infinite spacings; extent increment,
component-product, total-element, and byte overflow from size_t-derived inputs;
exact-boundary/one-too-small component and byte caps; real container limit cannot
be raised; invalid component selectors; overflowing lengths; a half spacing that
underflows; counts beyond exact half-index range; and unresolved half coordinates.
Check safe checked-arithmetic boundaries directly, including multiplication by
zero. For cells (x,2,2), independently expanded total elements are 37*x+16;
use this polynomial to target total and byte overflow without huge allocation.
Tests remain effective in Release and carry `fast;reference_structural` labels.

S01 native positions/flattening/stencil access are REF-02 work. Wall/field
compatibility, CFL, source, probe, time/run, and CLI validation stay with their
owning REF items. Do not report all of S01 or V03 passed after REF-01.

Build/test Debug and Release, retain the foundation regressions, run both
existing analytical audits, and record actual outcomes in
`docs/validation/REF-01-core-grid.md`. Same-author review is the available review
mode. Any failed check requires investigation rather than relaxing acceptance.
