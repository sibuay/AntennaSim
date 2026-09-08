"""Exact-arithmetic audit of FND-03's transcribed layout and curl stencils.

This is a method-note review aid, not an FDTD solver or a production-kernel
test. It does not parse the Markdown; agreement between the transcription and
the note must also be reviewed. Run with Python 3.9+; no packages are needed.
"""

from fractions import Fraction as Q
from itertools import product


PLACEMENT = {
    "Ex": (Q(1, 2), 0, 0), "Ey": (0, Q(1, 2), 0),
    "Ez": (0, 0, Q(1, 2)), "Hx": (0, Q(1, 2), Q(1, 2)),
    "Hy": (Q(1, 2), 0, Q(1, 2)), "Hz": (Q(1, 2), Q(1, 2), 0),
}
# Each term is (sign, source, positive endpoint offset, negative endpoint
# offset, derivative axis). H uses forward differences, E backward differences.
STENCIL = {
    "Hx": [(1, "Ey", (0, 0, 1), (0, 0, 0), 2),
           (-1, "Ez", (0, 1, 0), (0, 0, 0), 1)],
    "Hy": [(1, "Ez", (1, 0, 0), (0, 0, 0), 0),
           (-1, "Ex", (0, 0, 1), (0, 0, 0), 2)],
    "Hz": [(1, "Ex", (0, 1, 0), (0, 0, 0), 1),
           (-1, "Ey", (1, 0, 0), (0, 0, 0), 0)],
    "Ex": [(1, "Hz", (0, 0, 0), (0, -1, 0), 1),
           (-1, "Hy", (0, 0, 0), (0, 0, -1), 2)],
    "Ey": [(1, "Hx", (0, 0, 0), (0, 0, -1), 2),
           (-1, "Hz", (0, 0, 0), (-1, 0, 0), 0)],
    "Ez": [(1, "Hy", (0, 0, 0), (-1, 0, 0), 0),
           (-1, "Hx", (0, 0, 0), (0, -1, 0), 1)],
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def point(component, index, spacing):
    return tuple((index[a] + PLACEMENT[component][a]) * spacing[a]
                 for a in range(3))


def extents(component, cells):
    return tuple(cells[a] + (PLACEMENT[component][a] == 0)
                 for a in range(3))


def audit():
    spacing = (Q(2), Q(3), Q(5))
    # Independent continuous curl of F=(2x+3y+5z, 7x+11y+13z,
    # 17x+19y+23z) is (6,-12,4). Units may be supplied by the
    # corresponding affine coefficients; only geometric derivatives are audited.
    gradient = ((2, 3, 5), (7, 11, 13), (17, 19, 23))
    curl = (gradient[2][1] - gradient[1][2],
            gradient[0][2] - gradient[2][0],
            gradient[1][0] - gradient[0][1])
    term_count = 0
    for target, terms in STENCIL.items():
        total = Q(0)
        for sign, source, high, low, axis in terms:
            hi, lo = point(source, high, spacing), point(source, low, spacing)
            midpoint = tuple((hi[a] + lo[a]) / 2 for a in range(3))
            require(midpoint == point(target, (0, 0, 0), spacing),
                    f"{target}/{source}: misplaced derivative")
            require(tuple(hi[a] - lo[a] for a in range(3)) ==
                    tuple(spacing[a] if a == axis else 0 for a in range(3)),
                    f"{target}/{source}: incorrect derivative axis/length")
            slopes = gradient["xyz".index(source[1])]
            total += sign * sum(slopes[a] * (hi[a] - lo[a])
                                for a in range(3)) / spacing[axis]
            term_count += 1
        expected = curl["xyz".index(target[1])]
        if target[0] == "H":
            expected = -expected
        require(total == expected, f"{target}: incorrect curl sign/value")
    print(f"PASS: {term_count} derivative midpoints/axes; six affine curl increments")

    reads = 0
    for cells in ((2, 2, 2), (2, 3, 4)):
        count = 0
        for target, terms in STENCIL.items():
            shape = extents(target, cells)
            count += shape[0] * shape[1] * shape[2]
            indices = list(product(*(range(s) for s in shape)))
            flat = {i + shape[0] * (j + shape[1] * k) for i, j, k in indices}
            require(flat == set(range(len(indices))), f"{target}: flattening")
            for index in indices:
                constrained = target[0] == "E" and any(
                    PLACEMENT[target][a] == 0 and index[a] in (0, cells[a])
                    for a in range(3))
                if constrained:
                    continue
                for _, source, high, low, _ in terms:
                    source_shape = extents(source, cells)
                    for offset in (high, low):
                        require(all(0 <= index[a] + offset[a] < source_shape[a]
                                    for a in range(3)), f"{target}: out-of-bounds read")
                        reads += 1
        expected_count = 90 if cells == (2, 2, 2) else 231
        require(count == expected_count, f"{cells}: field count")
        print(f"PASS: cells={cells}, fields={count}, binary64 bytes={8 * count}")
    print(f"PASS: {reads} stencil endpoint reads in bounds; contiguous unique offsets")
    print("LIMIT: specification audit only; no time integration or physical validation")


if __name__ == "__main__":
    audit()
