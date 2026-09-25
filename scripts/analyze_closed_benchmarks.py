"""MAT-02/MAT-03 independent physical analysis of closed-v1 raw artifacts (V04-V06).

Reads emitted metadata/CSV only; no solver operator is imported. The
predictions and fixed version-1 limits come from the MAT-01 specification
audit (check_material_benchmarks.py), which evaluates only closed-form
expressions. The V05/V06 reductions live in material_reductions.py. Every
check is recorded and all outputs are written before the nonzero exit for a
failed suite.

Python 3.9+, standard library. Usage:
  python scripts/analyze_closed_benchmarks.py --input ROOT --output DIR
ROOT contains the CLI suite directories ``cavity``, ``cavity-spectrum``, ``pec``,
``dielectric``, ``interface``, ``slab-cavity``, ``lossy`` and ``dissipation`` (any
subset with --suite) and an optional ``resources.json`` from
scripts/run_reference_benchmarks.py.
"""
import argparse
import csv
import json
import math
import platform
import sys
from pathlib import Path

from analyze_reference_benchmarks import check_resources
from check_material_benchmarks import (cavity_mode, cavity_lines, pulse_samples, spectral_peaks, project,
                                       recurrence_frequency, pec_marked, cyclic, V04_CAPS, V04_HALF_Q_CAP,
                                       V04_DISCRETE_LIMIT, V04_STRUCTURE_LIMIT, V04_BASE_CELLS, V04B_STEPS,
                                       V04B_SHORT_STEPS, V04B_SOURCE_INDEX, V04B_PROBE_INDEX, V04B_TAU, V04B_FCUT,
                                       V04B_STRENGTH_FLOOR, V04B_PEAK_BIN_LIMIT, V04B_HEIGHT_LIMIT, V04C_MARGIN,
                                       V04C_SOURCE_INSIDE, V04C_SOURCE_OUTSIDE, V04C_PROBES_INSIDE,
                                       V04C_PROBES_OUTSIDE, pulse_drive,
                                       V04C_DRIVE_LIMIT, V04C_EXCITATION_FLOOR, V04C_INVARIANT_LIMIT)
from check_reference_runs import read_json, C0, MU0, EPS0, ETA0, NAMES
import material_reductions as mr

SCHEMA = "closed-v1-raw-1"
AMPLITUDE = 1.0
ORDER_RANGE = (1.8, 2.2)
EQUIVALENCE_LIMIT = 1e-12
GROWTH_FACTOR = 1.5
GROWTH_WINDOW = 4096
# V04-B growth rule, version 1.1 (MAT-02): a component whose post-pulse window
# maximum is below NULL_FLOOR times the largest window maximum of its family
# is analytically null (Hz for the z-directed source) and must stay below that
# floor; the 1.5 factor applies to the other components. Version 1 had no floor
# and failed on roundoff-level Hz (recorded in the MAT-02 evidence).
NULL_FLOOR = 1e-9
MODES = ((1, 1), (2, 1), (1, 2))
AXES = "xyz"
V04C_BOX = [[V04C_MARGIN, V04C_MARGIN + c] for c in V04_BASE_CELLS]
REGIONS = ("interior", "surface", "exterior")
MATERIAL_SUITES = ("dielectric", "interface", "slab-cavity", "lossy", "dissipation")
# The emitted initial-condition descriptions, checked against the MAT-01
# convention so that a run can be reproduced from its own metadata. Revision
# 1.3 (MAT-02 finding R2) corrected the mode sign: the description printed the
# amplitude `H_s=-C E_s/(mu0 Omega)` where the emitted field is its value at
# -dt/2, `H^(-1/2)=-H_s sin(omega_d dt/2)`. The initializer was always positive.
# The historical string is accepted only for the exact source snapshot that
# emitted it, so the retained V04 raw evidence stays auditable while any other
# description fails.
MODE_INITIALIZATION = ("exact discrete standing mode: E_a=A sin(k_b r_b) sin(k_c r_c) at t=0; "
                       "H=+(C E_s) sin(omega_d dt/2)/(mu0 Omega) at -dt/2 by permutation curl")
SOURCE_INITIALIZATION = "zero fields"
HISTORICAL_MODE_INITIALIZATION = ("exact discrete standing mode: E_a=A sin(k_b r_b) sin(k_c r_c) at t=0; "
                                  "H=-C E_s/(mu0 Omega) sin(omega_d dt/2) at -dt/2 by permutation curl")
HISTORICAL_SNAPSHOT = "f02fbe47c49ba3067e23051e3e10bc22456f1bfd522c5fd767ae20872e4bf61e"
# MAT-03 material kinds and their pinned initial-condition and source descriptions.
MATERIAL_KINDS = ("wave", "sheet", "slab", "modular")
WAVE_INITIALIZATION = {
    False: ("FND-04 compact potentials, discrete eigenwave: E_b=A cos(k r_a) at t=0; H_c=s abs(h) cos(k r_a+phi) "
            "at -dt/2 with h=(1/eta) z^(-1/2), phi=-arg(h)=omega_d dt/2"),
    True: ("FND-04 compact potentials, exact lossy eigenwave: E_b=A cos(k r_a) at t=0; H_c=s abs(h) cos(k r_a+phi) "
           "at -dt/2 with h=hhat z^(-1/2), hhat/A=(i dt K/mu0)/(z^(1/2)-z^(-1/2)), phi=-arg(h)")}
MATERIAL_INITIALIZATION = {
    "sheet": "zero fields",
    "slab": ("exact discrete slab eigenvector: E_b=A e[i_a] sin(pi i_c/N_c) at t=0; "
             "H=+(C E_s) sin(omega_d dt/2)/(mu0 Omega) at -dt/2 by permutation curl"),
    "modular": "FND-04 v1 normalized modular P curl"}
SHEET_SOURCE = ("J_b=J0 sin(pi i_c/N_c) g_n on every E_b edge of the plane i_src, J0=1 A/m^2, "
                "g_n=exp(-(((n+1/2) dt-t0)/tau)^2/2) cos(2 pi f0 ((n+1/2) dt-t0)), tau=1/(2 pi 0.15 f0), t0=4 tau, every step")
COEFFICIENT_LIMIT = 1e-15


def finite(value):
    return isinstance(value, float) and math.isfinite(value)


def initialization_accepted(meta):
    """True when the emitted initial-condition description is the specified one.

    The one historical mode description (the revision 1.3 sign typo) is accepted
    only together with the source snapshot that emitted it.
    """
    description = meta["initialization"]
    if meta["kind"] in MATERIAL_KINDS:
        expected = (WAVE_INITIALIZATION[meta["sigma_S_per_m"] != 0] if meta["kind"] == "wave"
                    else MATERIAL_INITIALIZATION[meta["kind"]])
        return description == expected
    if description == (MODE_INITIALIZATION if meta["kind"] == "mode" else SOURCE_INITIALIZATION):
        return True
    return (meta["kind"] == "mode" and description == HISTORICAL_MODE_INITIALIZATION
            and meta["source_snapshot_sha256"] == HISTORICAL_SNAPSHOT)


def has_failure(metrics, text):
    return any(text in failure for failure in metrics["failures"])


def expected_cavity_names():
    names = ["cavity-%s-m%d%d-s%d" % (AXES[a], nb, nc, s) for a in range(3) for nb, nc in MODES for s in (1, 2, 4)]
    return names + ["cavity-%s-m11-s1-q50" % AXES[a] for a in range(3)]


def expected_pec_names():
    return ["pec-c1-%s" % AXES[a] for a in range(3)] + ["pec-c2-inside", "pec-c3-outside"]


def parse_cavity_name(name):
    """cavity-<axis>-m<nb><nc>-s<s>[-q50] or pec-c1-<axis>."""
    parts = name.split("-")
    if len(parts) == 3 and parts[0] == "pec" and parts[1] == "c1" and parts[2] in AXES:
        return {"a": AXES.index(parts[2]), "nb": 1, "nc": 1, "s": 1, "q": 0.99, "pad": V04C_MARGIN}
    if len(parts) < 4 or parts[0] != "cavity" or parts[1] not in AXES:
        return None
    if not (parts[2].startswith("m") and len(parts[2]) == 3 and parts[3].startswith("s")):
        return None
    try:
        nb, nc, s = int(parts[2][1]), int(parts[2][2]), int(parts[3][1:])
    except ValueError:
        return None
    if (nb, nc) not in MODES or s not in (1, 2, 4):
        return None
    q = 0.99
    if len(parts) == 5:
        if parts[4] != "q50" or s != 1 or (nb, nc) != (1, 1):
            return None
        q = 0.5
    elif len(parts) != 4:
        return None
    return {"a": AXES.index(parts[1]), "nb": nb, "nc": nc, "s": s, "q": q, "pad": 0}


def closure_counts(cells):
    """Tangential outer-face E samples per component (independent formula)."""
    out = []
    for a in range(3):
        extents = [cells[t] + (0 if t == a else 1) for t in range(3)]
        interior = cells[a]
        for t in range(3):
            if t != a:
                interior *= cells[t] - 1
        out.append(math.prod(extents) - interior)
    return out


