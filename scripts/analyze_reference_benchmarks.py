"""REF-05 independent physical analysis of reference-v1 raw artifacts (V01-V03).

Reads emitted metadata/CSV only; no solver operators are imported. Acceptance
values are the fixed FND-04 version-1 thresholds. Every check is recorded and
all outputs are written before the nonzero exit for a failed suite.

Python 3.9+, standard library. Usage:
  python scripts/analyze_reference_benchmarks.py --input ROOT --output DIR
ROOT contains the CLI suite directories ``propagation`` and ``stability`` and an
optional ``resources.json`` from scripts/run_reference_benchmarks.py.
"""
import argparse
import cmath
import csv
import json
import math
import platform
import sys
from pathlib import Path

from check_reference_runs import audit, read_json, C0, ETA0, NAMES
from reference_measurements import fit_harmonic, native_impedance

LAMBDA = 0.3
K = 2*math.pi/LAMBDA
AMPLITUDE = 1.0
CONTINUUM_CAP = {24: 0.0015, 48: 0.000375, 96: 0.00009375}
SENSITIVITY_CAP = 0.003
DISCRETE_LIMIT = 1e-9
AMPLITUDE_LIMIT = 1e-9
RESIDUAL_LIMIT = 1e-9
INACTIVE_LIMIT = 1e-9
IMPEDANCE_LIMIT = 1e-8
ENLARGED_LIMIT = 1e-10
ORDER_RANGE = (1.8, 2.2)
INVARIANT_LIMIT = 1e-8
STABILITY_STEPS = {False: 20000, True: 20008}
MEMORY_BUDGET = 2**31
BLOCK = 1000
AXES = "xyz"
VARIANTS = ("primary", "enlarged", "half-q", "cubic")


def finite(value):
    return isinstance(value, float) and math.isfinite(value)


def expected_case(a, b, p, variant):
    """Independent transcription of the FND-04 v1 propagation geometry."""
    c = 3-a-b
    enlarged, cubic = variant == "enlarged", variant == "cubic"
    cells, spacing = [0, 0, 0], [0.0, 0.0, 0.0]
    cells[a] = (7 if enlarged else 3)*p
    cells[b] = 14*p//3 if enlarged else (3 if cubic else 2)*p
    cells[c] = (4 if enlarged or cubic else 2)*p
    spacing[a] = LAMBDA/p
    spacing[b] = (1 if cubic else 1.5)*spacing[a]
    spacing[c] = (1 if cubic else 2)*spacing[a]
    q = 0.5 if variant == "half-q" else 0.99
    dt = q/(C0*math.sqrt(sum(1/d**2 for d in spacing)))
    steps = math.floor(0.1*LAMBDA/C0/dt)
    name = "prop-%s%s-p%d-%s" % (AXES[a], AXES[b], p, variant)
    return {"case": name, "cells": cells, "spacing_m": spacing, "q": q, "dt_s": dt, "steps": steps}


def expected_propagation_names():
    names = []
    for a in range(3):
        for b in range(3):
            if a == b:
                continue
            for p in (24, 48, 96):
                names.append(expected_case(a, b, p, "primary")["case"])
            for variant in VARIANTS[1:]:
                names.append(expected_case(a, b, 24, variant)["case"])
    return names


def expected_stability_names():
    return ["stable-%s-%s" % (q, kind) for q in ("q50", "q99") for kind in ("initial", "driven")]


def variant_of(name):
    for variant in VARIANTS:
        if name.endswith("-"+variant):
            return variant
    return None


def continuum_cap(p, variant):
    return CONTINUUM_CAP[p] if variant in ("primary", "enlarged") else SENSITIVITY_CAP


