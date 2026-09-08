# REF-02 — Field storage and indexing contract

Date: 2026-09-07. Recorded before implementation. Scope: storage and structural
geometry checks only; no new electromagnetic method or stability claim.

Basis: [FND-03 spatial layout and provisional boundary](FND-03-yee-conventions.md)
and the fixed [FND-04 S01/S02 requirements](../validation/FND-04-reference-benchmarks.md).
Those equations, sources, assumptions, SI conventions, and thresholds remain
unchanged. Time levels become operational in REF-03; storage has no clock.

## API and invariants

- Add `UniformGrid::offset(component, index)` and `position_m(component, index)`.
  Indices are three size_t values. Check the component and each axis before
  arithmetic. Unknown selectors throw invalid_argument; invalid indices throw
  out_of_range, including negative integers explicitly converted to size_t.
  Text and fractional-input parsing remains REF-04.
- Offset is `i + sx*(j + sy*k)`, using the selected component's exact extents.
  Once all three indices pass bounds checks, the REF-01 checked extent products
  prove every intermediate and result fits size_t. No per-access overflow
  arithmetic is necessary beyond this proof; no wrapping or ghost reads.
- Coordinates are `(double(index[a]) + half_offset[a])*spacing[a]` with the
  six literal half offsets from FND-03. REF-01 guarantees exact integer/half
  indices and representable geometry. Coordinates are deterministic binary64
  calculations; only the specified representable fixtures require exact equality.
- Add checked `is_tangential_e_wall` and `is_normal_h_wall` predicates on the
  grid. Tangential E is the union of its two transverse endpoint planes;
  normal H is on its own axis's endpoint planes. Each predicate returns false
  for the other field family. These classify samples without modifying fields.
- `FieldStorage` owns a grid value and six separate vector<double> arrays,
  sized from its validated layouts and initialized to positive zero. Construction
  may throw bad_alloc; RAII releases partially allocated arrays. The existing
  allocation cap bounds payload, not RAM availability or container overhead.
- Storage exposes its grid by const reference, checked mutable/const `at`, and
  const contiguous `values(component)` spans for inspection. No resizing,
  assignment, copying, or moving is supported in this initial owner API: the
  grid and arrays retain one fixed identity and outstanding references remain
  valid until destruction. Revisit transfer semantics only with a concrete run
  or checkpoint requirement. No large implicit field copies are introduced.
- Raw writes may contain arbitrary binary64 values. Storage does not validate
  supplied physical initial conditions, divergence, finiteness, or wall values;
  public run validation/enforcement belongs to REF-03/04. Do not silently clamp
  data here. Boundary evolution and absence of unintended zeroing remain S02
  kernel obligations in REF-03.

## Independent acceptance specification

Use all three S01 fixtures: cells (2,2,2), (2,3,4), (5,4,3), spacing (2,3,5) m.
Tests use literal six-component extent/half-offset tables and count offsets by
enumeration, rather than computing expected offsets with the production formula.

1. Every array has its literal expected size and every sample starts at +0.
   Enumerate k/j/i; offsets must equal a monotonically increasing counter,
   addresses must equal contiguous base plus counter, and all coordinates must
   equal independently enumerated integer/half-coordinate sequences exactly.
   Fill component-distinct unique markers and read all arrays back after filling
   all six; check isolation between components and separate storage instances.
2. Check each first/last index and every one-past axis, size_t maximum on every
   axis, and invalid selectors through every public component/index operation.
   Failure must leave valid field samples unchanged; const access also rejects.
3. Walk every allocated location and classify walls independently using native
   physical coordinates equal to zero/domain length. Check faces and their
   intersections, including union counting without duplicates. Expected E-wall
   totals Ex/Ey/Ez are (16,16,16), (28,36,40), (70,64,54); normal-H totals are
   (8,8,8), (24,16,12), (24,30,40). Classification must not change any marker.
4. For every target in FND-03's six update ranges, enumerate all four neighbour
   reads through production storage using an explicit test-only stencil table.
   All reads must succeed, each pair midpoint must equal the target coordinate,
   and pair separation must equal the declared unequal spacing along only its
   derivative axis. Check each omitted E target is exactly a tangential wall.
   This validates access geometry, not curl signs, arithmetic, or production
   update loop ranges, which must receive S01/S03 regressions in REF-03.
5. Exercise actual storage with exact 48-element/1848-byte allocation limits.
   Test extreme accepted grid coordinates without allocating large arrays:
   resolvable subnormal spacing and largest finite endpoint on each axis.

Integer, marker, zero, and representable-coordinate comparisons are exact;
no tolerance is added or relaxed. Build/run Debug and Release, retain the three
foundation checks and reference.grid, and rerun both analytical audits. Record
environment, counts, timing, failures, snapshot hashes, and same-author review
limitations in `docs/validation/REF-02-field-storage.md` before closing REF-02.
