"""MAT-02/MAT-03 reduction validation before V04-V06 physical results are accepted.

1. Synthetic pass/failure-detection checks of the closed-v1 analyzer's
   V04-A/B/C reductions on prescribed data (no solver output).
2. With --app: run the closed-v1 CLI smoke suite (four steps) and compare its
   probes, U/Q, component and region maxima with an independent pure-Python
   transcription of the FND-03 update equations extended by the E-edge PEC
   mask, the exact-mode fixture and the pulse; then apply the analyzer to the
   smoke cases and require the shell case to reproduce the open cavity.
3. MAT-03 (check_material_analysis.py): synthetic V05/V06 and coefficient-table
   checks, and with --app the material oracle on the five material smoke cases.

Python 3.9+, standard library. No production operator is imported.
"""
import argparse
import cmath
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from analyze_closed_benchmarks import (analyze_cavity, analyze_pec, analyze_spectrum, audit_closed, closure_counts,
                                       initialization_accepted, line_specification, load_case, parse_cavity_name,
                                       probe_coverage, refinement, AXES, MODES, REGIONS, V04C_BOX,
                                       HISTORICAL_MODE_INITIALIZATION, HISTORICAL_SNAPSHOT, MODE_INITIALIZATION,
                                       SOURCE_INITIALIZATION)
from check_material_benchmarks import (cavity_lines, cavity_mode, cyclic, pec_marked, pulse_samples, pulse_drive, V04B_STEPS,
                                       V04B_SHORT_STEPS, V04B_SOURCE_INDEX, V04B_PROBE_INDEX, V04B_TAU, V04B_FCUT,
                                       V04_BASE_CELLS, V04C_MARGIN, V04C_SOURCE_OUTSIDE)
from check_reference_analysis import Oracle, half_offsets, close, MU0, EPS0, PI
from check_reference_runs import NAMES, C0, ETA0
import check_material_analysis


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def has_failure(metrics, text):
    return any(text in failure for failure in metrics["failures"])


def base_meta(name, suite, kind, cells, spacing, dt, steps, q=0.99, pad=0):
    box = [[pad, pad + c] for c in V04_BASE_CELLS]
    closure = closure_counts(cells)
    masked = list(closure)
    primitives = []
    if pad:
        primitives = [{"shape": "pec_shell", "low": [pad] * 3, "high": [pad + c for c in V04_BASE_CELLS]}]
        masked = [c + e for c, e in zip(closure, (864, 1024, 1120))]
    return {"case": name, "suite": suite, "kind": kind, "cells": list(cells), "spacing_m": list(spacing), "dt_s": dt,
            "q": q, "steps": steps, "origin": [pad] * 3, "cavity_cells": list(V04_BASE_CELLS), "region": bool(pad),
            "diagnostics": bool(pad) or kind == "source", "pec_primitives": primitives, "masked_edges": masked,
            "closure_edges": closure, "elapsed_seconds": 0.0, "box": box}


def synthetic_cavity(a, nb, nc, s, q=0.99, pad=0, omega_factor=1.0, amplitude_error=0.0, h_sign=1, phase=0.0,
                     drop=None, relocate=False, steps=None, extra=False):
    mode = cavity_mode(s, a, nb, nc, q)
    cells = [n + 2 * pad for n in mode["cells"]]
    steps = mode["steps"] if steps is None else steps
    name = "pec-c1-%s" % AXES[a] if pad else "cavity-%s-m%d%d-s%d%s" % (AXES[a], nb, nc, s, "-q50" if q == 0.5 else "")
    meta = base_meta(name, "pec" if pad else "cavity", "mode", cells, mode["spacing"], mode["dt"], steps, q, pad)
    meta.update({"a": a, "mode": [nb, nc], "s": s, "cavity_cells": [n * s for n in V04_BASE_CELLS]})
    _, b, c = cyclic(a)
    dt = mode["dt"]
    omega = mode["omega_d"] * omega_factor
    big_omega = 2 / dt * math.sin(omega * dt / 2)
    kb, kc = mode["kb"], mode["kc"]
    hb_amp, hc_amp = -mode["Kc"] / (MU0 * big_omega), mode["Kb"] / (MU0 * big_omega)
    spacing = mode["spacing"]
    rows = []
    for n in range(steps + 1):
        for id, indices in line_specification(meta, parse_cavity_name(name)).items():
            half = half_offsets(id)
            for index in indices:
                r = [(index[t] - pad + half[t]) * spacing[t] for t in range(3)]
                shape = math.sin(kb * r[b]) if id == a or id == c + 3 else 1.0
                if id == a:
                    value = (1 + amplitude_error) * math.cos(omega * n * dt + phase) * shape * math.sin(kc * r[c])
                elif id == b + 3:
                    value = h_sign * hb_amp * math.sin(omega * (n - 0.5) * dt + phase) * math.sin(kb * r[b]) * math.cos(kc * r[c])
                else:
                    value = h_sign * hc_amp * math.sin(omega * (n - 0.5) * dt + phase) * math.cos(kb * r[b]) * math.sin(kc * r[c])
                stored = list(index)
                if relocate and id == a:
                    stored[c] += 1
                position = [(stored[t] + half[t]) * spacing[t] for t in range(3)]
                rows.append({"state": str(n), "component": NAMES[id], "i": str(stored[0]), "j": str(stored[1]),
                             "k": str(stored[2]), "x_m": repr(position[0]), "y_m": repr(position[1]),
                             "z_m": repr(position[2]), "time_s": repr((n - (0 if id < 3 else 0.5)) * dt), "value": repr(value)})
    if drop is not None:
        del rows[drop]
    if extra:
        rows.append(dict(rows[0], component="Ex"))
    return meta, rows