def prescribed_line(meta):
    """Sorted v1 native line indices: axial p..2p-1 (+2p when enlarged), transverse centres."""
    cells, a, p = meta["cells"], meta["a"], meta["p"]
    centre = [c//2 for c in cells]
    offset = 2*p if meta["enlarged"] else 0
    result = []
    for axial in range(p, 2*p):
        index = list(centre)
        index[a] = axial+offset
        result.append(tuple(index))
    return sorted(result)


def check_resources(resources, suites):
    """Runner status and measured peak working set of each analyzed suite."""
    failures = []
    if resources is None:
        failures.append("resources.json missing or unreadable; peak memory not measured")
    else:
        for name in suites:
            item = resources.get("suites", {}).get(name)
            if item is None:
                failures.append("no resource record for suite %s" % name)
                continue
            if item.get("status") != 0:
                failures.append("suite %s runner status %s" % (name, item.get("status")))
            peak = item.get("peak_working_set_bytes")
            if not isinstance(peak, int) or peak <= 0:
                failures.append("suite %s peak memory not measured" % name)
            elif peak > MEMORY_BUDGET:
                failures.append("suite %s peak working set %d exceeds %d bytes" % (name, peak, MEMORY_BUDGET))
    return {"suite": "resources", "cases": [], "budget_bytes": MEMORY_BUDGET, "failures": failures,
            "status": "pass" if not failures else "fail"}


def discrete_frequency(dt, spacing_a):
    discrete_k = 2/spacing_a*math.sin(K*spacing_a/2)
    return 2/dt*math.asin(C0*dt*discrete_k/2)


def load_case(directory):
    meta = read_json(directory/"metadata.json")
    with (directory/"probes.csv").open(newline="") as handle:
        probes = list(csv.DictReader(handle))
    with (directory/"diagnostics.csv").open(newline="") as handle:
        diagnostics = list(csv.DictReader(handle))
    return meta, probes, diagnostics


def analyze_propagation(meta, probes, fixed_suite=True):
    """V01/V02 measurements for one case; returns (metrics, trace rows)."""
    a, b, p = meta["a"], meta["b"], meta["p"]
    variant = variant_of(meta["case"])
    dt, steps = meta["dt_s"], meta["steps"]
    c = 3-a-b
    sign = 1 if (a+1) % 3 == b else -1
    active_e, active_h = b, c+3
    failures = []
    metrics = {"case": meta["case"], "a": a, "b": b, "p": p, "variant": variant, "steps": steps,
               "dt_s": dt, "q": meta["q"], "sign": sign, "elapsed_seconds": meta.get("elapsed_seconds"),
               "continuum_cap": continuum_cap(p, variant) if variant is not None else None}
    if variant is None:
        failures.append("unknown variant")
    else:
        expected = expected_case(a, b, p, variant)
        if meta["cells"] != expected["cells"]:
            failures.append("cells %s differ from v1 %s" % (meta["cells"], expected["cells"]))
        if any(abs(x/y-1) > 5e-15 for x, y in zip(meta["spacing_m"], expected["spacing_m"])):
            failures.append("spacing differs from v1 definition")
        if abs(meta["q"]/expected["q"]-1) > 5e-15 or abs(dt/expected["dt_s"]-1) > 5e-15:
            failures.append("q/dt differ from v1 definition")
        if fixed_suite and steps != expected["steps"]:
            failures.append("steps %d differ from v1 %d" % (steps, expected["steps"]))
        if meta["enlarged"] != (variant == "enlarged") or not meta["propagation"] or meta["driven"]:
            failures.append("case flags inconsistent with name")
    if steps < 1:
        failures.append("no evolved state")
    lines = {}
    indices = {}
    for row in probes:
        n, id = int(row["state"]), NAMES.index(row["component"])
        position = float(row[("x_m", "y_m", "z_m")[a]])
        lines.setdefault((n, id), []).append((position, float(row["value"]), float(row["time_s"])))
        indices.setdefault((n, id), []).append(tuple(int(row[key]) for key in ("i", "j", "k")))
    prescribed = prescribed_line(meta)
    fits = {}
    times = {}
    inactive = 0.0
    condition = {"e": 0.0, "h": 0.0}
    residual = {"e": 0.0, "h": 0.0}
    amplitude_error = {"e": 0.0, "h": 0.0}
    for n in range(steps+1):
        for id in range(6):
            samples = lines.get((n, id), [])
            if len(samples) != p:
                failures.append("state %d %s has %d native samples, expected %d" % (n, NAMES[id], len(samples), p))
                continue
            if sorted(indices[n, id]) != prescribed:
                failures.append("state %d %s samples are not the prescribed native line" % (n, NAMES[id]))
            if len({t for _, _, t in samples}) != 1:
                failures.append("state %d %s mixes sample times" % (n, NAMES[id]))
            if id not in (active_e, active_h):
                scale = 1.0 if id < 3 else ETA0
                inactive = max(inactive, max(abs(v)*scale for _, v, _ in samples))
                continue
            family = "e" if id == active_e else "h"
            scale = 1.0 if family == "e" else ETA0
            try:
                coefficient, fit_residual, cond = fit_harmonic(
                    [(x, v) for x, v, _ in samples], K, p, 0.5*AMPLITUDE/scale)
            except ValueError as error:
                failures.append("state %d %s fit rejected: %s" % (n, NAMES[id], error))
                continue
            fits[n, family] = coefficient
            times[n, family] = samples[0][2]
            condition[family] = max(condition[family], cond)
            residual[family] = max(residual[family], fit_residual*scale/AMPLITUDE)
            amplitude_error[family] = max(amplitude_error[family], abs(abs(coefficient)*scale/AMPLITUDE-1))
    omega_m = None
    if (0, "e") in fits and (steps, "e") in fits:
        omega_m = cmath.phase(fits[steps, "e"]/fits[0, "e"])/(steps*dt)
        if not omega_m > 0:
            failures.append("measured frequency not positive")
    else:
        failures.append("missing initial/final active E fit")
    omega_d = discrete_frequency(dt, meta["spacing_m"][a])
    metrics["omega_discrete"] = omega_d
    metrics["omega_measured"] = omega_m
    metrics["predicted_continuum_error"] = abs(omega_d/(K*C0)-1)
    trace = []
    impedance_error = 0.0
    final_impedance = None
    if omega_m is not None and omega_m > 0:
        metrics["continuum_error"] = abs(omega_m/(K*C0)-1)
        metrics["discrete_error"] = abs(omega_m/omega_d-1)
        for n in range(steps+1):
            if (n, "e") not in fits or (n, "h") not in fits:
                continue
            try:
                z = native_impedance(fits[n, "e"], fits[n, "h"], times[n, "e"], times[n, "h"],
                                     omega_m, 0.5*AMPLITUDE/ETA0)
            except ValueError as error:
                failures.append("state %d impedance rejected: %s" % (n, error))
                continue
            error = abs(z/(sign*ETA0)-1)
            impedance_error = max(impedance_error, error)
            final_impedance = z
            trace.append({"case": meta["case"], "state": n, "e_time_s": times[n, "e"], "h_time_s": times[n, "h"],
                          "ce_re": fits[n, "e"].real, "ce_im": fits[n, "e"].imag,
                          "ch_re": fits[n, "h"].real, "ch_im": fits[n, "h"].imag,
                          "z_re": z.real, "z_im": z.imag, "z_error": error})
        if metrics["continuum_cap"] is not None and metrics["continuum_error"] > metrics["continuum_cap"]:
            failures.append("continuum phase-speed error exceeds cap")
        if metrics["discrete_error"] > DISCRETE_LIMIT:
            failures.append("discrete frequency error exceeds limit")
    else:
        metrics["continuum_error"] = metrics["discrete_error"] = None
    metrics.update({
        "max_amplitude_error_e": amplitude_error["e"], "max_amplitude_error_h": amplitude_error["h"],
        "max_residual_e": residual["e"], "max_residual_h": residual["h"],
        "max_condition_e": condition["e"], "max_condition_h": condition["h"],
        "max_inactive": inactive, "max_impedance_error": impedance_error,
        "final_impedance_ohm": None if final_impedance is None else [final_impedance.real, final_impedance.imag],
        "reference_impedance_ohm": sign*ETA0})
    if amplitude_error["e"] > AMPLITUDE_LIMIT or amplitude_error["h"] > AMPLITUDE_LIMIT:
        failures.append("fitted amplitude error exceeds limit")
    if residual["e"] > RESIDUAL_LIMIT or residual["h"] > RESIDUAL_LIMIT:
        failures.append("fit residual exceeds limit")
    if inactive > INACTIVE_LIMIT:
        failures.append("inactive line samples exceed limit")
    if impedance_error > IMPEDANCE_LIMIT:
        failures.append("complex impedance error exceeds limit")
    if len(trace) != steps+1:
        failures.append("impedance not evaluated at every state")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace


def compare_enlarged(primary, enlarged):
    """Enlarged-domain sample comparison after the 2-lambda origin/probe shift."""
    meta_p, probes_p = primary
    meta_e, probes_e = enlarged
    failures = []
    shift = []
    for d_p, d_e in zip(meta_p["spacing_m"], meta_e["spacing_m"]):
        if d_p != d_e:
            failures.append("spacing differs between primary and enlarged")
        cells = 2*LAMBDA/d_p
        if abs(cells-round(cells)) > 1e-9:
            failures.append("2-lambda shift is not an integer cell count")
        shift.append(int(round(cells)))
    if meta_p["steps"] != meta_e["steps"] or meta_p["dt_s"] != meta_e["dt_s"]:
        failures.append("steps/dt differ between primary and enlarged")
    reference = {}
    for row in probes_p:
        key = (int(row["state"]), row["component"], int(row["i"]), int(row["j"]), int(row["k"]))
        reference[key] = (float(row["value"]), [float(row[n]) for n in ("x_m", "y_m", "z_m")])
    worst = 0.0
    matched = 0
    for row in probes_e:
        key = (int(row["state"]), row["component"], int(row["i"])-shift[0],
               int(row["j"])-shift[1], int(row["k"])-shift[2])
        if key not in reference:
            failures.append("enlarged sample %s has no primary match" % (key,))
            continue
        matched += 1
        value, position = reference[key]
        scale = 1.0 if row["component"][0] == "E" else ETA0
        worst = max(worst, abs(float(row["value"])-value)*scale/AMPLITUDE)
        for axis, name in enumerate(("x_m", "y_m", "z_m")):
            expected = position[axis]+2*LAMBDA
            if abs(float(row[name])-expected) > 5e-15*max(abs(expected), meta_p["spacing_m"][axis]):
                failures.append("enlarged coordinate %s of %s is not shifted by 2 lambda" % (name, key))
    if matched != len(reference) or not reference:
        failures.append("matched %d of %d primary samples" % (matched, len(reference)))
    if worst > ENLARGED_LIMIT:
        failures.append("enlarged/primary sample difference exceeds limit")
    return {"primary": meta_p["case"], "enlarged": meta_e["case"], "shift_cells": shift,
            "matched_samples": matched, "max_normalized_difference": worst, "limit": ENLARGED_LIMIT,
            "failures": failures, "status": "pass" if not failures else "fail"}


def refinement(errors):
    """errors: {24: e, 48: e, 96: e} continuum errors of one axis/polarization."""
    failures = []
    sequence = [errors.get(p) for p in (24, 48, 96)]
    if any(e is None or not finite(e) or e <= 0 for e in sequence):
        failures.append("missing/nonpositive continuum error")
        orders = [None, None]
    else:
        if not sequence[0] > sequence[1] > sequence[2]:
            failures.append("continuum errors not strictly decreasing")
        orders = [math.log2(sequence[0]/sequence[1]), math.log2(sequence[1]/sequence[2])]
        if any(not ORDER_RANGE[0] <= o <= ORDER_RANGE[1] for o in orders):
            failures.append("observed order outside [1.8,2.2]")
    return {"errors": sequence, "orders": orders, "failures": failures,
            "status": "pass" if not failures else "fail"}


def analyze_stability(meta, diagnostics, probes=(), fixed_suite=True):
    """V03 long-time invariant/bound checks for one case; returns (metrics, blocks)."""
    q, driven, steps = meta["q"], meta["driven"], meta["steps"]
    n_ref = 8 if driven else 0
    failures = []
    metrics = {"case": meta["case"], "q": q, "driven": driven, "steps": steps, "dt_s": meta["dt_s"],
               "reference_state": n_ref, "elapsed_seconds": meta.get("elapsed_seconds")}
    if meta["cells"] != [12, 14, 16] or meta["spacing_m"] != [0.01, 0.015, 0.02]:
        failures.append("grid differs from v1 stability fixture")
    if (abs(q-(0.5 if "q50" in meta["case"] else 0.99)) > 5e-15 or meta["propagation"]
            or meta["driven"] != ("driven" in meta["case"])):
        failures.append("case flags/q inconsistent with name")
    if meta.get("diagnostic_reference_state") != n_ref:
        failures.append("metadata reference state differs from v1")
    if fixed_suite and steps != STABILITY_STEPS[driven]:
        failures.append("steps %d differ from v1 %d" % (steps, STABILITY_STEPS[driven]))
    rows = []
    first_nonfinite = None
    for index, row in enumerate(diagnostics):
        values = {key: float(value) for key, value in row.items()}
        if int(values["state"]) != index:
            failures.append("diagnostic state %d out of order" % index)
        if first_nonfinite is None and any(not math.isfinite(v) for v in values.values()):
            first_nonfinite = {"state": index, "columns": [k for k, v in values.items() if not math.isfinite(v)]}
        rows.append(values)
    metrics["first_nonfinite"] = first_nonfinite
    if first_nonfinite is not None:
        failures.append("nonfinite diagnostic at state %d" % first_nonfinite["state"])
    if len(rows) != steps+1:
        failures.append("expected %d diagnostic states, found %d" % (steps+1, len(rows)))
    probe_max = 0.0
    for row in probes:
        value = float(row["value"])
        if not math.isfinite(value):
            failures.append("nonfinite probe sample at state %s" % row["state"])
            break
        probe_max = max(probe_max, abs(value)*(1.0 if row["component"][0] == "E" else ETA0))
    metrics["max_normalized_probe"] = probe_max
    blocks = []
    if len(rows) > n_ref and first_nonfinite is None:
        u_ref, q_ref = rows[n_ref]["U_J"], rows[n_ref]["Q_J"]
        metrics["U_reference_J"], metrics["Q_reference_J"] = u_ref, q_ref
        if not (u_ref > 0 and q_ref > 0):
            failures.append("nonpositive reference diagnostics")
        else:
            ratio_limit = (1+q)/(1-q)*(1+INVARIANT_LIMIT)
            worst = (0.0, n_ref)
            ratio_min, ratio_max = math.inf, -math.inf
            maxima_all = {name: 0.0 for name in NAMES}
            maxima_free = {name: 0.0 for name in NAMES}
            bound_violation = None
            complete_blocks = (len(rows)-1-n_ref)//BLOCK
            for n, row in enumerate(rows):
                for name in NAMES:
                    maxima_all[name] = max(maxima_all[name], row["max_"+name])
                if n < n_ref:
                    continue
                for name in NAMES:
                    maxima_free[name] = max(maxima_free[name], row["max_"+name])
                u, qn = row["U_J"], row["Q_J"]
                invariant = abs(qn-q_ref)/q_ref
                if invariant > worst[0]:
                    worst = (invariant, n)
                ratio = u/u_ref
                ratio_min, ratio_max = min(ratio_min, ratio), max(ratio_max, ratio)
                if bound_violation is None and not (ratio <= ratio_limit
                                                    and qn >= (1-q)*u-INVARIANT_LIMIT*q_ref
                                                    and qn <= (1+q)*u+INVARIANT_LIMIT*q_ref):
                    bound_violation = n
                block = (n-n_ref-1)//BLOCK
                if n > n_ref and block < complete_blocks:
                    if len(blocks) <= block:
                        blocks.append({"case": meta["case"], "block": block, "first_state": n, "last_state": n,
                                       "max_invariant_error": 0.0, "min_U_ratio": math.inf,
                                       "max_U_ratio": -math.inf, **{"max_"+name: 0.0 for name in NAMES}})
                    entry = blocks[block]
                    entry["last_state"] = n
                    entry["max_invariant_error"] = max(entry["max_invariant_error"], invariant)
                    entry["min_U_ratio"] = min(entry["min_U_ratio"], ratio)
                    entry["max_U_ratio"] = max(entry["max_U_ratio"], ratio)
                    for name in NAMES:
                        entry["max_"+name] = max(entry["max_"+name], row["max_"+name])
            metrics.update({"max_invariant_error": worst[0], "max_invariant_error_state": worst[1],
                            "min_U_ratio": ratio_min, "max_U_ratio": ratio_max, "U_ratio_limit": ratio_limit,
                            "max_abs_field_all_states": maxima_all, "max_abs_field_source_free": maxima_free,
                            "bound_violation_state": bound_violation, "source_free_blocks": len(blocks)})
            if worst[0] > INVARIANT_LIMIT:
                failures.append("invariant drift exceeds 1e-8 at state %d" % worst[1])
            if bound_violation is not None:
                failures.append("energy bound violated at state %d" % bound_violation)
            if fixed_suite and len(blocks) != (STABILITY_STEPS[driven]-n_ref)//BLOCK:
                failures.append("unexpected source-free block count %d" % len(blocks))
            if driven and (rows[0]["U_J"] != 0 or rows[0]["Q_J"] != 0):
                failures.append("driven case does not start from zero fields")
            if not driven and rows[0]["Q_J"] != rows[0]["U_J"]:
                failures.append("initial zero-H identity Q_0=U_0 violated")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, blocks


def analyze_suite_propagation(root):
    result = {"suite": "propagation", "root": str(root), "cases": [], "enlarged": [], "refinement": [],
              "failures": []}
    trace = []
    try:
        directories = audit(root)
    except Exception as error:  # retained as evidence; analysis continues on readable cases
        result["failures"].append("artifact audit: %s" % error)
        directories = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if sorted(d.name for d in directories) != sorted(expected_propagation_names()):
        result["failures"].append("suite enumeration differs from the 36 v1 configurations")
    loaded = {}
    for directory in directories:
        try:
            meta, probes, _ = load_case(directory)
            metrics, rows = analyze_propagation(meta, probes)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail",
                                    "failures": ["unreadable: %s" % error]})
            continue
        loaded[meta["case"]] = (meta, probes)
        result["cases"].append(metrics)
        trace.extend(rows)
    by_name = {m["case"]: m for m in result["cases"]}
    for a in range(3):
        for b in range(3):
            if a == b:
                continue
            pair = AXES[a]+AXES[b]
            primary = "prop-%s-p24-primary" % pair
            enlarged = "prop-%s-p24-enlarged" % pair
            if primary in loaded and enlarged in loaded:
                result["enlarged"].append(compare_enlarged(loaded[primary], loaded[enlarged]))
            else:
                result["enlarged"].append({"primary": primary, "enlarged": enlarged, "status": "fail",
                                           "failures": ["missing case output"]})
            errors = {p: by_name.get("prop-%s-p%d-primary" % (pair, p), {}).get("continuum_error")
                      for p in (24, 48, 96)}
            entry = refinement(errors)
            entry["pair"] = pair
            result["refinement"].append(entry)
    result["status"] = "pass" if not result["failures"] and all(
        item["status"] == "pass" for key in ("cases", "enlarged", "refinement") for item in result[key]) else "fail"
    return result, trace


