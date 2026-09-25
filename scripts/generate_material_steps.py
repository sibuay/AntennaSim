"""MAT-03 S11 exact-rational oracle of two full lossy material steps.

Generate with --write; otherwise compare the committed small golden header.
No production code or solver outputs are loaded. Python standard library only.

The binary64 inputs the C++ test uses (pinned mu0 and epsilon0, dt = 2^-30 s,
the S10 modular per-cell eps_r/sigma, the spacing) are converted to exact
fractions; every later operation (four-cell averages, the MAT-01 coefficients,
curls, both updates) is exact. The initial state is D-compatible: E is the
circulation of a modular H-type potential divided by the edge's relative
permittivity, so that div(eps_r,e E) = 0 exactly, and H is the circulation of
a modular E-type potential. The header stores the initial state and the two
full steps rounded to binary64.
"""
from fractions import Fraction as Q
from itertools import product
from pathlib import Path
import sys

CELLS = (5, 4, 3)
SPACING = tuple(map(Q, (2, 3, 5)))
DT = Q(1, 2**30)
MU0 = Q(1.25663706127e-6)
EPS0 = Q(1 / (1.25663706127e-6 * 299792458.0 * 299792458.0))
HALF = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0))  # half-integer axes


def extents(c):
    return tuple(CELLS[a] + (0 if HALF[c][a] else 1) for a in range(3))


def indices(c):
    return product(*(range(n) for n in extents(c)))


def constrained(c, idx):
    """Tangential outer-wall E or normal outer-wall H (integer coordinate on a face)."""
    return any(not HALF[c][a] and idx[a] in (0, CELLS[a]) for a in range(3))


def cell_value(i, j, k):
    return max(0, (17 * i + 31 * j + 43 * k) % 101 - 50)


def material(i, j, k):
    v = cell_value(i, j, k)
    return Q(1 + v / 60), Q(v / 50)      # exact fractions of the binary64 inputs


def edge_material(a, idx):
    """Exact mean over the four cells that share an interior E_a edge."""
    b, c = (a + 1) % 3, (a + 2) % 3
    eps, sigma = Q(0), Q(0)
    for db in (0, 1):
        for dc in (0, 1):
            cell = list(idx)
            cell[b] -= db
            cell[c] -= dc
            e, s = material(*cell)
            eps += e
            sigma += s
    return eps / 4, sigma / 4


def get(state, c, idx):
    if any(not 0 <= idx[a] < extents(c)[a] for a in range(3)):
        raise IndexError((c, idx))
    return state[c, tuple(idx)]


def curl(state, target, idx):
    """Explicit FND-03 component equations: forward differences of E for H
    targets, backward differences of H for E targets."""
    i, j, k = idx
    dx, dy, dz = SPACING
    if target >= 3:
        ex, ey, ez = (lambda p, c=c: get(state, c, p) for c in (0, 1, 2))
        if target == 3:
            return (ez((i, j + 1, k)) - ez((i, j, k))) / dy - (ey((i, j, k + 1)) - ey((i, j, k))) / dz
        if target == 4:
            return (ex((i, j, k + 1)) - ex((i, j, k))) / dz - (ez((i + 1, j, k)) - ez((i, j, k))) / dx
        return (ey((i + 1, j, k)) - ey((i, j, k))) / dx - (ex((i, j + 1, k)) - ex((i, j, k))) / dy
    hx, hy, hz = (lambda p, c=c: get(state, c, p) for c in (3, 4, 5))
    if target == 0:
        return (hz((i, j, k)) - hz((i, j - 1, k))) / dy - (hy((i, j, k)) - hy((i, j, k - 1))) / dz
    if target == 1:
        return (hx((i, j, k)) - hx((i, j, k - 1))) / dz - (hz((i, j, k)) - hz((i - 1, j, k))) / dx
    return (hy((i, j, k)) - hy((i - 1, j, k))) / dx - (hx((i, j, k)) - hx((i, j - 1, k))) / dy


def generate_states():
    keys = [(c, idx) for c in range(6) for idx in indices(c)]
    potential = {}
    for c, idx in keys:
        inside = all(1 <= idx[a] <= CELLS[a] - 1 for a in range(3))
        potential[c, idx] = Q((17 * idx[0] + 31 * idx[1] + 43 * idx[2] + 13 * c) % 101 - 50, 100) if inside else Q(0)
    initial = {}
    for c, idx in keys:
        if constrained(c, idx):
            initial[c, idx] = Q(0)
        elif c < 3:
            initial[c, idx] = curl(potential, c, idx) / edge_material(c, idx)[0]
        else:
            initial[c, idx] = curl(potential, c, idx)
    # Discrete Gauss law with the edge permittivity, and div H, exactly zero.
    for electric in (True, False):
        for node in product(*(range(1 if electric else 0, n) for n in CELLS)):
            div = Q(0)
            for a in range(3):
                hi, lo = list(node), list(node)
                if electric:
                    lo[a] -= 1
                else:
                    hi[a] += 1
                c = a + (0 if electric else 3)
                weight = (lambda p: edge_material(a, p)[0]) if electric else (lambda p: 1)
                div += (weight(tuple(hi)) * initial[c, tuple(hi)] - weight(tuple(lo)) * initial[c, tuple(lo)]) / SPACING[a]
            if div != 0:    # not an assert: python -O would strip it
                raise SystemExit('FAIL: exact %s divergence %s at node %s' % ('div(eps E)' if electric else 'div H', div, node))
    states = [initial]
    for _ in range(2):
        old = states[-1]
        new = dict(old)
        for c, idx in keys:
            if c >= 3 and not constrained(c, idx):
                new[c, idx] = old[c, idx] - DT / MU0 * curl(old, c, idx)
        for c, idx in keys:
            if c < 3 and not constrained(c, idx):
                eps_r, sigma = edge_material(c, idx)
                eps = eps_r * EPS0
                x = sigma * DT / (2 * eps)
                ca, cb = (1 - x) / (1 + x), (DT / eps) / (1 + x)
                new[c, idx] = ca * old[c, idx] + cb * curl(new, c, idx)
        states.append(new)
    return keys, states


def generate():
    keys, states = generate_states()
    lines = [
        '// Generated by scripts/generate_material_steps.py; exact rational oracle, not solver output.',
        '#pragma once', '#include <array>', '#include <cstddef>',
        'namespace material_golden {',
        'struct Sample { std::size_t component; std::array<std::size_t, 3> index; std::array<double, 3> stages; };',
        'inline constexpr std::array<Sample, %d> samples{{' % len(keys),
    ]
    for c, idx in keys:
        values = ', '.join(float(s[c, idx]).hex() for s in states)
        lines.append('    {%d, {%s}, {%s}},' % (c, ', '.join(map(str, idx)), values))
    lines.extend(['}};', '} // namespace material_golden', ''])
    return '\n'.join(lines)


def main():
    output = Path(__file__).resolve().parents[1] / 'tests/material_steps_golden.hpp'
    expected = generate()
    if sys.argv[1:] == ['--write']:
        output.write_bytes(expected.encode('utf-8'))
        print('WROTE:', output.name)
    elif sys.argv[1:]:
        raise SystemExit('Usage: generate_material_steps.py [--write]')
    elif output.read_text(encoding='utf-8') != expected:
        raise SystemExit('FAIL: material golden header differs from the exact-rational calculation')
    print('PASS: %d samples x 3 states; exact zero walls, exact div(eps_r,e E) and div H initially'
          % expected.count('\n    {'))
    print('LIMIT: deterministic exact-rational calculations of the MAT-01 lossy update, not physical validation')


if __name__ == '__main__':
    main()
