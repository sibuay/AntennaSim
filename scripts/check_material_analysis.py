"""MAT-03 reduction validation before V05/V06 physical results are accepted.

Imported by scripts/check_closed_analysis.py (CTest reference.closed_analysis).

1. Synthetic pass/fault-detection checks of the V05-A/B/C and V06-A/B
   reductions (material_reductions.py) on series built from the MAT-01
   closed forms, and of the coefficient-table audit against a brute-force
   edge enumeration (no solver output).
2. A pure-Python oracle: the FND-03 transcription extended with per-cell
   materials averaged independently onto the edges, the lossy coefficient
   update and the dissipation D, plus independent transcriptions of the wave,
   sheet, slab and modular fixtures. With --app it must reproduce every probe
   and U/Q/D/maxima of the closed-v1 material smoke cases within 1e-12.

Python 3.9+, standard library. No production operator is imported.
"""
import cmath
import json
import math
import shutil

import material_reductions as mr
from analyze_closed_benchmarks import audit_closed, coefficient_audit, expected_materials, load_case, update_edges
from check_reference_analysis import Oracle, close, half_offsets, require
from check_material_benchmarks import (C0, MU0, EPS0, ETA0, PI, LAMBDA, EPS_R, v01_like, kappa, discrete_omega,
                                       lossy_step_root, v05b_geometry, reduced_oracle, gaussian_pulse, v05c_geometry)

NAMES = mr.NAMES
AXES = mr.AXES


def has_failure(metrics, text):
    return any(text in failure for failure in metrics["failures"])


def probe_row(n, id, index, spacing, dt, value):
    half = half_offsets(id)
    position = [(index[t] + half[t]) * spacing[t] for t in range(3)]
    return {"state": str(n), "component": NAMES[id], "i": str(index[0]), "j": str(index[1]), "k": str(index[2]),
            "x_m": repr(position[0]), "y_m": repr(position[1]), "z_m": repr(position[2]),
            "time_s": repr((n - (0 if id < 3 else 0.5)) * dt), "value": repr(value)}


# ---- V05-A / V06-A ---------------------------------------------------------------
def lossy_h(dt, big_k, z):
    """H phasor at -dt/2 per unit E amplitude: hhat z^(-1/2), hhat = (i dt K/mu0)/(z^(1/2)-z^(-1/2))."""
    root = z ** 0.5
    return (1j * dt * big_k / MU0) / (root - 1 / root) / root