def analyze_suite_stability(root):
    result = {"suite": "stability", "root": str(root), "cases": [], "failures": []}
    blocks = []
    try:
        directories = audit(root)
    except Exception as error:
        result["failures"].append("artifact audit: %s" % error)
        directories = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if sorted(d.name for d in directories) != sorted(expected_stability_names()):
        result["failures"].append("suite enumeration differs from the four v1 configurations")
    for directory in directories:
        try:
            meta, probes, diagnostics = load_case(directory)
            metrics, rows = analyze_stability(meta, diagnostics, probes)
        except Exception as error:
            result["cases"].append({"case": directory.name, "status": "fail",
                                    "failures": ["unreadable: %s" % error]})
            continue
        result["cases"].append(metrics)
        blocks.extend(rows)
    result["status"] = "pass" if not result["failures"] and all(
        c["status"] == "pass" for c in result["cases"]) else "fail"
    return result, blocks


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
    lines = ["# REF-05 reference-v1 physical analysis", "",
             "Generated by scripts/analyze_reference_benchmarks.py; thresholds are the fixed FND-04 v1 values.",
             "Overall status: **%s**." % summary["status"].upper(), ""]
    for suite in summary["suites"]:
        lines.append("## Suite %s: %s" % (suite["suite"], suite["status"].upper()))
        lines.append("")
        for failure in suite["failures"]:
            lines.append("- SUITE FAILURE: %s" % failure)
        if suite["suite"] == "propagation":
            lines += ["", "| Case | N | omega_m/(k c0)-1 | cap | omega_m/omega_d-1 | amp E/H | resid E/H | inactive"
                      " | Z error | Z final (ohm) | s*eta0 | status |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for c in suite["cases"]:
                z = c.get("final_impedance_ohm")
                lines.append("| %s | %s | %s | %s | %s | %s / %s | %s / %s | %s | %s | %s | %s | %s |" % (
                    c["case"], c.get("steps"), fmt(c.get("continuum_error"), 9), fmt(c.get("continuum_cap")),
                    fmt(c.get("discrete_error"), 3), fmt(c.get("max_amplitude_error_e"), 3),
                    fmt(c.get("max_amplitude_error_h"), 3), fmt(c.get("max_residual_e"), 3),
                    fmt(c.get("max_residual_h"), 3), fmt(c.get("max_inactive"), 3),
                    fmt(c.get("max_impedance_error"), 3), "n/a" if z is None else "%.9g%+.3gj" % (z[0], z[1]),
                    fmt(c.get("reference_impedance_ohm"), 12), c["status"]))
            lines += ["", "| Pair | e24 | e48 | e96 | order 24/48 | order 48/96 | status |",
                      "| --- | --- | --- | --- | --- | --- | --- |"]
            for r in suite["refinement"]:
                lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                    r["pair"], *[fmt(e, 9) for e in r["errors"]], *[fmt(o, 9) for o in r["orders"]], r["status"]))
            lines += ["", "| Primary | Enlarged | shift cells | matched | max diff | status |",
                      "| --- | --- | --- | --- | --- | --- |"]
            for e in suite["enlarged"]:
                lines.append("| %s | %s | %s | %s | %s | %s |" % (
                    e["primary"], e["enlarged"], e.get("shift_cells"), e.get("matched_samples"),
                    fmt(e.get("max_normalized_difference"), 3), e["status"]))
        elif suite["suite"] == "stability":
            lines += ["", "| Case | steps | n_ref | max abs(Q-Qref)/Qref (state) | min/max U/Uref | limit | blocks"
                      " | max abs E / eta0 abs H source-free | status |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for c in suite["cases"]:
                free = c.get("max_abs_field_source_free") or {}
                e_max = max([free.get(n, 0.0) for n in NAMES[:3]] or [0.0])
                h_max = max([free.get(n, 0.0) for n in NAMES[3:]] or [0.0])*ETA0
                lines.append("| %s | %s | %s | %s (%s) | %s / %s | %s | %s | %s / %s | %s |" % (
                    c["case"], c.get("steps"), c.get("reference_state"), fmt(c.get("max_invariant_error"), 3),
                    c.get("max_invariant_error_state"), fmt(c.get("min_U_ratio"), 6), fmt(c.get("max_U_ratio"), 6),
                    fmt(c.get("U_ratio_limit"), 6), c.get("source_free_blocks"), fmt(e_max, 4), fmt(h_max, 4),
                    c["status"]))
        for c in suite["cases"]:
            for failure in c.get("failures", []):
                lines.append("- FAIL %s: %s" % (c["case"], failure))
        for key in ("enlarged", "refinement"):
            for item in suite.get(key, []):
                for failure in item.get("failures", []):
                    lines.append("- FAIL %s %s: %s" % (key, item.get("pair") or item.get("enlarged"), failure))
        lines.append("")
    if summary.get("resources"):
        lines += ["## Measured resources", "", "| Suite | status | elapsed s | peak working set bytes |",
                  "| --- | --- | --- | --- |"]
        for name, item in summary["resources"].get("suites", {}).items():
            lines.append("| %s | %s | %s | %s |" % (name, item.get("status"), fmt(item.get("elapsed_seconds"), 5),
                                                    item.get("peak_working_set_bytes")))
        lines.append("")
    lines += ["Per-state fits are in propagation-trace.csv; 1,000-step block maxima are in stability-blocks.csv.",
              "A passing analysis supports only the declared axis-aligned vacuum/closed-grid envelope."]
    return "\n".join(lines)+"\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", choices=("all", "propagation", "stability"), default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": "reference-v1-analysis-1", "input": str(args.input.resolve()), "suites": [],
               "thresholds": {"continuum_cap": CONTINUUM_CAP, "sensitivity_cap": SENSITIVITY_CAP,
                              "discrete": DISCRETE_LIMIT, "amplitude": AMPLITUDE_LIMIT,
                              "residual": RESIDUAL_LIMIT, "inactive": INACTIVE_LIMIT,
                              "impedance": IMPEDANCE_LIMIT, "enlarged": ENLARGED_LIMIT,
                              "order_range": ORDER_RANGE, "invariant": INVARIANT_LIMIT},
               "analysis_environment": {"python": sys.version.split()[0], "platform": platform.platform()}}
    trace, blocks = [], []
    if args.suite in ("all", "propagation"):
        result, rows = analyze_suite_propagation(args.input/"propagation")
        summary["suites"].append(result)
        trace = rows
    if args.suite in ("all", "stability"):
        result, rows = analyze_suite_stability(args.input/"stability")
        summary["suites"].append(result)
        blocks = rows
    resources = args.input/"resources.json"
    try:
        summary["resources"] = read_json(resources) if resources.is_file() else None
    except Exception as error:
        summary["resources"] = None
        summary["resources_error"] = str(error)
    summary["suites"].append(check_resources(summary["resources"], [s["suite"] for s in summary["suites"]]))
    source_snapshots = set()
    provenance_failures = []
    for suite in summary["suites"]:
        for case in suite.get("cases", []):
            path = Path(suite["root"])/case["case"]/"metadata.json"
            if not path.is_file():
                continue
            try:
                source_snapshots.add(read_json(path)["source_snapshot_sha256"])
            except Exception as error:
                provenance_failures.append("%s: unreadable metadata (%s)" % (case["case"], error))
    summary["source_snapshots"] = sorted(source_snapshots)
    if len(source_snapshots) != 1:
        provenance_failures.append("cases come from %d source snapshots" % len(source_snapshots))
    if provenance_failures:
        summary["suites"].append({"suite": "provenance", "cases": [], "status": "fail",
                                  "failures": provenance_failures})
    summary["status"] = "pass" if summary["suites"] and all(
        s["status"] == "pass" for s in summary["suites"]) else "fail"
    (args.output/"metrics.json").write_text(json.dumps(summary, indent=1)+"\n")
    write_csv(args.output/"propagation-trace.csv", trace)
    write_csv(args.output/"stability-blocks.csv", blocks)
    (args.output/"report.md").write_text(report(summary))
    print(report(summary))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