def shell_counts(cells, box):
    """Independent enumeration of the shell edges beyond the outer closure."""
    counts = [0, 0, 0]
    for a in range(3):
        extents = [cells[t] + (0 if t == a else 1) for t in range(3)]
        for i in range(extents[0]):
            for j in range(extents[1]):
                for k in range(extents[2]):
                    index = (i, j, k)
                    wall = any(index[t] in (0, cells[t]) for t in range(3) if t != a)
                    if not wall and pec_marked(a, index, box, True):
                        counts[a] += 1
    return counts


def probe_coverage(meta, per_state):
    """Revision 1.4: the probe record must be complete, not merely uniform.

    ``per_state`` maps each state to the set of `(component id, index)` keys
    recorded for it. Counting rows per state, as revisions 1–1.3 did, accepts a
    prescribed probe that is absent from *every* state, because the count stays
    uniform; the reductions then read the missing samples as zero. Every state
    must therefore record the same keys, and a source case must record exactly
    the `Ez` edges its own metadata prescribes.
    """
    if sorted(per_state) != list(range(meta["steps"] + 1)):
        return "probe states"
    recorded = {frozenset(keys) for keys in per_state.values()}
    if len(recorded) != 1:
        return "probe keys differ between states"
    keys = next(iter(recorded))
    if not keys:
        return "no probe samples"
    if meta["kind"] == "source":
        prescribed = frozenset((NAMES.index("Ez"), tuple(index)) for index in meta["probe_indices"])
        if keys != prescribed:
            return "recorded probes differ from the prescribed indices"
    return None


def update_edges(cells):
    """E samples per component in the FND-03 update ranges."""
    return [cells[a] * math.prod(cells[t] - 1 for t in range(3) if t != a) for a in range(3)]


def expected_materials(meta):
    """Independent material classes of a case from its kind and fixed rule.

    Returns ({(eps_r, sigma): cell count}, {(eps_r_e, sigma_e): edge count}).
    A uniform map has one class; the V05-B/C plane at cell ``i_int`` along the
    first role axis gives vacuum, the two-medium mean and the loaded medium,
    counted in closed form per component (E_a by cell, E_b/E_c by a-node).
    """
    cells = meta["cells"]
    total = math.prod(cells)
    edges = update_edges(cells)
    kind = meta["kind"]
    if kind in ("mode", "source"):
        return {(1.0, 0.0): total}, {(1.0, 0.0): sum(edges)}
    eps, sigma = float(meta["eps_r"]), float(meta["sigma_S_per_m"])
    if kind in ("wave", "modular"):
        return {(eps, sigma): total}, {(eps, sigma): sum(edges)}
    a, i_int = meta["roles"][0], meta["i_int"]
    n_a = cells[a]
    per_layer = total // n_a
    vacuum = loaded = mean = 0
    for e in range(3):
        if e == a:
            transverse = math.prod(cells[t] - 1 for t in range(3) if t != a)
            vacuum += i_int * transverse
            loaded += (n_a - i_int) * transverse
        else:
            t = 3 - a - e
            per_node = cells[e] * (cells[t] - 1)
            vacuum += (i_int - 1) * per_node
            mean += per_node
            loaded += (n_a - 1 - i_int) * per_node
    return ({(1.0, 0.0): i_int * per_layer, (eps, sigma): (n_a - i_int) * per_layer},
            {(1.0, 0.0): vacuum, ((1.0 + eps) / 2, 0.0): mean, (eps, sigma): loaded})


def same_class(key, entry):
    """An emitted entry belongs to an expected (eps_r_e, sigma_e) class: eps_r
    exactly (sums of 1, 4 and 2.25 are exact), sigma within 1e-15 relative."""
    if entry["eps_r"] != key[0]:
        return False
    if key[1] == 0:
        return entry["sigma_S_per_m"] == 0
    return abs(entry["sigma_S_per_m"] / key[1] - 1) <= COEFFICIENT_LIMIT


def coefficient_audit(meta):
    """MAT-03: the emitted material summary and solver coefficient table against
    the independent classes and the MAT-01 formulas. Returns an error or None."""
    material = meta["kind"] in MATERIAL_KINDS
    if "coefficients" not in meta:
        return "missing coefficient table" if material else None
    cell_classes, edge_classes = expected_materials(meta)
    summary = meta.get("materials", {})
    recorded = {(float(c["eps_r"]), float(c["sigma_S_per_m"])): c["count"] for c in summary.get("cells", [])}
    if recorded != cell_classes:
        return "material map summary %s differs from the fixed rule %s" % (recorded, cell_classes)
    extents = [[meta["cells"][a] + int(a != id) for a in range(3)] for id in range(3)]
    e_total = sum(math.prod(shape) for shape in extents)
    if summary.get("map_bytes") != (16 * math.prod(meta["cells"]) if material else 0):
        return "material map bytes"
    table = meta["coefficients"]
    entries = table["entries"]
    if table["index_bytes"] != 4 * e_total or not entries or table["table_bytes"] % len(entries) \
            or table["table_bytes"] // len(entries) < 40:
        return "coefficient storage bytes"
    if len(entries) != len(edge_classes):
        return "coefficient table has %d entries, expected %d" % (len(entries), len(edge_classes))
    dt = meta["dt_s"]
    matched = set()
    for entry in entries:
        key = next((k for k in edge_classes if same_class(k, entry)), None)
        if key is None or key in matched:
            return "coefficient entry (%r, %r) is not an expected edge class" % (entry["eps_r"], entry["sigma_S_per_m"])
        matched.add(key)
        if entry["edges"] != edge_classes[key]:
            return "entry (%r, %r) covers %d edges, expected %d" % (key + (entry["edges"], edge_classes[key]))
        eps = entry["eps_r"] * EPS0
        x = entry["sigma_S_per_m"] * dt / (2 * eps)
        ca, cb = (1 - x) / (1 + x), dt / eps / (1 + x)
        if key == (1.0, 0.0):
            if not (entry["x"] == 0 and entry["Ca"] == 1 and entry["Cb"] == dt / EPS0):
                return "vacuum entry is not Ca=1, Cb=dt/epsilon0 exactly"
        elif not (abs(entry["x"] - x) <= COEFFICIENT_LIMIT * abs(x) and abs(entry["Ca"] - ca) <= COEFFICIENT_LIMIT * max(abs(ca), 1)
                  and abs(entry["Cb"] - cb) <= COEFFICIENT_LIMIT * cb):
            return "entry (%r, %r) coefficients differ from the MAT-01 formula" % key
        if not (math.isfinite(entry["Ca"]) and entry["Cb"] > 0):
            return "entry coefficients are not finite with Cb > 0"
    return None


def load_case(directory):
    meta = read_json(directory / "metadata.json")
    with (directory / "probes.csv").open(newline="") as handle:
        probes = list(csv.DictReader(handle))
    with (directory / "diagnostics.csv").open(newline="") as handle:
        diagnostics = list(csv.DictReader(handle))
    return meta, probes, diagnostics