def synthetic_wave(a, b, p, sigma=0.0, omega_factor=1.0, amplitude_error=0.0, h_sign=1, h_phase=0.0, inactive=0.0,
                   decay_factor=1.0, lossless_start=False, amplitude=1.0, steps=None, h_amplitude_error=0.0,
                   kink=0.0, phase_factor=1.0):
    """``kink`` adds a non-harmonic offset to one active E sample (fit residual);
    ``phase_factor`` scales the phase of the lossy growth factor (V06-A phase)."""
    spacing_role, cells_role, dt, steps_v1, k, omega_d = v01_like(p, EPS_R)
    c = 3 - a - b
    roles = (a, b, c)
    cells, spacing = mr.role_list(roles, list(cells_role)), mr.role_list(roles, list(spacing_role))
    steps = steps_v1 if steps is None else steps
    name = ("dielectric-%s%s-p%d" % (AXES[a], AXES[b], p) if sigma == 0
            else "lossy-%s%s-p%d-%s" % (AXES[a], AXES[b], p, mr.SIGMA_LABEL[sigma]))
    meta = {"case": name, "kind": "wave", "roles": list(roles), "p": p, "eps_r": EPS_R, "sigma_S_per_m": sigma,
            "i_int": 0, "cells": cells, "spacing_m": spacing, "dt_s": dt, "q": 0.99, "steps": steps,
            "elapsed_seconds": 0.0}
    big_k = kappa(k, spacing_role[0])
    eps = EPS_R * EPS0
    if sigma == 0:
        z = cmath.exp(1j * omega_d * omega_factor * dt)
        h = math.sqrt(EPS_R) / ETA0 / z ** 0.5
    else:
        z = lossy_step_root(dt, big_k, eps, sigma) * decay_factor
        z = abs(z) * cmath.exp(1j * cmath.phase(z) * phase_factor)
        h = lossy_h(dt, big_k, z)
    h *= 1 + h_amplitude_error
    sign = 1 if (a + 1) % 3 == b else -1
    e_amplitudes = [amplitude * (1 + amplitude_error) * z ** n for n in range(steps + 1)]
    if lossless_start:
        x = sigma * dt / (2 * eps)
        ca, cb = (1 - x) / (1 + x), (dt / eps) / (1 + x)
        z0 = cmath.exp(1j * discrete_omega(dt, big_k, EPS_R))
        hm, e = lossy_h(dt, big_k, z0), 1 + 0j
        e_amplitudes = [e]
        for _ in range(steps):
            hm += (1j * dt * big_k / MU0) * e
            e = ca * e + cb * 1j * big_k * hm
            e_amplitudes.append(e)
    centre = [n // 2 for n in cells]
    rows = []
    for n in range(steps + 1):
        for id in range(6):
            for axial in range(p, 2 * p):
                index = list(centre)
                index[a] = axial
                half = half_offsets(id)
                r = (index[a] + half[a]) * spacing[a]
                if id == b:
                    value = (e_amplitudes[n] * cmath.exp(-1j * k * r)).real + (kink if (n, axial) == (1, p + 3) else 0.0)
                elif id == c + 3:
                    value = sign * h_sign * (h * z ** n * cmath.exp(-1j * k * r + 1j * h_phase)).real
                else:
                    value = inactive if (n == 1 and axial == p) else 0.0
                rows.append(probe_row(n, id, index, spacing, dt, value))
    return meta, rows


def synthetic_wave_checks():
    checks, worst = 0, 0.0
    for a, b in mr.ORDERINGS:
        for p in (24, 48, 96):
            meta, rows = synthetic_wave(a, b, p)
            metrics, _ = mr.analyze_wave(meta, rows)
            require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
            worst = max(worst, abs(metrics["continuum_error"] - metrics["predicted_continuum_error"]),
                        metrics["discrete_error"], metrics["max_impedance_error"])
            checks += 1
    for sigma in mr.V06_SIGMAS:
        for a, b in mr.ORDERINGS[:2]:
            for p in (24, 48):
                meta, rows = synthetic_wave(a, b, p, sigma)
                metrics, _ = mr.analyze_wave(meta, rows)
                require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
                worst = max(worst, metrics["max_discrete_ratio_error"],
                            abs(metrics["decay_error"] - metrics["predicted_decay_error"]),
                            abs(metrics["phase_error"] - metrics["predicted_phase_error"]))
                checks += 1
        meta, rows = synthetic_wave(0, 1, 96, sigma)
        require(mr.analyze_wave(meta, rows)[0]["status"] == "pass", "synthetic lossy p96")
        checks += 1
    require(worst <= 1e-11, "synthetic V05-A/V06-A estimator precision %.3g" % worst)
    faults = [
        (dict(omega_factor=1 + 3e-9), "discrete frequency error"),
        (dict(amplitude_error=3e-9), "fitted amplitude error"),
        (dict(h_sign=-1), "complex impedance error"),
        (dict(h_phase=1e-6), "complex impedance error"),
        (dict(inactive=1e-8), "inactive line samples"),
        (dict(omega_factor=0.99), "continuum phase-speed error"),
        (dict(steps=3), "differ from v1"),
        # Added in the 2026-09-25 review: checks that no earlier fault exercised,
        # and NaN inputs that once vanished from a maximum.
        (dict(h_amplitude_error=3e-9), "fitted amplitude error"),
        (dict(kink=1e-8), "fit residual exceeds"),
        (dict(inactive=math.nan), "inactive line samples"),
        (dict(dt_nan=True), "q/dt differ"),
    ]
    for kwargs, text in faults:
        dt_nan = kwargs.pop("dt_nan", False)
        meta, rows = synthetic_wave(1, 2, 24, **kwargs)
        if dt_nan:
            meta["dt_s"] = math.nan
        metrics, _ = mr.analyze_wave(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected V05-A fault: " + text)
        checks += 1
    x = 0.1 * v01_like(24, EPS_R)[2] / (2 * EPS_R * EPS0)
    lossy_faults = [
        (dict(decay_factor=math.exp(-2e-3 * x)), "decay-rate error exceeds cap"),
        (dict(decay_factor=1 + 3e-9), "per-step ratio differs"),
        (dict(lossless_start=True), "per-step ratio differs"),
        (dict(amplitude=0.4), "fit rejected"),
        (dict(inactive=1e-8), "inactive line samples"),
        (dict(phase_factor=0.998), "phase error exceeds cap"),
        (dict(kink=1e-8), "fit residual exceeds"),
        # ordering xz: the active H line is Hy; the V01 floor 0.5 A/eta rejects it
        (dict(h_amplitude_error=-0.6), "Hy fit rejected"),
    ]
    for kwargs, text in lossy_faults:
        meta, rows = synthetic_wave(0, 2, 24, 0.1, **kwargs)
        metrics, _ = mr.analyze_wave(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected V06-A fault: " + text)
        checks += 1
    meta, rows = synthetic_wave(0, 1, 24, 0.1, steps=4)
    require(mr.analyze_wave(meta, rows, fixed_suite=False)[0]["status"] == "pass", "smoke-length lossy synthetic")
    meta, rows = synthetic_wave(0, 1, 24, 0.1)
    meta = dict(meta, sigma_S_per_m=0.01)
    require(has_failure(mr.analyze_wave(meta, rows)[0], "case flags"), "wrong conductivity metadata undetected")
    checks += 2
    predicted = {p: mr.analyze_wave(*synthetic_wave(0, 1, p))[0]["continuum_error"] for p in (24, 48, 96)}
    require(mr.refinement(predicted, (24, 48, 96))["status"] == "pass", "V05-A refinement pass")
    require(mr.refinement({24: 2e-3, 48: 2e-3, 96: 5e-4}, (24, 48, 96))["status"] == "fail", "flat refinement")
    require(mr.refinement({24: 2e-3, 48: 3e-4}, (24, 48))["status"] == "fail", "two-level order fault")
    checks += 3
    print("PASS synthetic V05-A/V06-A reductions: %d checks; worst estimator deviation %.3g" % (checks, worst))
    return checks


# ---- V05-B -----------------------------------------------------------------------
_ORACLE_SERIES = {}


def reduced_series(p):
    if p not in _ORACLE_SERIES:
        _ORACLE_SERIES[p] = reduced_oracle(v05b_geometry(p))
    return _ORACLE_SERIES[p]


def purity_states(s1):
    """(state of the peak amplitude, a quiet state after arrival with |a| < 1e-5 peak)."""
    peak = max(abs(v) for v in s1)
    strong = max(range(len(s1)), key=lambda n: abs(s1[n]))
    quiet = next(n for n in range(strong, len(s1)) if 0 < abs(s1[n]) < 1e-5 * peak)
    return peak, strong, quiet


def synthetic_interface(a, p, reflect_shift=False, reflect_scale=1.0, transmit_shift=False, plane_fault=False,
                        purity=None, scale=1.0, meta_gate=0, drop=None, nan_at=None):
    """``purity`` injects TE_2 content: ("strong", c) adds c*a_n at the peak state;
    ("quiet", c) adds c*peak at a state whose amplitude is below 1e-5 of the peak."""
    g = v05b_geometry(p)
    roles = (a, (a + 1) % 3, (a + 2) % 3)
    cells, spacing = mr.role_list(roles, list(g["cells"])), mr.role_list(roles, list(g["spacing"]))
    dt, steps, gate, n_c = g["dt"], g["steps"], g["gate"], g["cells"][2]
    meta = {"case": "interface-%s-p%d" % (AXES[a], p), "kind": "sheet", "roles": list(roles), "p": p,
            "eps_r": EPS_R, "sigma_S_per_m": 0.0, "i_int": g["i_int"], "i_src": g["i_src"], "i_p1": g["i_p1"],
            "i_p2": g["i_p2"], "gate": gate + meta_gate, "cells": cells, "spacing_m": spacing, "dt_s": dt, "q": 0.99,
            "steps": steps, "elapsed_seconds": 0.0}
    p1, p2 = reduced_series(p)
    s1 = [0.0] + [v * scale for v in p1]
    s2 = [0.0] + [v * scale for v in p2]
    if reflect_shift:
        s1 = s1[:gate + 1] + [s1[n - 1] for n in range(gate + 1, steps + 1)]
    if reflect_scale != 1.0:
        s1 = s1[:gate + 1] + [v * reflect_scale for v in s1[gate + 1:]]
    if transmit_shift:
        s2 = [0.0] + s2[:-1]
    b = roles[1]
    extra = {}
    if purity is not None:
        peak, strong, quiet = purity_states(s1)
        extra = {strong: purity[1] * s1[strong]} if purity[0] == "strong" else {quiet: purity[1] * peak}
    rows = []
    for n in range(steps + 1):
        for k in range(n_c + 1):
            value = s1[n] * math.sin(PI * k / n_c) + extra.get(n, 0.0) * math.sin(2 * PI * k / n_c)
            if nan_at == (n, k):
                value = math.nan
            rows.append(probe_row(n, b, mr.to_xyz(roles, (g["i_p1"], 0, k)), spacing, dt, value))
        p2b = s2[n] if not (plane_fault in (True, "p2b") and n == gate) else math.nextafter(s2[n], math.inf)
        p1b = s1[n] if not (plane_fault == "p1b" and n == gate) else math.nextafter(s1[n], math.inf)
        for role_index, value in (((g["i_p2"], 0, n_c // 2), s2[n]), ((g["i_p1"], 1, n_c // 2), p1b),
                                  ((g["i_p2"], 1, n_c // 2), p2b)):
            rows.append(probe_row(n, b, mr.to_xyz(roles, role_index), spacing, dt, value))
    if drop is not None:
        del rows[drop]
    return meta, rows


def synthetic_interface_checks():
    checks = 0
    series = {}
    for a in range(3):
        meta, rows = synthetic_interface(a, 16)
        metrics, _, series[meta["case"]] = mr.analyze_interface(meta, rows)
        require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
        checks += 1
    require(mr.orientation_agreement(series, 16)["status"] == "pass", "synthetic orientation agreement")
    meta, rows = synthetic_interface(1, 16, scale=1 + 1e-11)
    series[meta["case"]] = mr.analyze_interface(meta, rows)[2]
    require(mr.orientation_agreement(series, 16)["status"] == "fail", "orientation mismatch undetected")
    # Three empty records once passed vacuously (or crashed on max() of nothing).
    empty = {name: {"p1": [], "p2": [], "p1b": [], "p2b": []} for name in series}
    require(mr.orientation_agreement(empty, 16)["status"] == "fail", "empty orientation series accepted")
    checks += 3
    faults = [
        (dict(reflect_shift=True), "differ from the closed-form discrete"),
        (dict(reflect_shift=True), "imaginary part of R"),
        (dict(reflect_scale=1.001), "differ from the closed-form discrete"),
        (dict(transmit_shift=True), "differ from the closed-form discrete"),
        (dict(plane_fault=True), "differs between the two b planes"),
        # Revision 1.5 keeps the version-1 limit wherever the amplitude is resolvable
        # and bounds weak states by 1e-13 of the record peak.
        (dict(purity=("strong", 2e-9)), "projection residual exceeds"),
        (dict(purity=("quiet", 3e-13)), "projection residual exceeds"),
        (dict(meta_gate=1), "layout"),
        (dict(drop=1000), "prescribed E_b samples"),
        # An off-centre NaN once vanished from the purity maximum (max(x, nan) is x).
        (dict(nan_at=(400, 5)), "non-finite E_b sample"),
        (dict(nan_at=(400, 5)), "incomplete probe record"),
        # Added in the 2026-09-25 review (previously unexercised checks).
        (dict(plane_fault="p1b"), "differs between the two b planes"),
        (dict(reflect_scale=1.5), "continuum |R|/|T| error exceeds cap"),
        (dict(dt_nan=True), "q/dt differ"),
    ]
    for kwargs, text in faults:
        dt_nan = kwargs.pop("dt_nan", False)
        meta, rows = synthetic_interface(0, 16, **kwargs)
        if dt_nan:
            meta["dt_s"] = math.nan
        metrics, _, _ = mr.analyze_interface(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected V05-B fault: " + text)
        checks += 1
    require(mr.refinement({16: 0.0471754, 32: 0.0103689, 64: 0.00251729}, (16, 32, 64))["status"] == "pass",
            "V05-B predicted refinement")
    # Roundoff-scale TE_2 content (2e-15 of the peak) at a quiet state: version 1
    # divided by the tiny local amplitude and failed; revision 1.5 passes it.
    meta, rows = synthetic_interface(0, 16, purity=("quiet", 2e-15))
    metrics, _, _ = mr.analyze_interface(meta, rows)
    require(metrics["status"] == "pass" and metrics["max_purity_residual_v1_reported"] > mr.STRUCTURE_LIMIT
            and metrics["max_purity_residual"] < 1e-10, "revision 1.5 conditioning: %s" % metrics)
    meta, rows = synthetic_interface(0, 16, purity=("strong", 5e-10))
    require(mr.analyze_interface(meta, rows)[0]["status"] == "pass", "sub-limit strong content accepted")
    # A zero record must be exactly pure.
    meta, rows = synthetic_interface(0, 16, scale=0.0)
    meta["steps"] = 4
    rows = [r for r in rows if int(r["state"]) <= 4]
    require(mr.analyze_interface(meta, rows, fixed_suite=False)[0]["status"] == "pass", "zero smoke record")
    # Impurity at k = 0, where sin(0) = 0 exactly in every libm, so the TE_1
    # amplitude is exactly zero and the zero-amplitude rule must reject it. (Hosted
    # CI, 2026-09-25: the earlier +/-1e-300 pair at k = 4 and 12 relied on
    # sin(pi/4) == sin(3 pi/4), which holds in the Windows libm but not in glibc.)
    impure = [dict(r) for r in rows]
    impure[0]["value"] = repr(1e-300)
    require(has_failure(mr.analyze_interface(meta, impure, fixed_suite=False)[0], "zero amplitude"),
            "impure zero-amplitude record undetected")
    # A pair that nearly cancels leaves a subnormal amplitude, and so a subnormal
    # peak and floor; the purity limit must reject it. This is the glibc outcome
    # of the old pair, made platform-independent with a 1e-10 relative mismatch
    # (amplitude about 1e-311 whatever the last bit of either sine).
    impure = [dict(r) for r in rows]
    impure[4]["value"], impure[12]["value"] = repr(1e-300), repr(-1e-300 * (1 + 1e-10))
    require(has_failure(mr.analyze_interface(meta, impure, fixed_suite=False)[0], "projection residual exceeds"),
            "impure near-zero-amplitude record undetected")
    checks += 6
    print("PASS synthetic V05-B reductions: %d checks (reduced-TE oracle series at p=16)" % checks)
    return checks


# ---- V05-C -----------------------------------------------------------------------
def synthetic_slab(a, mode, p, omega_factor=1.0, amplitude_error=0.0, vacuum_shape=False, steps=None, drop=None):
    g, f_c, f_d = mr.slab_prediction(p, mode)
    roles = (a, (a + 1) % 3, (a + 2) % 3)
    cells, spacing = mr.role_list(roles, list(g["cells"])), mr.role_list(roles, list(g["spacing"]))
    dt = g["dt"]
    steps = math.ceil(2 / f_c / dt) if steps is None else steps
    meta = {"case": "slab-%s-m%d-p%d" % (AXES[a], mode, p), "kind": "slab", "roles": list(roles), "p": p,
            "mode": mode, "eps_r": EPS_R, "sigma_S_per_m": 0.0, "i_int": g["i_int"], "cells": cells,
            "spacing_m": spacing, "dt_s": dt, "q": 0.99, "steps": steps, "elapsed_seconds": 0.0}
    n_a, n_c = g["cells"][0], g["cells"][2]
    shape = [math.sin(PI * i / n_a) for i in range(n_a + 1)] if vacuum_shape else mr.slab_shape(g, f_d)
    omega = 2 * PI * f_d * omega_factor
    rows = []
    for n in range(steps + 1):
        for i in range(n_a + 1):
            value = (1 + amplitude_error) * math.cos(omega * n * dt) * shape[i]
            rows.append(probe_row(n, roles[1], mr.to_xyz(roles, (i, 0, n_c // 2)), spacing, dt, value))
    if drop is not None:
        del rows[drop]
    return meta, rows


def synthetic_slab_checks():
    checks, worst = 0, 0.0
    errors = {}
    for mode in (1, 2):
        for p in (24, 48, 96):
            meta, rows = synthetic_slab(0, mode, p)
            metrics, _ = mr.analyze_slab(meta, rows)
            require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
            worst = max(worst, metrics["discrete_error"], metrics["max_amplitude_error"], metrics["max_normalized_residual"])
            errors[mode, p] = metrics["continuum_error"]
            checks += 1
        require(mr.refinement({p: errors[mode, p] for p in (24, 48, 96)}, (24, 48, 96))["status"] == "pass",
                "V05-C refinement pass")
        checks += 1
    for a in (1, 2):
        meta, rows = synthetic_slab(a, 2, 24)
        require(mr.analyze_slab(meta, rows)[0]["status"] == "pass", "synthetic slab orientation %d" % a)
        checks += 1
    require(worst <= 1e-11, "synthetic V05-C estimator precision %.3g" % worst)
    faults = [
        (dict(omega_factor=1 + 3e-9), "discrete frequency error"),
        (dict(amplitude_error=3e-9), "modal amplitude error"),
        (dict(vacuum_shape=True), "projection residual exceeds"),
        (dict(omega_factor=0.99), "continuum resonance error"),
        (dict(steps=5), "differ from v1"),
        (dict(drop=40), "prescribed E_b line"),
    ]
    for kwargs, text in faults:
        meta, rows = synthetic_slab(1, 1, 24, **kwargs)
        metrics, _ = mr.analyze_slab(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected V05-C fault: " + text)
        checks += 1
    print("PASS synthetic V05-C reductions: %d checks; worst estimator deviation %.3g" % (checks, worst))
    return checks


# ---- V06-B -----------------------------------------------------------------------
def synthetic_dissipation(q=0.99, final=1e-6, balance_at=None, increase_at=None, negative_at=None, bound_at=None,
                          nonfinite_at=None, start_d=0.0, steps=mr.V06B_STEPS, bound_low_at=None, vanish_at=None):
    """``vanish_at`` drops Q and U to zero at one state, with D carrying the loss so
    the balance holds, and restores Q at the next state with D = 0."""
    dt = q / (C0 * math.sqrt(sum(1 / d**2 for d in mr.V06B_SPACING)))
    meta = {"case": "dissipation-q%s" % ("99" if q == 0.99 else "50"), "kind": "modular", "cells": list(mr.V06B_CELLS),
            "spacing_m": list(mr.V06B_SPACING), "dt_s": dt, "q": q, "steps": steps, "eps_r": mr.V06B_EPS_R,
            "sigma_S_per_m": mr.V06B_SIGMA, "diagnostics": True, "elapsed_seconds": 0.0}
    ratio = final ** (1 / mr.V06B_STEPS)
    q_values = [1e-14 * ratio**n for n in range(steps + 1)]
    if increase_at is not None:
        q_values[increase_at + 1] = q_values[increase_at] * (1 + 1e-11)
    if vanish_at is not None:
        q_values[vanish_at] = 0.0
    rows = []
    for n in range(steps + 1):
        d = start_d if n == 0 else q_values[n - 1] - q_values[n]
        if vanish_at is not None and n == vanish_at + 1:
            d = 0.0
        u = q_values[n]
        if balance_at == n:
            d += 2e-8 * q_values[n - 1]
        if negative_at == n:
            d = -1e-300
        if bound_at == n:
            u = 0.9 * q_values[n] / (1 + q)
        if bound_low_at == n:
            u = 1.1 * q_values[n] / (1 - q)
        row = {"state": str(n), "e_time_s": repr(n * dt), "h_time_s": repr((n - 0.5) * dt), "U_J": repr(u),
               "Q_J": repr(q_values[n]), "D_J": repr(d)}
        row.update({"max_" + name: repr(1.0) for name in NAMES})
        if nonfinite_at == n:
            row["max_Ex"] = "nan"
        rows.append(row)
    return meta, rows


def synthetic_dissipation_checks():
    checks = 0
    for q in (0.99, 0.5):
        metrics, _ = mr.analyze_dissipation(*synthetic_dissipation(q))
        require(metrics["status"] == "pass", "synthetic dissipation q=%g: %s" % (q, metrics["failures"]))
        checks += 1
    faults = [
        (dict(balance_at=700), "dissipation balance"),
        (dict(increase_at=300), "invariant increases"),
        (dict(negative_at=900), "negative dissipation"),
        (dict(bound_at=5), "energy bounds violated"),
        (dict(final=1e-3), "final Q_N/Q_0"),
        (dict(nonfinite_at=17), "nonfinite diagnostic"),
        (dict(start_d=1e-30), "state 0 carries"),
        (dict(steps=1999), "differ from v1"),
        # Added in the 2026-09-25 review: the lower bound, and an invariant that
        # reaches zero and reappears (monotonicity once applied only where Q_n > 0).
        (dict(bound_low_at=5), "energy bounds violated"),
        (dict(vanish_at=1000), "invariant increases"),
    ]
    for kwargs, text in faults:
        metrics, _ = mr.analyze_dissipation(*synthetic_dissipation(**kwargs))
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected V06-B fault: " + text)
        checks += 1
    metrics, _ = mr.analyze_dissipation(*synthetic_dissipation(final=0.5, steps=4), fixed_suite=False)
    require(metrics["status"] == "pass", "smoke-length dissipation synthetic: %s" % metrics["failures"])
    checks += 1
    print("PASS synthetic V06-B reductions: %d checks" % checks)
    return checks


# ---- Coefficient-table audit -------------------------------------------------------
def brute_force_classes(cells, rule):
    """Cell classes and per-edge four-cell means by explicit enumeration (sorted sums)."""
    cell_classes, edge_classes = {}, {}
    for i in range(cells[0]):
        for j in range(cells[1]):
            for k in range(cells[2]):
                key = rule((i, j, k))
                cell_classes[key] = cell_classes.get(key, 0) + 1
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        extents = [cells[t] + (0 if t == a else 1) for t in range(3)]
        for i in range(extents[0]):
            for j in range(extents[1]):
                for k in range(extents[2]):
                    index = (i, j, k)
                    if any(index[t] in (0, cells[t]) for t in (b, c)):
                        continue
                    values = []
                    for db in (0, 1):
                        for dc in (0, 1):
                            cell = list(index)
                            cell[b] -= db
                            cell[c] -= dc
                            values.append(rule(tuple(cell)))
                    key = (sum(sorted(v[0] for v in values)) / 4, sum(sorted(v[1] for v in values)) / 4)
                    edge_classes[key] = edge_classes.get(key, 0) + 1
    return cell_classes, edge_classes


def table_meta(kind, cells, roles, i_int, eps_r, sigma, dt, cell_classes, edge_classes):
    entries = []
    for (eps, sig), edges in edge_classes.items():
        x = sig * dt / (2 * eps * EPS0)
        entries.append({"eps_r": eps, "sigma_S_per_m": sig, "x": x, "Ca": (1 - x) / (1 + x),
                        "Cb": dt / (eps * EPS0) / (1 + x), "edges": edges})
    e_total = sum(math.prod(cells[t] + (0 if t == a else 1) for t in range(3)) for a in range(3))
    return {"kind": kind, "cells": list(cells), "roles": list(roles), "i_int": i_int, "eps_r": eps_r,
            "sigma_S_per_m": sigma, "dt_s": dt,
            "materials": {"cells": [{"eps_r": e, "sigma_S_per_m": s, "count": n} for (e, s), n in cell_classes.items()],
                          "map_bytes": 16 * math.prod(cells) if kind != "mode" else 0},
            "coefficients": {"index_bytes": 4 * e_total, "table_bytes": 48 * len(entries), "entries": entries}}


def coefficient_audit_checks():
    checks = 0
    dt = 2.5e-11
    cells, roles, i_int = (6, 9, 2), (1, 2, 0), 5          # a = y, the plane at cell 5 of 9
    rule = lambda cell: (EPS_R, 0.0) if cell[roles[0]] >= i_int else (1.0, 0.0)
    cell_classes, edge_classes = brute_force_classes(cells, rule)
    expected_cells, expected_edges = expected_materials({"kind": "sheet", "cells": list(cells), "roles": list(roles),
                                                         "i_int": i_int, "eps_r": EPS_R, "sigma_S_per_m": 0.0})
    require(cell_classes == expected_cells and edge_classes == expected_edges,
            "closed-form plane classes %s differ from the enumeration %s" % (expected_edges, edge_classes))
    require(sum(edge_classes.values()) == sum(update_edges(list(cells))), "update-range edge total")
    meta = table_meta("slab", cells, roles, i_int, EPS_R, 0.0, dt, cell_classes, edge_classes)
    require(coefficient_audit(meta) is None, "valid plane table rejected: %s" % coefficient_audit(meta))
    checks += 3
    lossy_rule = lambda cell: (EPS_R, 0.1)
    lossy_cells, lossy_edges = brute_force_classes((4, 3, 5), lossy_rule)
    lossy = table_meta("wave", (4, 3, 5), (0, 1, 2), 0, EPS_R, 0.1, dt, lossy_cells, lossy_edges)
    require(coefficient_audit(lossy) is None, "valid lossy table rejected: %s" % coefficient_audit(lossy))
    vacuum_cells, vacuum_edges = brute_force_classes((4, 3, 5), lambda cell: (1.0, 0.0))
    vacuum = table_meta("mode", (4, 3, 5), (0, 1, 2), 0, 1.0, 0.0, dt, vacuum_cells, vacuum_edges)
    require(coefficient_audit(vacuum) is None, "valid vacuum table rejected")
    retained = dict(vacuum)
    del retained["coefficients"]
    require(coefficient_audit(retained) is None, "retained V04 evidence without a table rejected")
    checks += 3

    def mutated(base, change):
        copy = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
        copy["coefficients"] = dict(base["coefficients"], entries=[dict(e) for e in base["coefficients"]["entries"]])
        copy["materials"] = dict(base["materials"], cells=[dict(c) for c in base["materials"]["cells"]])
        change(copy)
        return copy
    vacuum_index = next(i for i, e in enumerate(meta["coefficients"]["entries"]) if e["eps_r"] == 1.0)
    faults = [
        (meta, lambda m: m["coefficients"]["entries"][0].update(edges=m["coefficients"]["entries"][0]["edges"] + 1)),
        (meta, lambda m: m["coefficients"]["entries"][1].update(Cb=m["coefficients"]["entries"][1]["Cb"] * (1 + 1e-14))),
        (meta, lambda m: m["coefficients"]["entries"][vacuum_index].update(
            Cb=math.nextafter(m["coefficients"]["entries"][vacuum_index]["Cb"], 0))),
        (meta, lambda m: m["coefficients"]["entries"].append(dict(m["coefficients"]["entries"][0], eps_r=3.0))),
        (meta, lambda m: m["coefficients"]["entries"].pop()),
        (meta, lambda m: m["coefficients"].update(index_bytes=m["coefficients"]["index_bytes"] + 4)),
        (meta, lambda m: m["materials"]["cells"][0].update(count=m["materials"]["cells"][0]["count"] - 1)),
        (meta, lambda m: m.update(i_int=4)),
        (meta, lambda m: m.pop("coefficients")),
        (lossy, lambda m: m["coefficients"]["entries"][0].update(
            sigma_S_per_m=m["coefficients"]["entries"][0]["sigma_S_per_m"] * (1 + 1e-14))),
        (lossy, lambda m: m["coefficients"]["entries"][0].update(Ca=m["coefficients"]["entries"][0]["Ca"] + 1e-14)),
        (vacuum, lambda m: m["coefficients"]["entries"][0].update(eps_r=4.0)),
        (vacuum, lambda m: m["materials"].update(map_bytes=16 * 60)),
    ]
    for base, change in faults:
        require(coefficient_audit(mutated(base, change)) is not None, "undetected coefficient-table fault")
        checks += 1
    print("PASS coefficient-table audit: %d checks (closed-form classes equal the brute-force enumeration)" % checks)
    return checks


# ---- Material oracle ---------------------------------------------------------------
class MaterialOracle(Oracle):
    """FND-03 transcription with independently averaged per-cell materials, the
    MAT-01 lossy update and the dissipation of each step."""

    def __init__(self, cells, spacing, rule):
        super().__init__(cells, spacing)
        self.ca, self.cb, self.eps_e, self.sigma_e = [], [], [], []
        for id in range(3):
            b, c = (id + 1) % 3, (id + 2) % 3
            arrays = [self.make(id) for _ in range(4)]
            for i, j, k in self.indices(id):
                if self.wall(id, (i, j, k)):
                    continue
                eps = sigma = 0.0
                for dc in (0, 1):
                    for db in (0, 1):
                        cell = [i, j, k]
                        cell[b] -= db
                        cell[c] -= dc
                        e, s = rule(tuple(cell))
                        eps += e
                        sigma += s
                eps, sigma = eps / 4, sigma / 4
                arrays[2][i][j][k], arrays[3][i][j][k] = eps, sigma
            self.eps_e.append(arrays[2])
            self.sigma_e.append(arrays[3])
            self.ca.append(arrays[0])
            self.cb.append(arrays[1])

    def set_dt(self, dt):
        for id in range(3):
            for i, j, k in self.indices(id):
                if self.wall(id, (i, j, k)):
                    continue
                eps = self.eps_e[id][i][j][k] * EPS0
                x = self.sigma_e[id][i][j][k] * dt / (2 * eps)
                self.ca[id][i][j][k] = (1 - x) / (1 + x)
                self.cb[id][i][j][k] = dt / eps / (1 + x)

    def material_step(self, e, h, dt, sources=()):
        """One full step; sources are (id, (i, j, k), J) at the half time. Returns D of the step."""
        for id in (3, 4, 5):
            for i, j, k in self.indices(id):
                h[id - 3][i][j][k] -= dt / MU0 * self.curl_e(e, id, i, j, k)
        current = {(id, index): value for id, index, value in sources}
        volume = self.spacing[0] * self.spacing[1] * self.spacing[2]
        joule = []
        for id in (0, 1, 2):
            ca, cb, sigma = self.ca[id], self.cb[id], self.sigma_e[id]
            for i, j, k in self.indices(id):
                if self.wall(id, (i, j, k)):
                    continue
                old = e[id][i][j][k]
                new = ca[i][j][k] * old + cb[i][j][k] * (self.curl_h(h, id, i, j, k) - current.get((id, (i, j, k)), 0.0))
                e[id][i][j][k] = new
                mean = (new + old) / 2
                joule.append(self.weight(id, (i, j, k)) * sigma[i][j][k] * mean * mean)
        return volume * dt * math.fsum(joule)

    def material_diagnostics(self, e, h, dt):
        electric, magnetic, cross, maxima = [], [], [], []
        for id in range(6):
            array = (e + h)[id]
            maximum = 0.0
            for i, j, k in self.indices(id):
                value = array[i][j][k]
                maximum = max(maximum, abs(value))
                weight = self.weight(id, (i, j, k))
                if id < 3:
                    if not self.wall(id, (i, j, k)):
                        electric.append(weight * self.eps_e[id][i][j][k] * value * value)
                else:
                    magnetic.append(weight * value * value)
                    cross.append(weight * value * self.curl_e(e, id, i, j, k))
            maxima.append(maximum)
        volume = self.spacing[0] * self.spacing[1] * self.spacing[2]
        u = volume / 2 * (EPS0 * math.fsum(electric) + MU0 * math.fsum(magnetic))
        return u, u - volume * dt / 2 * math.fsum(cross), maxima


def wave_fixture(oracle, meta, e, h):
    """V01-type compact potentials with the medium's (lossless or lossy) H phasor."""
    a, b, c = meta["roles"]
    spacing, cells, dt = meta["spacing_m"], meta["cells"], meta["dt_s"]
    k = 2 * PI / LAMBDA
    big_k = kappa(k, spacing[a])
    sigma = mr.parse_wave_name(meta["case"])["sigma"]
    if sigma == 0:
        h_phasor = math.sqrt(EPS_R) / ETA0 * cmath.exp(-0.5j * discrete_omega(dt, big_k, EPS_R) * dt)
    else:
        h_phasor = lossy_h(dt, big_k, lossy_step_root(dt, big_k, EPS_R * EPS0, sigma))
    sign = 1 if (a + 1) % 3 == b else -1

    def potential(id):
        array = oracle.make(id)
        if id not in (b, c + 3):
            return array
        half = half_offsets(id)
        for i, j, kk in oracle.indices(id):
            index = (i, j, kk)
            taper = 1.0
            for t in range(3):
                cells_from = (index[t] + half[t]) * spacing[t] / spacing[t]
                distance = min(cells_from, cells[t] - cells_from)
                taper *= min(max((distance - 2) / 2, 0.0), 1.0)
            r = (index[a] + half[a]) * spacing[a]
            if id == c + 3:
                array[i][j][kk] = -sign / big_k * taper * math.sin(k * r)
            else:
                array[i][j][kk] = taper * abs(h_phasor) / big_k * math.sin(k * r - cmath.phase(h_phasor))
        return array
    p_e = [potential(id) for id in range(3)]
    p_h = [potential(id) for id in (3, 4, 5)]
    for id in range(3):
        for i, j, kk in oracle.indices(id):
            if not oracle.wall(id, (i, j, kk)):
                e[id][i][j][kk] = oracle.curl_h(p_h, id, i, j, kk)
    for id in (3, 4, 5):
        for i, j, kk in oracle.indices(id):
            h[id - 3][i][j][kk] = oracle.curl_e(p_e, id, i, j, kk)


def slab_fixture(oracle, meta, e, h):
    a, b, c = meta["roles"]
    spec = mr.parse_slab_name(meta["case"])
    g, f_c, _ = mr.slab_prediction(spec["p"], spec["mode"])
    g = dict(g, dt=meta["dt_s"])
    from check_material_benchmarks import roots, slab_discrete, V05B_KC, F0
    f_d = roots(lambda f: slab_discrete(f, g), V05B_KC * C0 / 2 / PI * 1.001, 1e6, 5 * F0, spec["mode"])[spec["mode"] - 1]
    shape = mr.slab_shape(g, f_d)
    n_c = meta["cells"][c]
    for i, j, kk in oracle.indices(b):
        index = (i, j, kk)
        if not oracle.wall(b, index):
            e[b][i][j][kk] = shape[index[a]] * math.sin(PI * index[c] / n_c)
    dt, omega = meta["dt_s"], 2 * PI * f_d
    factor = math.sin(omega * dt / 2) / (MU0 * (2 / dt * math.sin(omega * dt / 2)))
    for id in (3, 4, 5):
        for i, j, kk in oracle.indices(id):
            h[id - 3][i][j][kk] = oracle.curl_e(e, id, i, j, kk) * factor


def material_rule(meta):
    """The fixed version-1 material rule of a smoke case, from its name and the audit geometry."""
    name = meta["case"]
    if name.startswith("dielectric") or name.startswith("lossy"):
        sigma = mr.parse_wave_name(name)["sigma"]
        return lambda cell: (EPS_R, sigma)
    if name.startswith("dissipation"):
        return lambda cell: (mr.V06B_EPS_R, mr.V06B_SIGMA)
    if name.startswith("interface"):
        spec = mr.parse_interface_name(name)
        i_int, a = v05b_geometry(spec["p"])["i_int"], spec["a"]
    else:
        spec = mr.parse_slab_name(name)
        i_int, a = v05c_geometry(spec["p"])["i_int"], spec["a"]
    require(meta["i_int"] == i_int, "declared interface cell")
    return lambda cell: (EPS_R, 0.0) if cell[a] >= i_int else (1.0, 0.0)


MATERIAL_SMOKE = ("dielectric-xy-p24", "interface-x-p16", "slab-x-m1-p24", "lossy-xy-p24-sig0p1", "dissipation-q99")


def oracle_material_smoke(root):
    checks = 0
    for name in MATERIAL_SMOKE:
        meta, probes, diagnostics = load_case(root / name)
        dt = meta["dt_s"]
        require(abs(dt / (meta["q"] / (C0 * math.sqrt(sum(1 / d**2 for d in meta["spacing_m"])))) - 1) <= 5e-15,
                "independent CFL")
        oracle = MaterialOracle(meta["cells"], meta["spacing_m"], material_rule(meta))
        oracle.set_dt(dt)
        e = [oracle.make(id) for id in range(3)]
        h = [oracle.make(id) for id in (3, 4, 5)]
        sources, pulse = [], None
        if meta["kind"] == "wave":
            wave_fixture(oracle, meta, e, h)
        elif meta["kind"] == "slab":
            slab_fixture(oracle, meta, e, h)
        elif meta["kind"] == "modular":
            shape = oracle.fixture()
            for id in range(3):
                for i, j, k in oracle.indices(id):
                    e[id][i][j][k] = shape[id][i][j][k]
        else:
            a, b, c = meta["roles"]
            n_c = meta["cells"][c]
            pulse = gaussian_pulse(dt, meta["steps"])
            for plane in (0, 1):
                for k in range(1, n_c):
                    sources.append((b, mr.to_xyz((a, b, c), (meta["i_src"], plane, k)), math.sin(PI * k / n_c)))
        dissipation = 0.0
        for n in range(meta["steps"] + 1):
            u, q, maxima = oracle.material_diagnostics(e, h, dt)
            row = diagnostics[n]
            scale = max(u, 1e-300)
            require(close(float(row["U_J"]), u, scale) and close(float(row["Q_J"]), q, scale),
                    "%s U/Q state %d" % (name, n))
            require(close(float(row["D_J"]), dissipation, dissipation or 1e-300), "%s D state %d" % (name, n))
            for id, name_id in enumerate(NAMES):
                require(close(float(row["max_" + name_id]), maxima[id], maxima[id] or 1e-300),
                        "%s maxima state %d" % (name, n))
            checks += 4
            for probe in probes:
                if int(probe["state"]) != n:
                    continue
                id = NAMES.index(probe["component"])
                i, j, k = (int(probe[x]) for x in "ijk")
                value = (e + h)[id][i][j][k]
                require(close(float(probe["value"]), value, maxima[id] or 1e-300),
                        "%s probe %s[%d,%d,%d] state %d" % (name, probe["component"], i, j, k, n))
                checks += 1
            if n == meta["steps"]:
                break
            step_sources = [(id, index, value * pulse[n]) for id, index, value in sources] if pulse else ()
            dissipation = oracle.material_step(e, h, dt, step_sources)
        print("PASS material oracle %s: %d states of probes/U/Q/D/maxima within 1e-12" % (name, meta["steps"] + 1))
    return checks


def analyze_material_smoke(root):
    """The reductions on the smoke-length material cases (no full-suite limits)."""
    checks = 0
    for name in MATERIAL_SMOKE:
        meta, probes, diagnostics = load_case(root / name)
        if meta["kind"] == "wave":
            metrics = mr.analyze_wave(meta, probes, fixed_suite=False)[0]
        elif meta["kind"] == "sheet":
            metrics = mr.analyze_interface(meta, probes, fixed_suite=False)[0]
        elif meta["kind"] == "slab":
            metrics = mr.analyze_slab(meta, probes, fixed_suite=False)[0]
        else:
            metrics = mr.analyze_dissipation(meta, diagnostics, fixed_suite=False)[0]
        require(metrics["status"] == "pass", "smoke %s: %s" % (name, metrics["failures"]))
        checks += 1
    print("PASS smoke-length material reductions: %d cases" % checks)
    return checks


def fixture_report_checks(root):
    """The structural audit must require each material case's plateau report (a
    missing key once defaulted to 0.0) and reject one above 1e-11."""
    checks = 0
    faults = [(lambda m: m.pop("fixture_max_plateau_error"), "missing plateau report"),
              (lambda m: m.update(fixture_max_plateau_error=2e-11), "plateau report above 1e-11"),
              (lambda m: m.update(fixture_max_plateau_error=float("nan")), "non-finite plateau report")]
    for change, label in faults:
        copy = root.parent / (root.name + "-fixture-fault")
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(root, copy)
        path = copy / "dielectric-xy-p24" / "metadata.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        change(meta)
        path.write_text(json.dumps(meta), encoding="utf-8")
        try:
            audit_closed(copy, "smoke")
        except (ValueError, KeyError):
            checks += 1
        else:
            require(False, "undetected fixture-report fault: " + label)
        finally:
            shutil.rmtree(copy)
    print("PASS fixture-report audit faults: %d detected" % checks)
    return checks


def synthetic_checks():
    return (synthetic_wave_checks() + synthetic_interface_checks() + synthetic_slab_checks()
            + synthetic_dissipation_checks() + coefficient_audit_checks())