def synthetic_cavity_checks():
    checks = 0
    worst = 0.0
    for a in range(3):
        for nb, nc in MODES:
            for s in (1, 2, 4):
                meta, rows = synthetic_cavity(a, nb, nc, s)
                metrics, trace = analyze_cavity(meta, rows)
                require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
                require(len(trace) == meta["steps"] + 1, "trace per state")
                worst = max(worst, abs(metrics["continuum_error"] - metrics["predicted_continuum_error"]),
                            metrics["discrete_error"], metrics["max_amplitude_error"], metrics["max_magnetic_error"],
                            metrics["max_normalized_residual"])
                checks += 1
        meta, rows = synthetic_cavity(a, 1, 1, 1, q=0.5)
        metrics, _ = analyze_cavity(meta, rows)
        require(metrics["status"] == "pass" and metrics["continuum_cap"] == 0.0028, "synthetic q=0.5 %s" % metrics["failures"])
        checks += 1
    require(worst <= 1e-11, "synthetic V04-A estimator precision %.3g" % worst)
    a, nb, nc = 1, 2, 1
    faults = [
        (dict(omega_factor=1 + 3e-9), "discrete frequency error"),
        (dict(amplitude_error=3e-9), "modal amplitude error"),
        (dict(h_sign=-1), "magnetic relation error"),
        (dict(phase=1e-6), "error exceeds limit"),
        (dict(relocate=True), "prescribed native line"),
        (dict(drop=7), "native samples"),
        (dict(steps=2), "differ from v1"),
        (dict(extra=True), "outside the three prescribed lines"),
        (dict(omega_factor=0.99), "continuum resonance error"),
    ]
    for kwargs, text in faults:
        meta, rows = synthetic_cavity(a, nb, nc, 1, **kwargs)
        metrics, _ = analyze_cavity(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected: " + text)
        checks += 1
    meta, rows = synthetic_cavity(a, nb, nc, 1)
    meta["cells"][2] += 1
    require(has_failure(analyze_cavity(meta, rows)[0], "cells"), "geometry mismatch undetected")
    meta, rows = synthetic_cavity(a, nb, nc, 1)
    rows[3]["time_s"] = repr(float(rows[3]["time_s"]) + 1e-13)
    require(has_failure(analyze_cavity(meta, rows)[0], "mixes sample times"), "time mismatch undetected")
    meta, rows = synthetic_cavity(a, nb, nc, 1, steps=3)
    metrics, _ = analyze_cavity(meta, rows, fixed_suite=False)
    require(metrics["status"] == "pass", "smoke-length synthetic: %s" % metrics["failures"])
    checks += 3
    errors = {s: cavity_mode(s, 0, 1, 1)["error"] for s in (1, 2, 4)}
    result = refinement(errors)
    require(result["status"] == "pass" and all(1.8 <= o <= 2.2 for o in result["orders"]), "refinement pass")
    for bad in ({1: 1e-3, 2: 3e-4, 4: 1.5e-4}, {1: 1e-3, 2: 1e-3, 4: 2.5e-4}, {1: 0.0, 2: 0.0, 4: 0.0},
                {1: 1e-3, 2: None, 4: 1e-4}):
        require(refinement(bad)["status"] == "fail", "undetected refinement failure %s" % bad)
    checks += 5
    print("PASS synthetic V04-A reductions: %d checks; worst estimator deviation %.3g" % (checks, worst))
    return checks


def modal_series(lines, dt, samples, steps, shift=None, spurious=None, missing=None):
    """Sum of exact modal responses after the pulse (the MAT-01 audit construction)."""
    n_pulse = len(samples)
    phases = {}
    for line in lines:
        theta = line["omega_d"] * dt
        pulse = sum((samples[m] - (samples[m - 1] if m else 0.0)) * cmath.exp(-1j * theta * m)
                    for m in range(n_pulse)) + (-samples[-1]) * cmath.exp(-1j * theta * n_pulse)
        phases[line["mode"]] = cmath.phase(pulse)
    strongest = max(line["strength"] for line in lines if line["omega_d"] / 2 / PI < V04B_FCUT)
    series = []
    for n in range(steps + 1):
        t = n * dt
        value = 0.0
        if n >= n_pulse + 1:
            for line in lines:
                if line["mode"] == missing:
                    continue
                omega = line["omega_d"]
                if shift is not None and line["mode"] == shift[0]:
                    omega = line["omega_d"] + 2 * PI * shift[1]
                value += line["signed"] * math.sin(omega * t + phases[line["mode"]])
            if spurious is not None:
                value += spurious[1] * strongest * math.sin(2 * PI * spurious[0] * t)
        series.append(value)
    return series


def synthetic_spectrum(steps=V04B_STEPS, growth=1.0, null_level=1e-18, null_growth=3.0, **kwargs):
    lines, dt, samples, source, probe = cavity_lines(1)
    series = modal_series(lines, dt, samples, steps, **kwargs)
    meta = base_meta("spectrum-s1", "cavity-spectrum", "source", V04_BASE_CELLS, (0.01, 0.015, 0.02), dt, steps)
    meta.update({"source_index": list(source), "probe_indices": [list(probe)], "tau_s": V04B_TAU,
                 "pulse_samples": len(samples), "pulse_half_samples": (len(samples) - 1) // 2})
    probes = [{"state": str(n), "component": "Ez", "i": str(probe[0]), "j": str(probe[1]), "k": str(probe[2]),
               "x_m": repr(probe[0] * 0.01), "y_m": repr(probe[1] * 0.015), "z_m": repr((probe[2] + 0.5) * 0.02),
               "time_s": repr(n * dt), "value": repr(value)} for n, value in enumerate(series)]
    diagnostics = []
    for n in range(steps + 1):
        level = 0.0 if n == 0 else (growth if n >= len(samples) + 4096 else 1.0)
        row = {"state": str(n), "e_time_s": repr(n * dt), "h_time_s": repr((n - 0.5) * dt),
               "U_J": repr(level * 1e-12), "Q_J": repr(level * 1e-12)}
        row.update({"max_" + name: repr(level) for name in NAMES})
        # Hz is analytically null for the z-directed source: roundoff-level values
        # that drift upward, as observed, must pass; growth above the floor must fail.
        row["max_Hz"] = repr(0.0 if n == 0 else null_level * (null_growth if n >= len(samples) + 4096 else 1.0))
        diagnostics.append(row)
    return meta, probes, diagnostics


def synthetic_spectrum_checks():
    checks = 0
    meta, probes, diagnostics = synthetic_spectrum()
    metrics, rows = analyze_spectrum(meta, probes, diagnostics)
    require(metrics["status"] == "pass", "synthetic V04-B: %s" % metrics["failures"])
    require(set(metrics["analyses"]) == {"full", "truncated"} and len(rows) == 16, "both analyses with eight lines each")
    require(metrics["growth"]["Hz"]["null_component"] and not metrics["growth"]["Ex"]["null_component"], "null-component classification")
    worst = max(a["max_offset_bins"] for a in metrics["analyses"].values())
    checks += 2
    lines, dt, _, _, _ = cavity_lines(1)
    bin_hz = 1 / (V04B_STEPS * dt)
    faults = [
        (dict(shift=((1, 1, 2), 0.6 * bin_hz)), "no peak within 0.25 bin"),
        (dict(spurious=(1.65e9, 0.1)), "spurious peak"),
        (dict(missing=(1, 1, 2)), "no peak within 0.25 bin"),
        (dict(steps=20000), "fewer than"),
        (dict(growth=2.0), "grow beyond 1.5"),
        (dict(null_growth=1e12), "null component whose maxima exceed the floor"),
    ]
    for kwargs, text in faults:
        meta, probes, diagnostics = synthetic_spectrum(**kwargs)
        metrics, _ = analyze_spectrum(meta, probes, diagnostics)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected: " + text)
        checks += 1
    meta, probes, diagnostics = synthetic_spectrum()
    probes[0]["value"] = "1e-300"
    require(has_failure(analyze_spectrum(meta, probes, diagnostics)[0], "initial probe"), "nonzero start undetected")
    meta, probes, diagnostics = synthetic_spectrum()
    diagnostics[100]["max_Hy"] = "nan"
    require(has_failure(analyze_spectrum(meta, probes, diagnostics)[0], "nonfinite"), "nonfinite maxima undetected")
    checks += 2
    print("PASS synthetic V04-B identification: %d checks; worst required-line offset %.4f bins" % (checks, worst))
    return checks


def region_rows(steps, dt, alive, silent_value=0.0, silent_at=None, silent_region=None):
    rows = []
    for n in range(steps + 1):
        row = {"state": str(n), "e_time_s": repr(n * dt), "h_time_s": repr((n - 0.5) * dt), "U_J": "0.0" if n == 0 else "1e-14",
               "Q_J": "0.0" if n == 0 else "1e-14"}
        for name in NAMES:
            values = {region: 0.0 for region in REGIONS}
            values[alive] = 1.0
            if silent_at == n and silent_region is not None:
                values[silent_region] = silent_value
            row["max_" + name] = repr(max(values.values()))
            for region in REGIONS:
                row[region + "_" + name] = repr(values[region])
        rows.append(row)
    return rows


def driven_rows(steps, dt, alive, silent_value=0.0, silent_at=None, silent_region=None,
                drive_factor=1.0, peak_factor=1.0, invariant=1e-17, invariant_drift=0.0,
                start_energy=0.0, first_extra=0.0, deposit="Ez"):
    """Region maxima of an idealized C2/C3 record: zero fields, the closed-form
    first deposit on the driven edge alone, the pulse peak, then a constant
    invariant. The factors inject the revision 1.2 faults; ``deposit`` moves the
    first deposit to another component (the revision 1.3 wrong-component fault)."""
    _, drive, largest, pulse_length = pulse_drive()
    extra = "Ey" if deposit == "Ex" else "Ex"
    rows = []
    for n in range(steps + 1):
        energy = 0.0
        if n >= pulse_length:
            energy = invariant * (1 + invariant_drift) if n > pulse_length else invariant
        elif n == 0:
            energy = start_energy
        row = {"state": str(n), "e_time_s": repr(n * dt), "h_time_s": repr((n - 0.5) * dt),
               "U_J": repr(energy), "Q_J": repr(energy)}
        for name in NAMES:
            values = {region: 0.0 for region in REGIONS}
            if n == 1:
                values[alive] = drive * drive_factor if name == deposit else (first_extra if name == extra else 0.0)
            elif n > 1:
                values[alive] = largest * peak_factor / (1.0 if name[0] == "E" else ETA0)
            if silent_at == n and silent_region is not None:
                values[silent_region] = silent_value
            row["max_" + name] = repr(max(values.values()))
            for region in REGIONS:
                row[region + "_" + name] = repr(values[region])
        rows.append(row)
    return rows


def driven_probes(steps, dt, source, silent, spacing=(0.01, 0.015, 0.02), first=None, silent_first=0.0,
                  component="Ez", shift=False, omit=()):
    """Native probe record of an idealized C2/C3 run: the signed closed-form
    deposit `-(dt/eps0) J0 g_0` on the source edge at state 1, zero elsewhere.
    ``first``, ``silent_first``, ``component`` and ``shift`` inject the revision
    1.3 wrong-sign, leaking-probe, wrong-component and wrong-location faults;
    ``omit`` holds `(role, state)` pairs to delete, with `state=None` deleting
    that probe from every state (the revision 1.4 missing-record fault)."""
    _, drive, _, _ = pulse_drive()
    first = -drive if first is None else first
    recorded = (source[0], source[1], source[2] + 1) if shift else source
    rows = []
    for n in range(steps + 1):
        for index, value, name, role in ((recorded, first, component, "source"),
                                         (silent, silent_first, "Ez", "quiet")):
            if (role, None) in omit or (role, n) in omit:
                continue
            position = [(index[t] + (0.5 if t == 2 else 0.0)) * spacing[t] for t in range(3)]
            rows.append({"state": str(n), "component": name, "i": str(index[0]), "j": str(index[1]),
                         "k": str(index[2]), "x_m": repr(position[0]), "y_m": repr(position[1]),
                         "z_m": repr(position[2]), "time_s": repr(n * dt),
                         "value": repr(value if n == 1 else 0.0)})
    return rows


def synthetic_pec_checks():
    checks = 0
    reference = synthetic_cavity(0, 1, 1, 1)
    meta, rows = synthetic_cavity(0, 1, 1, 1, pad=V04C_MARGIN)
    diagnostics = region_rows(meta["steps"], meta["dt_s"], "interior")
    metrics, _ = analyze_pec(meta, rows, diagnostics, reference)
    require(metrics["status"] == "pass" and metrics["equivalence_bitwise"] == metrics["equivalence_matched"] > 0,
            "synthetic C1: %s" % metrics["failures"])
    checks += 1
    for region in ("exterior", "surface"):
        bad = region_rows(meta["steps"], meta["dt_s"], "interior", 1e-300, 5, region)
        metrics, _ = analyze_pec(meta, rows, bad, reference)
        require(has_failure(metrics, "%s Ex nonzero" % region), "nonzero %s undetected" % region)
        checks += 1
    perturbed = [dict(r) for r in rows]
    target = next(i for i, r in enumerate(perturbed) if r["component"] == "Ex" and float(r["value"]) > 0.5)
    perturbed[target]["value"] = repr(float(perturbed[target]["value"]) + 1e-11)
    metrics, _ = analyze_pec(meta, perturbed, diagnostics, reference)
    require(has_failure(metrics, "differs from the V04-A case"), "1e-11 interior deviation undetected")
    metrics, _ = analyze_pec(meta, rows, diagnostics, None)
    require(has_failure(metrics, "no cavity s=1 reference"), "missing reference undetected")
    wrong_mask = dict(meta, masked_edges=[m + 1 for m in meta["masked_edges"]])
    require(has_failure(analyze_pec(wrong_mask, rows, diagnostics, reference)[0], "shell edge counts"), "mask count undetected")
    checks += 3
    _, dt, _, _, _ = cavity_lines(1)
    cells = [c + 2 * V04C_MARGIN for c in V04_BASE_CELLS]
    for name, source, quiet, alive in (("pec-c2-inside", (8, 10, 12), (10, 12, 16), "interior"),
                                       ("pec-c3-outside", V04C_SOURCE_OUTSIDE, (9, 11, 13), "exterior")):
        meta = base_meta(name, "pec", "source", cells, (0.01, 0.015, 0.02), dt, 4096, pad=V04C_MARGIN)
        meta.update({"source_index": list(source), "probe_indices": [list(quiet), list(source)], "a": 2})
        probes = driven_probes(4096, dt, source, quiet)
        metrics, _ = analyze_pec(meta, probes, driven_rows(4096, dt, alive), None)
        require(metrics["status"] == "pass", "synthetic %s: %s" % (name, metrics["failures"]))
        silent = [r for r in REGIONS if r != alive]
        for region in silent:
            metrics, _ = analyze_pec(meta, probes, driven_rows(4096, dt, alive, 1e-300, 4000, region), None)
            require(has_failure(metrics, "%s Ex nonzero" % region), "%s leak undetected in %s" % (region, name))
        metrics, _ = analyze_pec(dict(meta, source_index=[2, 2, 2]), probes, driven_rows(4096, dt, alive), None)
        require(has_failure(metrics, "source edge"), "wrong source undetected")
        checks += 4
        # Revision 1.2: a driven case that carries no pulse must not pass.
        excitation_faults = [
            ({"drive_factor": 0.0, "peak_factor": 0.0, "invariant": 0.0}, "closed-form deposit"),
            ({"drive_factor": 0.0, "peak_factor": 0.0, "invariant": 0.0}, "below the excitation floor"),
            ({"drive_factor": 0.0, "peak_factor": 0.0, "invariant": 0.0}, "not positive after the pulse"),
            ({"drive_factor": 1 + 1e-11}, "closed-form deposit"),
            ({"first_extra": 1e-300}, "more than the driven Ez edge"),
            ({"peak_factor": 0.05}, "below the excitation floor"),
            ({"invariant_drift": 1e-11}, "drifts"),
            ({"start_energy": 1e-300}, "does not start from zero fields"),
            # Revision 1.3: the deposit must be in Ez, not merely in some E component.
            ({"deposit": "Ex"}, "more than the driven Ez edge"),
            ({"deposit": "Ex"}, "closed-form deposit"),
        ]
        for kwargs, text in excitation_faults:
            metrics, _ = analyze_pec(meta, probes, driven_rows(4096, dt, alive, **kwargs), None)
            require(has_failure(metrics, text), "undetected in %s: %s" % (name, text))
            checks += 1
        metrics, _ = analyze_pec(dict(meta, dt_s=meta["dt_s"] * (1 + 1e-13)), probes,
                                 driven_rows(4096, dt, alive), None)
        require(has_failure(metrics, "dt differs"), "wrong dt undetected in %s" % name)
        checks += 1
        # Revision 1.3: the native record of the prescribed source edge itself.
        _, drive, _, _ = pulse_drive()
        probe_faults = [
            (dict(first=drive), "signed closed-form deposit"),
            (dict(first=0.0), "signed closed-form deposit"),
            (dict(silent_first=1e-300), "is not zero at state 1"),
            (dict(component="Ex"), "is not the driven Ez"),
            (dict(shift=True), "is not a prescribed index"),
            # Revision 1.4: an absent sample is a missing measurement, not a zero.
            (dict(omit=(("quiet", None),)), "expected 8194"),
            (dict(omit=(("quiet", None),)), "has no state 0 sample"),
            (dict(omit=(("quiet", 1),)), "has no state 1 sample"),
            (dict(omit=(("source", 1),)), "the source edge has no state 1 sample"),
        ]
        for kwargs, text in probe_faults:
            metrics, _ = analyze_pec(meta, driven_probes(4096, dt, source, quiet, **kwargs),
                                     driven_rows(4096, dt, alive), None)
            require(has_failure(metrics, text), "undetected in %s: %s" % (name, text))
            checks += 1
        # A duplicated sample must not stand in for a missing one.
        duplicated = driven_probes(4096, dt, source, quiet, omit=(("quiet", 7),))
        duplicated.append(dict(duplicated[0]))
        metrics, _ = analyze_pec(meta, duplicated, driven_rows(4096, dt, alive), None)
        require(has_failure(metrics, "duplicate state") and has_failure(metrics, "expected 8194"),
                "duplicate standing in for a missing sample undetected in %s" % name)
        checks += 1
        # Revision 1.4: the prescribed set comes from the fixture, so an artifact
        # that declares fewer probes cannot define its own coverage.
        metrics, _ = analyze_pec(dict(meta, probe_indices=[list(quiet)]), probes,
                                 driven_rows(4096, dt, alive), None)
        require(has_failure(metrics, "differ from the v1 set"), "short declared probe set undetected in %s" % name)
        # The MAT-02 R1 reproduction: an Ex deposit with the Ez source record zeroed.
        metrics, _ = analyze_pec(meta, driven_probes(4096, dt, source, quiet, first=0.0),
                                 driven_rows(4096, dt, alive, deposit="Ex"), None)
        require(metrics["status"] == "fail" and has_failure(metrics, "more than the driven Ez edge")
                and has_failure(metrics, "signed closed-form deposit"), "R1 reproduction undetected in %s" % name)
        checks += 2
    print("PASS synthetic V04-C enforcement: %d checks" % checks)
    return checks


def probe_coverage_checks():
    """Revision 1.4: the structural rule for the recorded probe keys.

    Revisions 1–1.3 counted probe rows per state, which a prescribed probe that
    is absent from every state satisfies. The rule is exercised here directly
    because the audit it belongs to needs a whole artifact directory.
    """
    meta = {"kind": "source", "steps": 3, "probe_indices": [[1, 1, 1], [9, 11, 13]]}
    keys = {(2, (1, 1, 1)), (2, (9, 11, 13))}
    states = range(meta["steps"] + 1)
    require(probe_coverage(meta, {n: set(keys) for n in states}) is None, "complete source record rejected")
    faults = [
        ({n: {(2, (1, 1, 1))} for n in states}, "recorded probes differ from the prescribed indices"),
        ({n: set(keys) | {(2, (2, 2, 2))} for n in states}, "recorded probes differ from the prescribed indices"),
        ({n: (set(keys) if n else {(2, (1, 1, 1))}) for n in states}, "probe keys differ between states"),
        ({n: set(keys) for n in range(meta["steps"])}, "probe states"),
        ({n: set() for n in states}, "no probe samples"),
    ]
    for per_state, text in faults:
        require(probe_coverage(meta, per_state) == text, "undetected probe-coverage fault: " + text)
    mode = {"kind": "mode", "steps": 1, "probe_indices": []}
    lines = {n: {(0, (1, 1, 1)), (4, (1, 1, 1)), (5, (1, 1, 1))} for n in range(mode["steps"] + 1)}
    require(probe_coverage(mode, lines) is None, "mode native-line record rejected")
    print("PASS probe-record coverage: 7 checks")
    return 7


def initialization_checks():
    """Revision 1.3: the emitted initial-condition description must be the specified one.

    A run has to be reproducible from its own metadata, so the audit pins the
    description. The single historical mode string (the corrected sign typo) is
    admissible only with the source snapshot that emitted it.
    """
    fresh = "0" * 64
    mode = {"kind": "mode", "initialization": MODE_INITIALIZATION, "source_snapshot_sha256": fresh}
    source = {"kind": "source", "initialization": SOURCE_INITIALIZATION, "source_snapshot_sha256": fresh}
    historical = dict(mode, initialization=HISTORICAL_MODE_INITIALIZATION)
    require(initialization_accepted(mode), "current mode description rejected")
    require(initialization_accepted(source), "source description rejected")
    require(initialization_accepted(dict(historical, source_snapshot_sha256=HISTORICAL_SNAPSHOT)),
            "retained V04 evidence rejected")
    require(not initialization_accepted(historical), "historical sign typo accepted for a new snapshot")
    require(not initialization_accepted(dict(mode, initialization=MODE_INITIALIZATION.replace("H=+(C", "H=-(C"))),
            "flipped mode sign accepted")
    require(not initialization_accepted(dict(mode, initialization=SOURCE_INITIALIZATION)),
            "source description accepted for a mode case")
    require(not initialization_accepted(dict(source, initialization=MODE_INITIALIZATION)),
            "mode description accepted for a source case")
    print("PASS initial-condition description: 7 checks")
    return 7


class MaskedOracle(Oracle):
    """FND-03 transcription with an E-edge mask from the independent endpoint rule."""

    def __init__(self, cells, spacing, primitives):
        super().__init__(cells, spacing)
        self.masked = set()
        for id in range(3):
            for index in self.indices(id):
                for primitive in primitives:
                    box = [[lo, hi] for lo, hi in zip(primitive["low"], primitive["high"])]
                    if pec_marked(id, index, box, primitive["shape"] == "pec_shell"):
                        self.masked.add((id, index))

    def wall(self, id, index):
        if id < 3 and (id, tuple(index)) in self.masked:
            return True
        return super().wall(id, index)

    def region_maxima(self, e, h, box):
        maxima = [[0.0] * 6 for _ in range(3)]
        for id in range(6):
            half = half_offsets(id)
            array = (e + h)[id]
            for i, j, k in self.indices(id):
                index = (i, j, k)
                inside, outside = True, False
                for t in range(3):
                    doubled = 2 * index[t] + (1 if half[t] else 0)
                    lo, hi = 2 * box[t][0], 2 * box[t][1]
                    if doubled < lo or doubled > hi:
                        outside = True
                    if not (lo < doubled < hi):
                        inside = False
                region = 2 if outside else (0 if inside else 1)
                maxima[region][id] = max(maxima[region][id], abs(array[i][j][k]))
        return maxima

    def mode_fixture(self, meta, e, h):
        a, b, c = cyclic(meta["a"])
        spec = parse_cavity_name(meta["case"])
        mode = cavity_mode(spec["s"], spec["a"], spec["nb"], spec["nc"], spec["q"])
        origin, cavity = meta["origin"], meta["cavity_cells"]
        dt = meta["dt_s"]
        for i, j, k in self.indices(a):
            index = (i, j, k)
            if not (origin[a] <= index[a] < origin[a] + cavity[a] and origin[b] < index[b] < origin[b] + cavity[b]
                    and origin[c] < index[c] < origin[c] + cavity[c]):
                continue
            rb = (index[b] - origin[b]) * self.spacing[b]
            rc = (index[c] - origin[c]) * self.spacing[c]
            e[a][i][j][k] = math.sin(mode["kb"] * rb) * math.sin(mode["kc"] * rc)
        big_omega = 2 / dt * math.sin(mode["omega_d"] * dt / 2)
        factor = math.sin(mode["omega_d"] * dt / 2) / (MU0 * big_omega)
        for id in (3, 4, 5):
            for i, j, k in self.indices(id):
                h[id - 3][i][j][k] = self.curl_e(e, id, i, j, k) * factor


def oracle_against_smoke(root):
    checks = 0
    for name in ("cavity-x-m11-s1", "spectrum-s1", "pec-c1-x", "pec-c3-outside"):
        meta, probes, diagnostics = load_case(root / name)
        oracle = MaskedOracle(meta["cells"], meta["spacing_m"], meta["pec_primitives"])
        dt = meta["dt_s"]
        expected_dt = meta["q"] / (C0 * math.sqrt(sum(1 / d**2 for d in meta["spacing_m"])))
        require(abs(dt / expected_dt - 1) <= 5e-15, "independent CFL")
        masked = [sum(1 for id_, _ in oracle.masked if id_ == id) for id in range(3)]
        require([m - c for m, c in zip(meta["masked_edges"], meta["closure_edges"])] == masked, "independent mask counts")
        e = [oracle.make(id) for id in range(3)]
        h = [oracle.make(id) for id in (3, 4, 5)]
        samples = None
        if meta["kind"] == "mode":
            oracle.mode_fixture(meta, e, h)
        else:
            samples = pulse_samples(dt, V04B_TAU)
            require(len(samples) == meta["pulse_samples"], "pulse length")
        box = [[lo, hi] for lo, hi in zip(meta["pec_primitives"][0]["low"], meta["pec_primitives"][0]["high"])] if meta["region"] else None
        for n in range(meta["steps"] + 1):
            for id, index in oracle.masked:
                require(e[id][index[0]][index[1]][index[2]] == 0, "oracle masked sample")
            if meta["diagnostics"]:
                u, q, maxima = oracle.diagnostics(e, h, dt)
                row = diagnostics[n]
                scale = max(u, 1e-300)
                require(close(float(row["U_J"]), u, scale) and close(float(row["Q_J"]), q, scale), "%s U/Q state %d" % (name, n))
                for id, name_id in enumerate(NAMES):
                    require(close(float(row["max_" + name_id]), maxima[id], maxima[id] or 1e-300), "%s maxima state %d" % (name, n))
                if box is not None:
                    regions = oracle.region_maxima(e, h, box)
                    for r, region in enumerate(REGIONS):
                        for id, name_id in enumerate(NAMES):
                            require(close(float(row[region + "_" + name_id]), regions[r][id], regions[r][id] or 1e-300),
                                    "%s %s maxima state %d" % (name, region, n))
                checks += 3
            for row in probes:
                if int(row["state"]) != n:
                    continue
                id = NAMES.index(row["component"])
                i, j, k = (int(row[x]) for x in "ijk")
                value = (e + h)[id][i][j][k]
                scale = max(abs(v) for plane in (e + h)[id] for column in plane for v in column) or 1e-300
                require(close(float(row["value"]), value, scale), "%s probe %s[%d,%d,%d] state %d" % (name, row["component"], i, j, k, n))
                checks += 1
            if n == meta["steps"]:
                break
            current = None
            if samples is not None and n < len(samples):
                current = [oracle.make(id) for id in range(3)]
                si, sj, sk = meta["source_index"]
                current[2][si][sj][sk] = samples[n]
            oracle.step(e, h, dt, current)
        print("PASS oracle %s: %d states of probes%s within 1e-12" % (
            name, meta["steps"] + 1, "/U/Q/maxima" + ("/regions" if box else "") if meta["diagnostics"] else ""))
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    checks = (synthetic_cavity_checks() + synthetic_spectrum_checks() + synthetic_pec_checks()
              + probe_coverage_checks() + initialization_checks() + check_material_analysis.synthetic_checks())
    if args.app is None:
        print("PASS %d synthetic reduction checks; LIMIT: no solver output examined (pass --app)" % checks)
        return
    require(args.output_root is not None, "--output-root is required with --app")
    args.output_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix="mat02-", dir=str(args.output_root.resolve())))
    command = [str(args.app.resolve()), "--benchmark", "closed-v1", "--suite", "smoke", "--output", str(evidence / "smoke"),
               "--steps", "4"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    require(result.returncode == 0 and result.stderr == "", "Smoke CLI failed: " + result.stdout + result.stderr)
    directories = audit_closed(evidence / "smoke", "smoke")
    require([d.name for d in directories] == sorted(["cavity-x-m11-s1", "pec-c1-x", "pec-c3-outside", "spectrum-s1"]
                                                    + list(check_material_analysis.MATERIAL_SMOKE)), "smoke identity")
    checks += oracle_against_smoke(evidence / "smoke") + 1
    cavity = load_case(evidence / "smoke" / "cavity-x-m11-s1")
    metrics, _ = analyze_cavity(cavity[0], cavity[1], fixed_suite=False)
    require(metrics["status"] == "pass", "four-step smoke cavity measurement: %s" % metrics["failures"])
    print("PASS four-step smoke cavity measurement: continuum error %.9g (cap %.4g), discrete %.3g, amplitude %.3g, magnetic %.3g"
          % (metrics["continuum_error"], metrics["continuum_cap"], metrics["discrete_error"], metrics["max_amplitude_error"],
             metrics["max_magnetic_error"]))
    shell = load_case(evidence / "smoke" / "pec-c1-x")
    metrics, _ = analyze_pec(shell[0], shell[1], shell[2], (cavity[0], cavity[1]), fixed_suite=False)
    require(metrics["status"] == "pass", "smoke shell case: %s" % metrics["failures"])
    print("PASS smoke shell case reproduces the open cavity: %d of %d samples bitwise, max difference %.3g; silent max %.3g"
          % (metrics["equivalence_bitwise"], metrics["equivalence_matched"], metrics["equivalence_max_difference"],
             metrics["max_outside_sample"]))
    outside = load_case(evidence / "smoke" / "pec-c3-outside")
    metrics, _ = analyze_pec(outside[0], outside[1], outside[2], None, fixed_suite=False)
    require(metrics["status"] == "pass", "smoke exterior-source case: %s" % metrics["failures"])
    print("PASS smoke exterior-source case: first driven sample %.17g equals the closed-form deposit %.17g "
          "to %.3g relative" % (metrics["drive_first_state"], metrics["drive_prediction"], metrics["drive_error"]))
    spectrum = load_case(evidence / "smoke" / "spectrum-s1")
    metrics, _ = analyze_spectrum(spectrum[0], spectrum[1], spectrum[2], fixed_suite=False)
    require(metrics["status"] == "pass", "smoke spectrum case: %s" % metrics["failures"])
    checks += 4
    checks += check_material_analysis.oracle_material_smoke(evidence / "smoke")
    checks += check_material_analysis.analyze_material_smoke(evidence / "smoke")
    checks += check_material_analysis.fixture_report_checks(evidence / "smoke")
    print("PASS %d reduction/oracle checks; evidence: %s" % (checks, evidence))
    print("LIMIT: smoke-length runs only; V04-V06 acceptance requires the full fixed suites")


if __name__ == "__main__":
    main()