def audit_closed(root, suite):
    """Structural audit of a closed-v1 suite directory; returns case directories."""
    marker = read_json(root / "COMPLETE.json")
    if marker["schema"] != SCHEMA or marker["physical_acceptance"] != "not evaluated" or marker["suite"] != suite:
        raise ValueError("completion marker contract")
    directories = sorted(p for p in root.iterdir() if p.is_dir())
    if len(directories) != marker["cases"]:
        raise ValueError("incomplete suite")
    for directory in directories:
        meta = read_json(directory / "metadata.json")
        config = read_json(directory / "configuration.json")
        if config["case_status"] != "incomplete" or config["fixture_checks_status"] != "pending":
            raise ValueError("provisional configuration status")
        for key in ("case", "suite", "kind", "source_snapshot_sha256", "cells", "spacing_m", "dt_s", "q", "steps",
                    "pec_primitives", "masked_edges", "source", "initialization"):
            if config[key] != meta[key]:
                raise ValueError("retained configuration mismatch: " + key)
        if meta["case"] != directory.name or meta["schema"] != SCHEMA or (suite != "smoke" and meta["suite"] != suite):
            raise ValueError("metadata identity")
        if meta["case_status"] != "raw_complete" or meta["fixture_checks_status"] != "passed":
            raise ValueError("incomplete case metadata")
        if meta["kind"] not in ("mode", "source") + MATERIAL_KINDS or not initialization_accepted(meta):
            raise ValueError("initial condition description")
        material = meta["kind"] in MATERIAL_KINDS
        if material and meta["source"] != (SHEET_SOURCE if meta["kind"] == "sheet" else "J=0"):
            raise ValueError("source description")
        if len(meta["source_snapshot_sha256"]) != 64:
            raise ValueError("source fingerprint")
        if not (meta["c0"] == C0 and meta["mu0"] == MU0 and meta["epsilon0"] == EPS0 and meta["eta0"] == ETA0):
            raise ValueError("pinned constants")
        cells, spacing, dt, steps = meta["cells"], meta["spacing_m"], meta["dt_s"], meta["steps"]
        expected_dt = meta["q"] / (C0 * math.sqrt(sum(1 / d**2 for d in spacing)))
        if abs(dt / expected_dt - 1) > 5e-15:
            raise ValueError("independent CFL metadata")
        extents = [[cells[a] + int(a != id) if id < 3 else cells[a] + int(a == id - 3) for a in range(3)]
                   for id in range(6)]
        if meta["extents"] != extents:
            raise ValueError("six extents")
        payload = 8 * sum(math.prod(shape) for shape in extents)
        mask_bytes = sum(math.prod(extents[id]) for id in range(3))
        floor = 2 * payload + mask_bytes
        if "coefficients" in meta:
            floor += meta["coefficients"]["index_bytes"] + meta["coefficients"]["table_bytes"]
        if material:
            if not (meta["map_bytes"] == 16 * math.prod(cells) and meta["coefficient_index_bytes"] == 4 * mask_bytes
                    and meta["diagnostic_bytes"] == (8 * mask_bytes if meta["diagnostics"] else 0)):
                raise ValueError("material storage bytes")
            floor += meta["map_bytes"] + meta["diagnostic_bytes"]
        if not (meta["field_bytes"] == payload and meta["mask_bytes"] == mask_bytes
                and floor <= meta["working_bytes_budgeted"] <= 2**31):
            raise ValueError("transient memory budget")
        if not (meta["fixture_max_divergence_error"] <= 1e-11 and meta["fixture_max_eigen_error"] <= 1e-11):
            raise ValueError("fixture report")
        # Material fixtures always report the plateau check; V04 metadata predates it.
        if material and not meta["fixture_max_plateau_error"] <= 1e-11:
            raise ValueError("fixture report")
        error = coefficient_audit(meta)
        if error is not None:
            raise ValueError(error)
        if meta["closure_edges"] != closure_counts(cells):
            raise ValueError("closure edge counts")
        primitives = meta["pec_primitives"]
        if not primitives:
            if meta["masked_edges"] != meta["closure_edges"]:
                raise ValueError("closure-only mask counts")
        elif len(primitives) == 1 and primitives[0]["shape"] == "pec_shell":
            box = [[lo, hi] for lo, hi in zip(primitives[0]["low"], primitives[0]["high"])]
            extra = shell_counts(cells, box)
            if [m - c for m, c in zip(meta["masked_edges"], meta["closure_edges"])] != extra:
                raise ValueError("shell edge counts differ from the independent enumeration")
        else:
            raise ValueError("unexpected primitive list")
        with (directory / "probes.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        seen = set()
        per_state = {}
        for row in rows:
            n, id = int(row["state"]), NAMES.index(row["component"])
            index = tuple(int(row[key]) for key in ("i", "j", "k"))
            expected_time = (n - (0 if id < 3 else .5)) * dt
            value = float(row["value"])
            if not (math.isfinite(value) and abs(float(row["time_s"]) - expected_time) <= 5e-15 * max(dt, abs(expected_time))):
                raise ValueError("native time/value")
            key = n, id, index
            if not (0 <= n <= steps and key not in seen):
                raise ValueError("unique state/sample")
            seen.add(key)
            per_state.setdefault(n, set()).add((id, index))
            for a, name in enumerate(("x_m", "y_m", "z_m")):
                half = .5 if (a == id if id < 3 else a != id - 3) else 0
                expected_position = (index[a] + half) * spacing[a]
                position = float(row[name])
                if not (0 <= index[a] < extents[id][a] and
                        abs(position - expected_position) <= 5e-15 * max(spacing[a], abs(expected_position))):
                    raise ValueError("native location")
        error = probe_coverage(meta, per_state)
        if error is not None:
            raise ValueError(error)
        with (directory / "diagnostics.csv").open(newline="") as handle:
            energy = list(csv.DictReader(handle))
        if len(energy) != (steps + 1 if meta["diagnostics"] else 0):
            raise ValueError("diagnostic rows")
        if material and energy and "D_J" not in energy[0]:
            raise ValueError("dissipation column")
        for n, row in enumerate(energy):
            values = {k: float(v) for k, v in row.items()}
            if int(values["state"]) != n or not all(math.isfinite(v) for v in values.values()):
                raise ValueError("finite diagnostic state")
            if values["e_time_s"] != n * dt or values["h_time_s"] != (n - .5) * dt:
                raise ValueError("diagnostic native time")
            if values["U_J"] < 0 or any(values["max_" + name] < 0 for name in NAMES):
                raise ValueError("positive norm/maxima")
            if meta["region"]:
                for name in NAMES:
                    regional = max(values[region + "_" + name] for region in REGIONS)
                    if not math.isclose(regional, values["max_" + name], rel_tol=0, abs_tol=0):
                        raise ValueError("region maxima do not partition the component maxima")
    return directories


def line_specification(meta, spec):
    """Prescribed V04-A native lines in storage indices (role axes cyclic from a)."""
    a, b, c = cyclic(spec["a"])
    origin, cavity = meta["origin"], meta["cavity_cells"]
    base = [0, 0, 0]
    base[a] = origin[a] + cavity[a] // 2
    base[c] = origin[c] + cavity[c] // 4
    e_line = []
    hc_line = []
    for j in range(cavity[b] + 1):
        index = list(base)
        index[b] = origin[b] + j
        e_line.append(tuple(index))
        if j < cavity[b]:
            hc_line.append(tuple(index))
    hb_line = []
    index = list(base)
    index[b] = origin[b] + cavity[b] // 4
    for k in range(cavity[c]):
        index[c] = origin[c] + k
        hb_line.append(tuple(index))
    return {a: sorted(e_line), c + 3: sorted(hc_line), b + 3: sorted(hb_line)}


def analyze_cavity(meta, probes, fixed_suite=True):
    """V04-A reductions for one exact-mode case; returns (metrics, trace rows)."""
    name = meta["case"]
    spec = parse_cavity_name(name)
    failures = []
    metrics = {"case": name, "steps": meta["steps"], "dt_s": meta["dt_s"], "q": meta["q"],
               "elapsed_seconds": meta.get("elapsed_seconds")}
    if spec is None:
        metrics.update({"failures": ["unknown case name"], "status": "fail"})
        return metrics, []
    a, b, c = cyclic(spec["a"])
    mode = cavity_mode(spec["s"], spec["a"], spec["nb"], spec["nc"], spec["q"])
    dt, steps = meta["dt_s"], meta["steps"]
    pad = spec["pad"]
    expected_cells = [n + 2 * pad for n in mode["cells"]]
    metrics.update({"a": spec["a"], "mode": [spec["nb"], spec["nc"]], "s": spec["s"],
                    "continuum_cap": V04_HALF_Q_CAP if spec["q"] == 0.5 else V04_CAPS[spec["s"]],
                    "omega_c": mode["omega_c"], "omega_d": mode["omega_d"], "predicted_continuum_error": mode["error"]})
    if meta["cells"] != expected_cells:
        failures.append("cells %s differ from v1 %s" % (meta["cells"], expected_cells))
    if any(abs(x / y - 1) > 5e-15 for x, y in zip(meta["spacing_m"], mode["spacing"])):
        failures.append("spacing differs from v1 definition")
    if abs(meta["q"] / spec["q"] - 1) > 5e-15 or abs(dt / mode["dt"] - 1) > 5e-15:
        failures.append("q/dt differ from v1 definition")
    if fixed_suite and steps != mode["steps"]:
        failures.append("steps %d differ from v1 %d" % (steps, mode["steps"]))
    if (meta["a"] != spec["a"] or meta["mode"] != [spec["nb"], spec["nc"]] or meta["s"] != spec["s"]
            or meta["origin"] != [pad] * 3 or meta["cavity_cells"] != list(mode["cells"]) or meta["kind"] != "mode"):
        failures.append("case flags inconsistent with name")
    if steps < 2:
        failures.append("too few evolved states for the recurrence")
    db, dc = mode["spacing"][b], mode["spacing"][c]
    kb, kc, big_kb, big_kc = mode["kb"], mode["kc"], mode["Kb"], mode["Kc"]
    nb_cells, nc_cells = mode["cells"][b], mode["cells"][c]
    fac_c = math.sin(kc * (nc_cells // 4) * dc)
    fac_b = math.sin(kb * (nb_cells // 4) * db)
    shapes = {a: [math.sin(kb * j * db) * fac_c for j in range(nb_cells + 1)],
              c + 3: [math.cos(kb * (j + 0.5) * db) * fac_c for j in range(nb_cells)],
              b + 3: [math.cos(kc * (k + 0.5) * dc) * fac_b for k in range(nc_cells)]}
    prescribed = line_specification(meta, spec)
    lines = {}
    for row in probes:
        n, id = int(row["state"]), NAMES.index(row["component"])
        index = tuple(int(row[key]) for key in ("i", "j", "k"))
        lines.setdefault((n, id), []).append((index, float(row["value"]), float(row["time_s"])))
    amplitudes = {id: [] for id in shapes}
    residual = {id: 0.0 for id in shapes}
    complete = True
    for n in range(steps + 1):
        for id, indices in prescribed.items():
            samples = lines.get((n, id), [])
            if len(samples) != len(indices):
                failures.append("state %d %s has %d native samples, expected %d" % (n, NAMES[id], len(samples), len(indices)))
                complete = False
                continue
            samples.sort()
            if [s[0] for s in samples] != indices:
                failures.append("state %d %s samples are not the prescribed native line" % (n, NAMES[id]))
                complete = False
                continue
            if len({t for _, _, t in samples}) != 1:
                failures.append("state %d %s mixes sample times" % (n, NAMES[id]))
            try:
                amplitude, fit_residual = project([v for _, v, _ in samples], shapes[id])
            except RuntimeError as error:
                failures.append("state %d %s projection rejected: %s" % (n, NAMES[id], error))
                complete = False
                continue
            amplitudes[id].append(amplitude)
            residual[id] = max(residual[id], fit_residual)
        if any(len(lines.get((n, id), [])) for id in range(6) if id not in prescribed):
            failures.append("state %d contains samples outside the three prescribed lines" % n)
    trace = []
    if complete and steps >= 2:
        try:
            omega_m = recurrence_frequency(amplitudes[a], dt)
        except RuntimeError as error:
            failures.append("recurrence frequency rejected: %s" % error)
            omega_m = None
    else:
        omega_m = None
    metrics["omega_measured"] = omega_m
    if omega_m is not None:
        big_omega = 2 / dt * math.sin(omega_m * dt / 2)
        hb_ref, hc_ref = -big_kc / (MU0 * big_omega), big_kb / (MU0 * big_omega)
        amp_err = h_err = 0.0
        for n in range(steps + 1):
            te, th = n * dt, (n - 0.5) * dt
            a_n, b_n, c_n = amplitudes[a][n], amplitudes[b + 3][n], amplitudes[c + 3][n]
            amp_err = max(amp_err, abs(a_n / AMPLITUDE - math.cos(omega_m * te)))
            h_err = max(h_err, abs(b_n / hb_ref - math.sin(omega_m * th)), abs(c_n / hc_ref - math.sin(omega_m * th)))
            trace.append({"case": name, "state": n, "e_time_s": te, "h_time_s": th, "a_n": a_n, "b_n": b_n, "c_n": c_n,
                          "cos_reference": math.cos(omega_m * te), "sin_reference": math.sin(omega_m * th)})
        worst_residual = max(residual[a] / AMPLITUDE, residual[b + 3] / abs(hb_ref), residual[c + 3] / abs(hc_ref))
        metrics.update({"continuum_error": abs(omega_m / mode["omega_c"] - 1),
                        "discrete_error": abs(omega_m / mode["omega_d"] - 1),
                        "max_amplitude_error": amp_err, "max_magnetic_error": h_err,
                        "max_normalized_residual": worst_residual,
                        "hb_reference": hb_ref, "hc_reference": hc_ref})
        if metrics["continuum_error"] > metrics["continuum_cap"]:
            failures.append("continuum resonance error exceeds cap")
        if metrics["discrete_error"] > V04_DISCRETE_LIMIT:
            failures.append("discrete frequency error exceeds limit")
        if amp_err > V04_STRUCTURE_LIMIT:
            failures.append("modal amplitude error exceeds limit")
        if h_err > V04_STRUCTURE_LIMIT:
            failures.append("magnetic relation error exceeds limit")
        if worst_residual > V04_STRUCTURE_LIMIT:
            failures.append("projection residual exceeds limit")
    else:
        metrics.update({"continuum_error": None, "discrete_error": None, "max_amplitude_error": None,
                        "max_magnetic_error": None, "max_normalized_residual": None})
        if complete:
            failures.append("frequency not measured")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace


def refinement(errors):
    """errors: {1: e, 2: e, 4: e} continuum errors of one polarization/mode."""
    failures = []
    sequence = [errors.get(s) for s in (1, 2, 4)]
    if any(e is None or not finite(e) or e <= 0 for e in sequence):
        failures.append("missing/nonpositive continuum error")
        orders = [None, None]
    else:
        if not sequence[0] > sequence[1] > sequence[2]:
            failures.append("continuum errors not strictly decreasing")
        orders = [math.log2(sequence[0] / sequence[1]), math.log2(sequence[1] / sequence[2])]
        if any(not ORDER_RANGE[0] <= o <= ORDER_RANGE[1] for o in orders):
            failures.append("observed order outside [1.8,2.2]")
    return {"errors": sequence, "orders": orders, "failures": failures, "status": "pass" if not failures else "fail"}


def spectrum_reduction(series, dt, lines, steps):
    """One V04-B identification on ``steps`` states of the probe series."""
    below = [line for line in lines if line["omega_d"] / 2 / math.pi < V04B_FCUT]
    s_max = max(line["strength"] for line in below)
    required = [line for line in below if line["strength"] >= V04B_STRENGTH_FLOOR * s_max]
    visible = [line for line in below if line["strength"] >= 0.01 * s_max]
    failures = []
    result = {"states": steps, "bin_hz": 1 / (steps * dt), "required_lines": len(required), "visible_lines": len(visible)}
    if len(series) < steps:
        failures.append("record has %d states, fewer than %d" % (len(series), steps))
        result.update({"failures": failures, "status": "fail", "lines": []})
        return result, []
    bin_hz, peaks = spectral_peaks(series[:steps], dt)
    if not peaks:
        failures.append("no spectral peak found")
        result.update({"failures": failures, "status": "fail", "lines": []})
        return result, []
    top = max(h for _, h in peaks)
    rows = []
    worst_bin = worst_height = worst_continuum_margin = 0.0
    for line in required:
        f_d, f_c = line["omega_d"] / 2 / math.pi, line["omega_c"] / 2 / math.pi
        nearest = min(peaks, key=lambda p: abs(p[0] - f_d))
        offset = abs(nearest[0] - f_d) / bin_hz
        height = abs(nearest[1] / top - line["strength"] / s_max)
        dispersion = abs(line["omega_d"] / line["omega_c"] - 1)
        continuum = abs(nearest[0] / f_c - 1)
        continuum_limit = dispersion + V04B_PEAK_BIN_LIMIT * bin_hz / f_c
        worst_bin, worst_height = max(worst_bin, offset), max(worst_height, height)
        worst_continuum_margin = max(worst_continuum_margin, continuum - continuum_limit)
        rows.append({"states": steps, "mode": "%d,%d,%d" % line["mode"], "f_d_hz": f_d, "f_c_hz": f_c,
                     "f_peak_hz": nearest[0], "offset_bins": offset, "predicted_strength": line["strength"] / s_max,
                     "measured_height": nearest[1] / top, "height_error": height, "dispersion": dispersion,
                     "continuum_error": continuum, "continuum_limit": continuum_limit,
                     "status": "pass" if offset <= V04B_PEAK_BIN_LIMIT and height <= V04B_HEIGHT_LIMIT
                     and continuum <= continuum_limit else "fail"})
    spurious = []
    for f_peak, height in peaks:
        if f_peak < V04B_FCUT and height >= V04B_STRENGTH_FLOOR * top:
            if min(abs(f_peak - line["omega_d"] / 2 / math.pi) for line in visible) > V04B_PEAK_BIN_LIMIT * bin_hz:
                spurious.append({"f_hz": f_peak, "height": height / top})
    if worst_bin > V04B_PEAK_BIN_LIMIT:
        failures.append("a required line has no peak within 0.25 bin")
    if worst_height > V04B_HEIGHT_LIMIT:
        failures.append("relative peak height differs from the predicted strength by more than 0.15")
    if worst_continuum_margin > 0:
        failures.append("continuum resonance of a required peak exceeds dispersion plus resolution")
    if spurious:
        failures.append("%d spurious peak(s) below the cutoff" % len(spurious))
    result.update({"max_offset_bins": worst_bin, "max_height_error": worst_height,
                   "max_continuum_margin": worst_continuum_margin, "spurious_peaks": spurious,
                   "peaks_below_cutoff": [[f, h / top] for f, h in peaks if f < V04B_FCUT and h >= 0.01 * top],
                   "failures": failures, "status": "pass" if not failures else "fail"})
    return result, rows


def analyze_spectrum(meta, probes, diagnostics, fixed_suite=True):
    """V04-B identification on the full and truncated records; returns (metrics, peak rows)."""
    failures = []
    dt, steps = meta["dt_s"], meta["steps"]
    lines, dt_expected, samples, source, probe = cavity_lines(1)
    metrics = {"case": meta["case"], "steps": steps, "dt_s": dt, "q": meta["q"], "elapsed_seconds": meta.get("elapsed_seconds"),
               "pulse_samples": len(samples), "source_index": list(source), "probe_index": list(probe)}
    if meta["cells"] != list(V04_BASE_CELLS) or any(abs(x / y - 1) > 5e-15 for x, y in zip(meta["spacing_m"], (0.01, 0.015, 0.02))):
        failures.append("grid differs from the v1 cavity")
    if abs(meta["q"] / 0.99 - 1) > 5e-15 or abs(dt / dt_expected - 1) > 5e-15:
        failures.append("q/dt differ from v1 definition")
    if fixed_suite and steps != V04B_STEPS:
        failures.append("steps %d differ from v1 %d" % (steps, V04B_STEPS))
    if (meta["kind"] != "source" or meta["source_index"] != list(V04B_SOURCE_INDEX) or meta["pec_primitives"]
            or meta["probe_indices"] != [list(V04B_PROBE_INDEX)] or abs(meta["tau_s"] / V04B_TAU - 1) > 5e-15
            or meta["pulse_samples"] != len(samples) or meta["pulse_half_samples"] != (len(samples) - 1) // 2):
        failures.append("source/probe/pulse metadata differ from v1")
    series = {}
    for row in probes:
        if row["component"] != "Ez" or tuple(int(row[k]) for k in "ijk") != tuple(V04B_PROBE_INDEX):
            failures.append("unexpected probe sample %s %s" % (row["component"], [row[k] for k in "ijk"]))
            break
        series[int(row["state"])] = float(row["value"])
    if sorted(series) != list(range(steps + 1)):
        failures.append("probe series is not the complete state range")
    ordered = [series.get(n, math.nan) for n in range(steps + 1)]
    if series.get(0, math.nan) != 0:
        failures.append("initial probe value is not zero")
    peaks_rows = []
    analyses = {}
    for record in (V04B_STEPS, V04B_SHORT_STEPS):
        if fixed_suite or len(ordered) >= record:
            result, rows = spectrum_reduction(ordered, dt, lines, record)
            analyses["full" if record == V04B_STEPS else "truncated"] = result
            peaks_rows.extend(rows)
            for failure in result["failures"]:
                failures.append("%d-state analysis: %s" % (record, failure))
    metrics["analyses"] = analyses
    # Field boundedness after the pulse from the per-state maxima.
    post = len(samples)
    rows = []
    for row in diagnostics:
        values = {k: float(v) for k, v in row.items()}
        rows.append(values)
    if len(rows) != steps + 1:
        failures.append("expected %d diagnostic states, found %d" % (steps + 1, len(rows)))
    nonfinite = next((n for n, r in enumerate(rows) if any(not math.isfinite(v) for v in r.values())), None)
    if nonfinite is not None:
        failures.append("nonfinite diagnostic at state %d" % nonfinite)
    growth = {}
    if rows and nonfinite is None:
        if rows[0]["U_J"] != 0 or rows[0]["Q_J"] != 0:
            failures.append("driven case does not start from zero fields")
        window = rows[post:post + GROWTH_WINDOW]
        later = rows[post + GROWTH_WINDOW:]
        window_max = {name: max((r["max_" + name] for r in window), default=0.0) for name in NAMES}
        family_max = {"E": max(window_max[n] for n in NAMES[:3]), "H": max(window_max[n] for n in NAMES[3:])}
        for name in NAMES:
            reference = window_max[name]
            worst = max((r["max_" + name] for r in later), default=0.0)
            floor = NULL_FLOOR * family_max[name[0]]
            null = reference <= floor
            growth[name] = {"window_max": reference, "later_max": worst, "floor": floor, "null_component": null,
                            "v1_ratio": None if reference == 0 else worst / reference}
            if null:
                if worst > floor:
                    failures.append("%s is a null component whose maxima exceed the floor after the window" % name)
            elif worst > GROWTH_FACTOR * reference:
                failures.append("%s maxima grow beyond 1.5 times their post-pulse window" % name)
        q_after = [r["Q_J"] for r in rows[post:]]
        if q_after and q_after[0] > 0:
            metrics["post_pulse_invariant_drift"] = max(abs(q - q_after[0]) / q_after[0] for q in q_after)
    metrics["growth"] = growth
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, peaks_rows


def region_checks(rows, zero_regions, finite_regions):
    """Exact-zero and finiteness checks of the per-state region maxima."""
    failures = []
    worst_zero = 0.0
    for n, row in enumerate(rows):
        for region in zero_regions:
            for name in NAMES:
                value = float(row[region + "_" + name])
                worst_zero = max(worst_zero, abs(value))
                if value != 0:
                    failures.append("%s %s nonzero at state %d" % (region, name, n))
                    break
            else:
                continue
            break
        for region in finite_regions:
            if any(not math.isfinite(float(row[region + "_" + name])) for name in NAMES):
                failures.append("%s nonfinite at state %d" % (region, n))
                break
    return worst_zero, failures


def excitation_checks(values, region, metrics, fixed_suite):
    """V04-C revision 1.2: the driven side must carry the pulse it was given.

    The references are the closed-form electric deposits of the fixed pulse on
    its own edge and the dissipationless invariant; none uses solver output.
    Finiteness alone cannot separate a shielded driven region from a dead one.

    Revision 1.3 (MAT-02 finding R1) names the component: the fixed source is
    `J_z` on an Ez edge, so the first deposit belongs to Ez alone. Sorting the
    three electric maxima, as revision 1.2 did, accepted an Ex or Ey deposit.
    """
    failures = []
    _, drive, largest, pulse_length = pulse_drive()
    metrics["drive_prediction"] = drive
    metrics["excitation_floor"] = V04C_EXCITATION_FLOOR * largest
    if len(values) < 2:
        return ["driven case has no state after the first update"]
    first = values[1]
    driven = first[region + "_Ez"]
    metrics["drive_first_state"] = driven
    metrics["drive_error"] = abs(driven / drive - 1)
    if metrics["drive_error"] > V04C_DRIVE_LIMIT:
        failures.append("first driven Ez sample %.17g differs from the closed-form deposit %.17g by %.3g"
                        % (driven, drive, metrics["drive_error"]))
    # Both the driven region and the whole domain: at state 1 only Ez has moved.
    moved = [name for name in NAMES
             if name != "Ez" and (first[region + "_" + name] != 0 or first["max_" + name] != 0)]
    if moved or first["max_Ez"] != driven:
        failures.append("the first update touched more than the driven Ez edge: %s"
                        % (", ".join(moved) if moved else "Ez outside the driven region"))
    peak = max(metrics["max_alive"][name] for name in NAMES[:3])
    metrics["excitation_peak"] = peak
    metrics["excitation_ratio"] = peak / largest
    if not fixed_suite:
        return failures                  # a smoke-length run has no post-pulse record
    if peak < metrics["excitation_floor"]:
        failures.append("driven region peak E %.3g is below the excitation floor %.3g"
                        % (peak, metrics["excitation_floor"]))
    after = [row["Q_J"] for row in values[pulse_length:]]
    if not after or after[0] <= 0:
        failures.append("the invariant Q is not positive after the pulse")
    else:
        drift = max(abs(q - after[0]) / after[0] for q in after)
        metrics["post_pulse_invariant"] = after[0]
        metrics["post_pulse_invariant_drift"] = drift
        if drift > V04C_INVARIANT_LIMIT:
            failures.append("the invariant Q drifts by %.3g after the pulse" % drift)
    return failures


def source_probe_checks(probes, source, indices, steps, metrics):
    """V04-C revision 1.3: the prescribed source edge itself, from the native record.

    Region maxima are unsigned and carry no location, so they cannot show which
    edge was driven. The C2/C3 configurations record the source edge among their
    Ez probes: the first E update of a zero state has no curl contribution, so
    that sample is exactly `-(dt/eps0) J0 g_0` (negative: the update subtracts
    the current), and every other prescribed probe is still zero.

    ``source`` and ``indices`` are the version-1 fixture's own edges (revision
    1.4), not the candidate artifact's declaration, so a run that records or
    declares fewer probes than the specification prescribes cannot define its
    own coverage.
    """
    failures = []
    _, drive, _, _ = pulse_drive()
    samples = {}
    for row in probes:
        if row["component"] != "Ez":
            failures.append("probe component %s is not the driven Ez" % row["component"])
            continue
        index = tuple(int(row[key]) for key in "ijk")
        if index not in indices:
            failures.append("probe %s is not a prescribed index" % (index,))
            continue
        key = int(row["state"]), index
        if key in samples:
            failures.append("probe %s has a duplicate state %d sample" % (index, key[0]))
        samples[key] = float(row["value"])
    # Revision 1.4: an absent sample is a missing measurement, never a zero.
    expected = (steps + 1) * len(indices)
    if len(samples) != expected:
        failures.append("the record holds %d prescribed probe samples, expected %d (%d probes over %d states)"
                        % (len(samples), expected, len(indices), steps + 1))
    if (1, source) not in samples:
        failures.append("the source edge has no state 1 sample")
    else:
        value = samples[1, source]
        metrics["source_probe_first_state"] = value
        metrics["source_probe_error"] = abs(value / (-drive) - 1)
        if metrics["source_probe_error"] > V04C_DRIVE_LIMIT:
            failures.append("the state 1 source sample %.17g differs from the signed closed-form deposit "
                            "%.17g by %.3g" % (value, -drive, metrics["source_probe_error"]))
    for index in indices:
        for state in (0, 1) if index != source else (0,):
            if (state, index) not in samples:
                failures.append("probe %s has no state %d sample" % (index, state))
            elif samples[state, index] != 0:
                failures.append("probe %s is not zero at state %d" % (index, state))
    return failures


def analyze_pec(meta, probes, diagnostics, reference=None, fixed_suite=True):
    """V04-C reductions; ``reference`` is the (meta, probes) of the matching cavity case for C1."""
    name = meta["case"]
    failures = []
    metrics = {"case": name, "steps": meta["steps"], "dt_s": meta["dt_s"], "elapsed_seconds": meta.get("elapsed_seconds")}
    expected_cells = [c + 2 * V04C_MARGIN for c in V04_BASE_CELLS]
    if meta["cells"] != expected_cells:
        failures.append("cells %s differ from v1 %s" % (meta["cells"], expected_cells))
    if any(abs(x / y - 1) > 5e-15 for x, y in zip(meta["spacing_m"], (0.01, 0.015, 0.02))):
        failures.append("spacing differs from v1 definition")
    if meta["pec_primitives"] != [{"shape": "pec_shell", "low": [V04C_MARGIN] * 3, "high": [m + c for m, c in zip([V04C_MARGIN] * 3, V04_BASE_CELLS)]}]:
        failures.append("primitive list is not the V04-C shell")
    extra = [m - c for m, c in zip(meta["masked_edges"], meta["closure_edges"])]
    metrics["shell_edges"] = extra
    if extra != [864, 1024, 1120]:
        failures.append("shell edge counts %s differ from 864/1024/1120" % extra)
    if not meta["region"] or not meta["diagnostics"]:
        failures.append("region maxima were not recorded")
    rows = diagnostics
    if len(rows) != meta["steps"] + 1:
        failures.append("expected %d diagnostic states, found %d" % (meta["steps"] + 1, len(rows)))
    if name.startswith("pec-c1"):
        cavity_metrics, trace = analyze_cavity(meta, probes, fixed_suite)
        metrics["cavity"] = cavity_metrics
        failures.extend("mode: " + f for f in cavity_metrics["failures"])
        worst_zero, region_failures = region_checks(rows, ("surface", "exterior"), ("interior",))
        failures.extend(region_failures)
        metrics["max_outside_sample"] = worst_zero
        if reference is None:
            failures.append("no cavity s=1 reference case available for the equivalence check")
        else:
            ref_meta, ref_probes = reference
            if ref_meta["steps"] != meta["steps"] or ref_meta["dt_s"] != meta["dt_s"]:
                failures.append("reference cavity case steps/dt differ")
            lookup = {}
            for row in ref_probes:
                lookup[(int(row["state"]), row["component"], tuple(int(row[k]) for k in "ijk"))] = float(row["value"])
            matched = bitwise = 0
            worst = 0.0
            for row in probes:
                key = (int(row["state"]), row["component"], tuple(int(row[k]) - V04C_MARGIN for k in "ijk"))
                if key not in lookup:
                    failures.append("sample %s has no cavity reference" % (key,))
                    break
                matched += 1
                scale = 1.0 if row["component"][0] == "E" else 1 / ETA0
                difference = abs(float(row["value"]) - lookup[key]) / scale
                bitwise += float(row["value"]) == lookup[key]
                worst = max(worst, difference)
            if matched != len(lookup) or not lookup:
                failures.append("matched %d of %d reference samples" % (matched, len(lookup)))
            if worst > EQUIVALENCE_LIMIT:
                failures.append("interior line differs from the V04-A case beyond 1e-12")
            metrics.update({"equivalence_matched": matched, "equivalence_bitwise": bitwise,
                            "equivalence_max_difference": worst, "equivalence_reference": ref_meta["case"]})
    else:
        inside = name == "pec-c2-inside"
        expected_source = list(V04C_SOURCE_INSIDE if inside else V04C_SOURCE_OUTSIDE)
        expected_probes = [tuple(index) for index in (V04C_PROBES_INSIDE if inside else V04C_PROBES_OUTSIDE)]
        if meta["kind"] != "source" or meta["source_index"] != expected_source:
            failures.append("source edge differs from v1")
        if sorted(tuple(index) for index in meta["probe_indices"]) != sorted(expected_probes):
            failures.append("probe indices %s differ from the v1 set %s"
                            % (meta["probe_indices"], [list(index) for index in expected_probes]))
        if fixed_suite and meta["steps"] != 4096:
            failures.append("steps %d differ from v1 4096" % meta["steps"])
        if abs(meta["dt_s"] / pulse_drive()[0] - 1) > 5e-15:
            failures.append("dt differs from the v1 cavity definition")
        zero = ("surface", "exterior") if inside else ("interior", "surface")
        alive = ("interior",) if inside else ("exterior",)
        worst_zero, region_failures = region_checks(rows, zero, alive)
        failures.extend(region_failures)
        metrics["max_silent_sample"] = worst_zero
        if rows:
            values = [{k: float(v) for k, v in r.items()} for r in rows]
            if any(not math.isfinite(v) for r in values for v in r.values()):
                failures.append("nonfinite diagnostic value")
            metrics["max_alive"] = {name_: max(r[alive[0] + "_" + name_] for r in values) for name_ in NAMES}
            if values[0]["U_J"] != 0 or values[0]["Q_J"] != 0:
                failures.append("driven case does not start from zero fields")
            failures.extend(excitation_checks(values, alive[0], metrics, fixed_suite))
        if any(not math.isfinite(float(row["value"])) for row in probes):
            failures.append("nonfinite probe sample")
        failures.extend(source_probe_checks(probes, tuple(expected_source), sorted(expected_probes),
                                            meta["steps"], metrics))
        trace = []
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace


def load_suite(root, suite, expected_names):
    result = {"suite": suite, "root": str(root), "cases": [], "failures": []}
    try:
        directories = audit_closed(root, suite)
    except Exception as error:  # retained as evidence; analysis continues on readable cases
        result["failures"].append("artifact audit: %s" % error)
        directories = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if sorted(d.name for d in directories) != sorted(expected_names):
        result["failures"].append("suite enumeration differs from the v1 configurations")
    return result, directories


def analyze_suite_cavity(root):
    result, directories = load_suite(root, "cavity", expected_cavity_names())
    result["refinement"] = []
    trace = []
    loaded = {}
    for directory in directories:
        try:
            meta, probes, _ = load_case(directory)
            metrics, rows = analyze_cavity(meta, probes)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail", "failures": ["unreadable: %s" % error]})
            continue
        loaded[meta["case"]] = (meta, probes)
        result["cases"].append(metrics)
        trace.extend(rows)
    by_name = {m["case"]: m for m in result["cases"]}
    for a in range(3):
        for nb, nc in MODES:
            errors = {s: by_name.get("cavity-%s-m%d%d-s%d" % (AXES[a], nb, nc, s), {}).get("continuum_error") for s in (1, 2, 4)}
            entry = refinement(errors)
            entry.update({"polarization": AXES[a], "mode": [nb, nc]})
            result["refinement"].append(entry)
    result["status"] = "pass" if not result["failures"] and all(
        item["status"] == "pass" for key in ("cases", "refinement") for item in result[key]) else "fail"
    return result, trace, loaded


def analyze_suite_spectrum(root):
    result, directories = load_suite(root, "cavity-spectrum", ["spectrum-s1"])
    peaks = []
    for directory in directories:
        try:
            meta, probes, diagnostics = load_case(directory)
            metrics, rows = analyze_spectrum(meta, probes, diagnostics)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail", "failures": ["unreadable: %s" % error]})
            continue
        result["cases"].append(metrics)
        peaks.extend(rows)
    result["status"] = "pass" if not result["failures"] and all(c["status"] == "pass" for c in result["cases"]) else "fail"
    return result, peaks


def analyze_suite_pec(root, cavity_cases):
    result, directories = load_suite(root, "pec", expected_pec_names())
    trace = []
    for directory in directories:
        try:
            meta, probes, diagnostics = load_case(directory)
            reference = cavity_cases.get("cavity-%s-m11-s1" % AXES[meta["a"]]) if meta["kind"] == "mode" else None
            metrics, rows = analyze_pec(meta, probes, diagnostics, reference)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail", "failures": ["unreadable: %s" % error]})
            continue
        result["cases"].append(metrics)
        trace.extend(rows)
    result["status"] = "pass" if not result["failures"] and all(c["status"] == "pass" for c in result["cases"]) else "fail"
    return result, trace


def analyze_suite_material(root, suite):
    """V05-A/B/C and V06-A/B suites; returns (result, trace rows)."""
    expected = {"dielectric": mr.expected_wave_names(False), "lossy": mr.expected_wave_names(True),
                "interface": mr.expected_interface_names(), "slab-cavity": mr.expected_slab_names(),
                "dissipation": mr.expected_dissipation_names()}[suite]
    result, directories = load_suite(root, suite, expected)
    result["refinement"] = []
    trace, series = [], {}
    for directory in directories:
        try:
            meta, probes, diagnostics = load_case(directory)
            if suite in ("dielectric", "lossy"):
                metrics, rows = mr.analyze_wave(meta, probes)
            elif suite == "interface":
                metrics, rows, series[meta["case"]] = mr.analyze_interface(meta, probes)
            elif suite == "slab-cavity":
                metrics, rows = mr.analyze_slab(meta, probes)
            else:
                metrics, rows = mr.analyze_dissipation(meta, diagnostics)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail", "failures": ["unreadable: %s" % error]})
            continue
        result["cases"].append(metrics)
        trace.extend(rows)
    by_name = {m["case"]: m for m in result["cases"]}

    def add(label, errors, keys):
        entry = mr.refinement(errors, keys)
        entry["sequence"] = label
        result["refinement"].append(entry)
    if suite == "dielectric":
        for a, b in mr.ORDERINGS:
            pair = AXES[a] + AXES[b]
            add(pair, {p: by_name.get("dielectric-%s-p%d" % (pair, p), {}).get("continuum_error") for p in (24, 48, 96)},
                (24, 48, 96))
    elif suite == "lossy":
        for sigma in mr.V06_SIGMAS:
            for a, b in mr.ORDERINGS:
                pair = AXES[a] + AXES[b]
                keys = (24, 48, 96) if pair == "xy" else (24, 48)
                for quantity in ("decay_error", "phase_error"):
                    add("%s %s %s" % (pair, mr.SIGMA_LABEL[sigma], quantity),
                        {p: by_name.get("lossy-%s-p%d-%s" % (pair, p, mr.SIGMA_LABEL[sigma]), {}).get(quantity)
                         for p in keys}, keys)
    elif suite == "slab-cavity":
        for a in range(3):
            for mode in (1, 2):
                add("%s m%d" % (AXES[a], mode),
                    {p: by_name.get("slab-%s-m%d-p%d" % (AXES[a], mode, p), {}).get("continuum_error") for p in (24, 48, 96)},
                    (24, 48, 96))
    elif suite == "interface":
        add("x band maximum", {p: by_name.get("interface-x-p%d" % p, {}).get("continuum_error") for p in (16, 32, 64)},
            (16, 32, 64))
        result["orientation"] = [mr.orientation_agreement(series, p) for p in (16, 32)]
    result["status"] = "pass" if not result["failures"] and all(
        item["status"] == "pass" for key in ("cases", "refinement", "orientation")
        for item in result.get(key, [])) else "fail"
    return result, trace


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: repr(v) if isinstance(v, float) else v for k, v in row.items()})


def write_material_csv(path, rows):
    """Heterogeneous material trace rows under the union of their keys."""
    keys = []
    for row in rows:
        keys.extend(k for k in row if k not in keys)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, restval="")
        if keys:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: repr(v) if isinstance(v, float) else v for k, v in row.items()})


def fmt(value, digits=6):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return "%.*g" % (digits, value)
    return str(value)


def material_report(suite):
    lines = [""]
    name = suite["suite"]
    if name == "dielectric":
        lines += ["| Case | N | omega_m sqrt(eps_r)/(k c0)-1 | cap | predicted | discrete | amp E/H | resid E/H | inactive"
                  " | Z error | status |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in suite["cases"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s / %s | %s / %s | %s | %s | %s |" % (
                c["case"], c.get("steps"), fmt(c.get("continuum_error"), 9), fmt(c.get("continuum_cap")),
                fmt(c.get("predicted_continuum_error"), 9), fmt(c.get("discrete_error"), 3),
                fmt(c.get("max_amplitude_error_e"), 3), fmt(c.get("max_amplitude_error_h"), 3),
                fmt(c.get("max_residual_e"), 3), fmt(c.get("max_residual_h"), 3), fmt(c.get("max_inactive"), 3),
                fmt(c.get("max_impedance_error"), 3), c["status"]))
    elif name == "lossy":
        lines += ["| Case | N | x | decay error | cap | predicted | phase error | cap | predicted | max abs(rho/z-1) "
                  "| H ratio (reported) | min abs(C) | status |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in suite["cases"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["case"], c.get("steps"), fmt(c.get("x"), 4), fmt(c.get("decay_error"), 6), fmt(c.get("decay_cap")),
                fmt(c.get("predicted_decay_error"), 6), fmt(c.get("phase_error"), 6), fmt(c.get("phase_cap")),
                fmt(c.get("predicted_phase_error"), 6), fmt(c.get("max_discrete_ratio_error"), 3),
                fmt(c.get("max_magnetic_ratio_error_reported"), 3), fmt(c.get("min_amplitude"), 4), c["status"]))
    elif name == "interface":
        lines += ["| Case | N | gate | band max continuum | cap | discrete max | max abs(Im R) | purity 1.5 | purity v1"
                  " (reported) | states below floor | b-plane mismatches | status |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in suite["cases"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["case"], c.get("steps"), c.get("gate"), fmt(c.get("continuum_error"), 6), fmt(c.get("continuum_cap")),
                fmt(c.get("max_discrete_error"), 3), fmt(c.get("max_imag_R"), 3), fmt(c.get("max_purity_residual"), 3),
                fmt(c.get("max_purity_residual_v1_reported"), 3), c.get("purity_states_below_floor"),
                c.get("b_plane_mismatches"), c["status"]))
        for item in suite.get("orientation", []):
            lines.append("")
            lines.append("Orientation agreement p=%s: max normalized difference %s, %s" % (
                item["p"], fmt(item.get("max_difference"), 3), item["status"]))
    elif name == "slab-cavity":
        lines += ["| Case | N | f_c GHz | f_m/f_c-1 | cap | predicted | f_m/f_d-1 | amplitude | residual | status |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in suite["cases"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["case"], c.get("steps"), fmt((c.get("f_c_hz") or 0) / 1e9, 7), fmt(c.get("continuum_error"), 9),
                fmt(c.get("continuum_cap")), fmt(c.get("predicted_continuum_error"), 9), fmt(c.get("discrete_error"), 3),
                fmt(c.get("max_amplitude_error"), 3), fmt(c.get("max_normalized_residual"), 3), c["status"]))
    elif name == "dissipation":
        lines += ["| Case | N | Q_0 J | max balance / Q_n | max Q increase | bound violation | negative D | Q_N/Q_0 | status |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in suite["cases"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["case"], c.get("steps"), fmt(c.get("Q0_J"), 6), fmt(c.get("max_balance_error"), 3),
                fmt(c.get("max_relative_Q_increase"), 3), c.get("bound_violation_state"),
                c.get("first_negative_D_state"), fmt(c.get("final_Q_ratio"), 3), c["status"]))
    if suite.get("refinement"):
        lines += ["", "| Sequence | errors | orders | status |", "| --- | --- | --- | --- |"]
        for r in suite["refinement"]:
            lines.append("| %s | %s | %s | %s |" % (r["sequence"], ", ".join(fmt(e, 6) for e in r["errors"]),
                                                     ", ".join(fmt(o, 6) for o in r["orders"]), r["status"]))
    return lines


