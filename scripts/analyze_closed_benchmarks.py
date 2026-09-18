"""MAT-02 independent physical analysis of closed-v1 raw artifacts (V04-A/B/C).

Reads emitted metadata/CSV only; no solver operator is imported. The
predictions and fixed version-1 limits come from the MAT-01 specification
audit (check_material_benchmarks.py), which evaluates only closed-form
expressions. Every check is recorded and all outputs are written before the
nonzero exit for a failed suite.

Python 3.9+, standard library. Usage:
  python scripts/analyze_closed_benchmarks.py --input ROOT --output DIR
ROOT contains the CLI suite directories ``cavity``, ``cavity-spectrum`` and
``pec`` and an optional ``resources.json`` from scripts/run_reference_benchmarks.py.
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
                                       V04C_SOURCE_INSIDE, V04C_SOURCE_OUTSIDE)
from check_reference_runs import read_json, C0, MU0, EPS0, ETA0, NAMES

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


def finite(value):
    return isinstance(value, float) and math.isfinite(value)


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
        if not (meta["field_bytes"] == payload and meta["mask_bytes"] == mask_bytes
                and 2 * payload + mask_bytes <= meta["working_bytes_budgeted"] <= 2**31):
            raise ValueError("transient memory budget")
        if not (meta["fixture_max_divergence_error"] <= 1e-11 and meta["fixture_max_eigen_error"] <= 1e-11):
            raise ValueError("fixture report")
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
            per_state[n] = per_state.get(n, 0) + 1
            for a, name in enumerate(("x_m", "y_m", "z_m")):
                half = .5 if (a == id if id < 3 else a != id - 3) else 0
                expected_position = (index[a] + half) * spacing[a]
                position = float(row[name])
                if not (0 <= index[a] < extents[id][a] and
                        abs(position - expected_position) <= 5e-15 * max(spacing[a], abs(expected_position))):
                    raise ValueError("native location")
        if sorted(per_state) != list(range(steps + 1)) or len(set(per_state.values())) != 1:
            raise ValueError("probe rows per state")
        with (directory / "diagnostics.csv").open(newline="") as handle:
            energy = list(csv.DictReader(handle))
        if len(energy) != (steps + 1 if meta["diagnostics"] else 0):
            raise ValueError("diagnostic rows")
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
        if meta["kind"] != "source" or meta["source_index"] != expected_source:
            failures.append("source edge differs from v1")
        if fixed_suite and meta["steps"] != 4096:
            failures.append("steps %d differ from v1 4096" % meta["steps"])
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
            if values[0]["U_J"] != 0:
                failures.append("driven case does not start from zero fields")
        if any(not math.isfinite(float(row["value"])) for row in probes):
            failures.append("nonfinite probe sample")
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


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: repr(v) if isinstance(v, float) else v for k, v in row.items()})


def fmt(value, digits=6):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return "%.*g" % (digits, value)
    return str(value)


def report(summary):
    lines = ["# MAT-02 closed-v1 physical analysis", "",
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
        elif suite["suite"] == "pec":
            lines += ["", "| Case | N | shell edges | silent max | equivalence max / bitwise / matched | status |",
                      "| --- | --- | --- | --- | --- | --- |"]
            for c in suite["cases"]:
                lines.append("| %s | %s | %s | %s | %s / %s / %s | %s |" % (
                    c["case"], c.get("steps"), c.get("shell_edges"),
                    fmt(c.get("max_outside_sample", c.get("max_silent_sample")), 3),
                    fmt(c.get("equivalence_max_difference"), 3), c.get("equivalence_bitwise", "n/a"),
                    c.get("equivalence_matched", "n/a"), c["status"]))
        for c in suite["cases"]:
            for failure in c.get("failures", []):
                lines.append("- FAIL %s: %s" % (c["case"], failure))
        for item in suite.get("refinement", []):
            for failure in item.get("failures", []):
                lines.append("- FAIL refinement %s %s: %s" % (item["polarization"], item["mode"], failure))
        lines.append("")
    if summary.get("resources"):
        lines += ["## Measured resources", "", "| Suite | status | elapsed s | peak working set bytes |",
                  "| --- | --- | --- | --- |"]
        for name, item in summary["resources"].get("suites", {}).items():
            lines.append("| %s | %s | %s | %s |" % (name, item.get("status"), fmt(item.get("elapsed_seconds"), 5),
                                                    item.get("peak_working_set_bytes")))
        lines.append("")
    lines += ["Per-state modal projections are in cavity-trace.csv; identified lines are in spectrum-peaks.csv.",
              "A passing analysis supports only the declared PEC-cavity envelope of the MAT-01 specification."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", choices=("all", "cavity", "cavity-spectrum", "pec"), default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": "closed-v1-analysis-1", "input": str(args.input.resolve()), "suites": [],
               "thresholds": {"continuum_cap": {str(k): v for k, v in V04_CAPS.items()}, "half_q_cap": V04_HALF_Q_CAP,
                              "discrete": V04_DISCRETE_LIMIT, "structure": V04_STRUCTURE_LIMIT,
                              "order_range": ORDER_RANGE, "peak_bins": V04B_PEAK_BIN_LIMIT,
                              "height": V04B_HEIGHT_LIMIT, "strength_floor": V04B_STRENGTH_FLOOR,
                              "f_cut_hz": V04B_FCUT, "growth_factor": GROWTH_FACTOR,
                              "null_floor": NULL_FLOOR, "growth_rule_version": "1.1",
                              "equivalence": EQUIVALENCE_LIMIT},
               "analysis_environment": {"python": sys.version.split()[0], "platform": platform.platform()}}
    trace, peaks = [], []
    cavity_cases = {}
    if args.suite in ("all", "cavity"):
        result, rows, cavity_cases = analyze_suite_cavity(args.input / "cavity")
        summary["suites"].append(result)
        trace = rows
    if args.suite in ("all", "cavity-spectrum"):
        result, rows = analyze_suite_spectrum(args.input / "cavity-spectrum")
        summary["suites"].append(result)
        peaks = rows
    if args.suite in ("all", "pec"):
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
    (args.output / "report.md").write_text(report(summary))
    print(report(summary))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