def report(summary):
    lines = ["# closed-v1 physical analysis (MAT-02 V04, MAT-03 V05/V06)", "",
             "Generated by scripts/analyze_closed_benchmarks.py; thresholds are the fixed MAT-01 v1 values.",
             "Overall status: **%s**." % summary["status"].upper(), ""]
    for suite in summary["suites"]:
        lines.append("## Suite %s: %s" % (suite["suite"], suite["status"].upper()))
        lines.append("")
        for failure in suite["failures"]:
            lines.append("- SUITE FAILURE: %s" % failure)
        if suite["suite"] == "cavity":
            lines += ["", "| Case | N | omega_m/omega_c-1 | cap | predicted | omega_m/omega_d-1 | amplitude | magnetic | residual | status |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for c in suite["cases"]:
                lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    c["case"], c.get("steps"), fmt(c.get("continuum_error"), 9), fmt(c.get("continuum_cap")),
                    fmt(c.get("predicted_continuum_error"), 9), fmt(c.get("discrete_error"), 3),
                    fmt(c.get("max_amplitude_error"), 3), fmt(c.get("max_magnetic_error"), 3),
                    fmt(c.get("max_normalized_residual"), 3), c["status"]))
            lines += ["", "| Polarization | Mode | e1 | e2 | e4 | order 1/2 | order 2/4 | status |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            for r in suite.get("refinement", []):
                lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    r["polarization"], r["mode"], *[fmt(e, 9) for e in r["errors"]], *[fmt(o, 9) for o in r["orders"]], r["status"]))
        elif suite["suite"] == "cavity-spectrum":
            for c in suite["cases"]:
                for label, analysis in c.get("analyses", {}).items():
                    lines.append("")
                    lines.append("%s record (%s states, bin %s MHz): max offset %s bins, max height error %s, spurious %d, status %s" % (
                        label, analysis.get("states"), fmt(analysis.get("bin_hz", 0) / 1e6, 5), fmt(analysis.get("max_offset_bins"), 3),
                        fmt(analysis.get("max_height_error"), 3), len(analysis.get("spurious_peaks", [])), analysis["status"]))
                if c.get("post_pulse_invariant_drift") is not None:
                    lines.append("post-pulse invariant drift (diagnostic): %s" % fmt(c["post_pulse_invariant_drift"], 3))
                if c.get("growth"):
                    lines += ["", "| Component | window max | later max | ratio | floor | null | status |",
                              "| --- | --- | --- | --- | --- | --- | --- |"]
                    for name, g in c["growth"].items():
                        ok = g["later_max"] <= g["floor"] if g["null_component"] else g["later_max"] <= GROWTH_FACTOR * g["window_max"]
                        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                            name, fmt(g["window_max"], 4), fmt(g["later_max"], 4), fmt(g.get("v1_ratio"), 4),
                            fmt(g["floor"], 3), g["null_component"], "pass" if ok else "fail"))
        if suite["suite"] == "pec":
            lines += ["", "| Case | N | shell edges | silent max | equivalence max / bitwise / matched | status |",
                      "| --- | --- | --- | --- | --- | --- |"]
            for c in suite["cases"]:
                lines.append("| %s | %s | %s | %s | %s / %s / %s | %s |" % (
                    c["case"], c.get("steps"), c.get("shell_edges"),
                    fmt(c.get("max_outside_sample", c.get("max_silent_sample")), 3),
                    fmt(c.get("equivalence_max_difference"), 3), c.get("equivalence_bitwise", "n/a"),
                    c.get("equivalence_matched", "n/a"), c["status"]))
            driven = [c for c in suite["cases"] if c.get("drive_prediction") is not None]
            if driven:
                lines += ["", "| Driven case | first Ez sample | closed-form deposit | relative error | "
                          "source edge sample | signed error | peak E | floor | ratio | invariant drift |",
                          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
                for c in driven:
                    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                        c["case"], fmt(c.get("drive_first_state"), 9), fmt(c["drive_prediction"], 9),
                        fmt(c.get("drive_error"), 3), fmt(c.get("source_probe_first_state"), 9),
                        fmt(c.get("source_probe_error"), 3), fmt(c.get("excitation_peak"), 4),
                        fmt(c.get("excitation_floor"), 4), fmt(c.get("excitation_ratio"), 4),
                        fmt(c.get("post_pulse_invariant_drift"), 3)))
        elif suite["suite"] in ("dielectric", "lossy", "interface", "slab-cavity", "dissipation"):
            lines += material_report(suite)
        for c in suite["cases"]:
            for failure in c.get("failures", []):
                lines.append("- FAIL %s: %s" % (c["case"], failure))
        for item in suite.get("refinement", []):
            label = item.get("sequence") or "%s %s" % (item.get("polarization"), item.get("mode"))
            for failure in item.get("failures", []):
                lines.append("- FAIL refinement %s: %s" % (label, failure))
        for item in suite.get("orientation", []):
            for failure in item.get("failures", []):
                lines.append("- FAIL orientation p=%s: %s" % (item["p"], failure))
        lines.append("")
    if summary.get("resources"):
        lines += ["## Measured resources", "", "| Suite | status | elapsed s | peak working set bytes |",
                  "| --- | --- | --- | --- |"]
        for name, item in summary["resources"].get("suites", {}).items():
            lines.append("| %s | %s | %s | %s |" % (name, item.get("status"), fmt(item.get("elapsed_seconds"), 5),
                                                    item.get("peak_working_set_bytes")))
        lines.append("")
    lines += ["Per-state modal projections are in cavity-trace.csv; identified lines are in spectrum-peaks.csv;",
              "material fits, growth factors, R/T spectra and balances are in material-trace.csv.",
              "A passing analysis supports only the declared envelope of the MAT-01 specification."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", choices=("all", "v04", "materials", "cavity", "cavity-spectrum", "pec") + MATERIAL_SUITES,
                        default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": "closed-v1-analysis-1", "input": str(args.input.resolve()), "suites": [],
               "thresholds": {"continuum_cap": {str(k): v for k, v in V04_CAPS.items()}, "half_q_cap": V04_HALF_Q_CAP,
                              "discrete": V04_DISCRETE_LIMIT, "structure": V04_STRUCTURE_LIMIT,
                              "order_range": ORDER_RANGE, "peak_bins": V04B_PEAK_BIN_LIMIT,
                              "height": V04B_HEIGHT_LIMIT, "strength_floor": V04B_STRENGTH_FLOOR,
                              "f_cut_hz": V04B_FCUT, "growth_factor": GROWTH_FACTOR,
                              "null_floor": NULL_FLOOR, "growth_rule_version": "1.1",
                              "equivalence": EQUIVALENCE_LIMIT, "drive": V04C_DRIVE_LIMIT,
                              "excitation_floor": V04C_EXCITATION_FLOOR, "invariant": V04C_INVARIANT_LIMIT,
                              "excitation_rule_version": "1.4"},
               "analysis_environment": {"python": sys.version.split()[0], "platform": platform.platform()}}
    # MAT-03 limits are recorded only when a material suite is analyzed, so that a
    # V04-only re-analysis stays key-for-key comparable with the MAT-02 summary.
    if args.suite in ("all", "materials") + MATERIAL_SUITES:
        summary["thresholds"].update({
            "v05a_caps": {str(k): v for k, v in mr.V05A_CAPS.items()}, "v05_structure": mr.STRUCTURE_LIMIT,
            "v05a_impedance": mr.IMPEDANCE_LIMIT, "v05b_caps": {str(k): v for k, v in mr.V05B_R_CAPS.items()},
            "v05b_discrete": mr.V05B_DISCRETE_LIMIT, "v05b_orientation": mr.ORIENTATION_LIMIT,
            "v05c_caps": {"%d,%d" % k: v for k, v in mr.V05C_CAPS.items()},
            "v06a_decay_caps": {"%d,%g" % k: v for k, v in mr.V06_DECAY_CAPS.items()},
            "v06a_phase_caps": {str(k): v for k, v in mr.V06_PHASE_CAPS.items()},
            "v06a_discrete": mr.V06_DISCRETE_LIMIT, "v06b_balance": mr.BALANCE_LIMIT,
            "v06b_monotone": mr.MONOTONE_LIMIT, "v06b_final_energy": mr.FINAL_ENERGY_LIMIT,
            "coefficients": COEFFICIENT_LIMIT, "v05b_purity_floor": mr.PURITY_FLOOR,
            "material_rule_version": "1; V05-B purity 1.5"})
    trace, peaks, material_trace = [], [], []
    cavity_cases = {}
    v04 = args.suite in ("all", "v04")
    if v04 or args.suite == "cavity":
        result, rows, cavity_cases = analyze_suite_cavity(args.input / "cavity")
        summary["suites"].append(result)
        trace = rows
    if v04 or args.suite == "cavity-spectrum":
        result, rows = analyze_suite_spectrum(args.input / "cavity-spectrum")
        summary["suites"].append(result)
        peaks = rows
    if v04 or args.suite == "pec":
        if args.suite == "pec":
            cavity_root = args.input / "cavity"
            for name in ("cavity-%s-m11-s1" % AXES[a] for a in range(3)):
                try:
                    meta, probes, _ = load_case(cavity_root / name)
                    cavity_cases[name] = (meta, probes)
                except Exception:
                    pass
        result, rows = analyze_suite_pec(args.input / "pec", cavity_cases)
        summary["suites"].append(result)
        trace.extend(rows)
    for suite in MATERIAL_SUITES:
        if args.suite in ("all", "materials", suite):
            result, rows = analyze_suite_material(args.input / suite, suite)
            summary["suites"].append(result)
            material_trace.extend(rows)
    resources = args.input / "resources.json"
    try:
        summary["resources"] = read_json(resources) if resources.is_file() else None
    except Exception as error:
        summary["resources"] = None
        summary["resources_error"] = str(error)
    summary["suites"].append(check_resources(summary["resources"], [s["suite"] for s in summary["suites"]]))
    snapshots = set()
    provenance_failures = []
    for suite in summary["suites"]:
        for case in suite.get("cases", []):
            path = Path(suite["root"]) / case["case"] / "metadata.json"
            if not path.is_file():
                continue
            try:
                snapshots.add(read_json(path)["source_snapshot_sha256"])
            except Exception as error:
                provenance_failures.append("%s: unreadable metadata (%s)" % (case["case"], error))
    summary["source_snapshots"] = sorted(snapshots)
    if len(snapshots) != 1:
        provenance_failures.append("cases come from %d source snapshots" % len(snapshots))
    if provenance_failures:
        summary["suites"].append({"suite": "provenance", "cases": [], "status": "fail", "failures": provenance_failures})
    summary["status"] = "pass" if summary["suites"] and all(s["status"] == "pass" for s in summary["suites"]) else "fail"
    (args.output / "metrics.json").write_text(json.dumps(summary, indent=1) + "\n")
    write_csv(args.output / "cavity-trace.csv", trace)
    write_csv(args.output / "spectrum-peaks.csv", peaks)
    write_material_csv(args.output / "material-trace.csv", material_trace)
    (args.output / "report.md").write_text(report(summary))
    print(report(summary))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
