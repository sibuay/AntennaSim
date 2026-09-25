"""MAT-03 independent V05/V06 reductions of closed-v1 material artifacts.

Imported by scripts/analyze_closed_benchmarks.py. Reads emitted metadata/CSV
rows only; no solver operator is imported. Every prediction and cap comes from
the MAT-01 specification audit (check_material_benchmarks.py) and the REF-05
estimators (reference_measurements.py); nothing is re-derived here.

Python 3.9+, standard library.
"""
import cmath
import math

from check_material_benchmarks import (C0, MU0, EPS0, ETA0, PI, LAMBDA, F0, EPS_R, V05A_CAPS, v01_like, kappa,
                                       v05b_geometry, discrete_reflection, beta_continuum, dft_at, V05B_BAND,
                                       V05B_BAND_POINTS, V05B_R_CAPS, V05B_T_CAPS, V05B_DISCRETE_LIMIT, V05B_KC,
                                       v05c_geometry, slab_discrete, slab_continuum, reduced_wavenumbers, roots,
                                       V05C_CAPS, lossy_step_root, V06_SIGMAS, V06_DECAY_CAPS, V06_PHASE_CAPS,
                                       V06_DISCRETE_LIMIT, project, recurrence_frequency)
from reference_measurements import fit_harmonic, native_impedance

NAMES = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
AXES = "xyz"
AMPLITUDE = 1.0
STRUCTURE_LIMIT = 1e-9          # discrete, amplitude, residual, inactive, purity (V05-A/B/C, V06-A)
IMPEDANCE_LIMIT = 1e-8          # V05-A complex impedance
ORIENTATION_LIMIT = 1e-12       # V05-B orientation agreement
# V05-B purity, revision 1.5 (MAT-03, 2026-09-23): the residual is normalized by
# max(|a_n|, PURITY_FLOOR * max_n |a_n|). Version 1 divided by |a_n| alone, which
# demands sub-roundoff precision where the TE_1 amplitude passes near zero: the
# criterion is meaningful only while 1e-9 |a_n| exceeds the binary64 resolution of
# the record, eps * peak = 2.2e-16 peak, i.e. |a_n| > 2.2e-7 peak. The floor 1e-4
# adds a factor of about 500 for accumulation over up to 2441 steps, so below it the
# limit is 1e-13 of the record peak. Above it the version-1 limit is unchanged.
PURITY_FLOOR = 1e-4
ORDER_RANGE = (1.8, 2.2)
BALANCE_LIMIT = 1e-8            # V06-B
MONOTONE_LIMIT = 1e-12
FINAL_ENERGY_LIMIT = 1e-4
V06B_STEPS = 2000
V06B_EPS_R, V06B_SIGMA = 2.25, 0.01
V06B_CELLS, V06B_SPACING = [12, 14, 16], (0.01, 0.015, 0.02)
ORDERINGS = ((0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1))
SIGMA_LABEL = {0.01: "sig0p01", 0.1: "sig0p1"}


def finite(value):
    return isinstance(value, float) and math.isfinite(value)


# Maxima and minima that keep a NaN: the built-in max(x, nan) returns x, so a NaN
# sample could vanish from a worst-case value (2026-09-25 review). Every limit
# below is written as `not value <= limit`, so a NaN worst case fails.
def worse(current, value):
    return value if value > current or math.isnan(value) else current


def lower(current, value):
    return value if value < current or math.isnan(value) else current


def worst_of(values, start=0.0):
    for value in values:
        start = worse(start, value)
    return start


def exceeds(value, limit):
    return not value <= limit


def role_list(roles, values):
    """Role-ordered (a, b, c) values placed on the x/y/z axes."""
    out = [None, None, None]
    for r, axis in enumerate(roles):
        out[axis] = values[r]
    return out


def to_xyz(roles, role_index):
    return tuple(role_list(roles, role_index))


def geometry_failures(meta, roles, cells, spacing, dt, steps, fixed_suite):
    failures = []
    if meta["cells"] != role_list(roles, list(cells)):
        failures.append("cells %s differ from v1 %s" % (meta["cells"], role_list(roles, list(cells))))
    if len(meta["spacing_m"]) != 3 or any(exceeds(abs(x / y - 1), 5e-15)
                                          for x, y in zip(meta["spacing_m"], role_list(roles, list(spacing)))):
        failures.append("spacing differs from v1 definition")
    if exceeds(abs(meta["q"] / 0.99 - 1), 5e-15) or exceeds(abs(meta["dt_s"] / dt - 1), 5e-15):
        failures.append("q/dt differ from v1 definition")
    if fixed_suite and meta["steps"] != steps:
        failures.append("steps %d differ from v1 %d" % (meta["steps"], steps))
    if meta["steps"] < 1:
        failures.append("no evolved state")
    return failures


def refinement(errors, keys):
    """Strictly decreasing errors with log2 orders in [1.8, 2.2] over the available keys."""
    failures = []
    sequence = [errors.get(k) for k in keys]
    if any(e is None or not finite(e) or e <= 0 for e in sequence):
        return {"errors": sequence, "orders": [None] * (len(keys) - 1), "status": "fail",
                "failures": ["missing/nonpositive error"]}
    if any(not sequence[i] > sequence[i + 1] for i in range(len(sequence) - 1)):
        failures.append("errors not strictly decreasing")
    orders = [math.log2(sequence[i] / sequence[i + 1]) for i in range(len(sequence) - 1)]
    if any(not ORDER_RANGE[0] <= o <= ORDER_RANGE[1] for o in orders):
        failures.append("observed order outside [1.8,2.2]")
    return {"errors": sequence, "orders": orders, "failures": failures, "status": "pass" if not failures else "fail"}


def group_probes(probes):
    """{(state, component id): {index: (value, time, position)}}; duplicates reported."""
    lines, duplicates = {}, []
    for row in probes:
        key = int(row["state"]), NAMES.index(row["component"])
        index = tuple(int(row[k]) for k in "ijk")
        entry = lines.setdefault(key, {})
        if index in entry:
            duplicates.append((key, index))
        entry[index] = (float(row["value"]), float(row["time_s"]),
                        tuple(float(row[k]) for k in ("x_m", "y_m", "z_m")))
    return lines, duplicates


# ---- V05-A / V06-A: homogeneous eigenwaves ---------------------------------------
def parse_wave_name(name):
    parts = name.split("-")
    if len(parts) not in (3, 4) or parts[0] not in ("dielectric", "lossy") or len(parts[1]) != 2:
        return None
    try:
        a, b = AXES.index(parts[1][0]), AXES.index(parts[1][1])
        p = int(parts[2][1:]) if parts[2].startswith("p") else None
    except ValueError:
        return None
    if a == b or p not in (24, 48, 96):
        return None
    if parts[0] == "dielectric":
        return {"a": a, "b": b, "p": p, "sigma": 0.0} if len(parts) == 3 else None
    sigma = {v: k for k, v in SIGMA_LABEL.items()}.get(parts[3]) if len(parts) == 4 else None
    if sigma is None or (p == 96 and (a, b) != (0, 1)):
        return None
    return {"a": a, "b": b, "p": p, "sigma": sigma}


def expected_wave_names(lossy):
    if not lossy:
        return ["dielectric-%s%s-p%d" % (AXES[a], AXES[b], p) for a, b in ORDERINGS for p in (24, 48, 96)]
    names = []
    for sigma in V06_SIGMAS:
        names += ["lossy-%s%s-p%d-%s" % (AXES[a], AXES[b], p, SIGMA_LABEL[sigma]) for a, b in ORDERINGS for p in (24, 48)]
        names.append("lossy-xy-p96-%s" % SIGMA_LABEL[sigma])
    return names


def wave_fits(meta, probes, spec, failures, h_floor):
    """V01 native-line fits of the active lines at every state; inactive-line maximum."""
    a, b, p = spec["a"], spec["b"], spec["p"]
    c = 3 - a - b
    active_e, active_h = b, c + 3
    eta = ETA0 / math.sqrt(EPS_R)
    k = 2 * PI / LAMBDA
    centre = [n // 2 for n in meta["cells"]]
    prescribed = []
    for axial in range(p, 2 * p):
        index = list(centre)
        index[a] = axial
        prescribed.append(tuple(index))
    prescribed.sort()
    lines, duplicates = group_probes(probes)
    if duplicates:
        failures.append("duplicate probe samples")
    fits, times = {}, {}
    worst = {"inactive": 0.0, "condition": 0.0, "residual_e": 0.0, "residual_h": 0.0}
    for n in range(meta["steps"] + 1):
        for id in range(6):
            samples = lines.get((n, id), {})
            if sorted(samples) != prescribed:
                failures.append("state %d %s samples are not the prescribed native line" % (n, NAMES[id]))
                continue
            if len({t for _, t, _ in samples.values()}) != 1:
                failures.append("state %d %s mixes sample times" % (n, NAMES[id]))
            scale = 1.0 if id < 3 else eta
            if id not in (active_e, active_h):
                worst["inactive"] = worst_of((abs(v) * scale for v, _, _ in samples.values()), worst["inactive"])
                continue
            family = "e" if id == active_e else "h"
            try:
                coefficient, residual, condition = fit_harmonic(
                    [(r[a], v) for v, _, r in samples.values()], k, p,
                    0.5 * AMPLITUDE if family == "e" else h_floor)
            except ValueError as error:
                failures.append("state %d %s fit rejected: %s" % (n, NAMES[id], error))
                continue
            fits[n, family] = coefficient
            times[n, family] = next(iter(samples.values()))[1]
            worst["condition"] = worse(worst["condition"], condition)
            worst["residual_" + family] = worse(worst["residual_" + family], residual * scale / AMPLITUDE)
    return fits, times, worst


def analyze_wave(meta, probes, fixed_suite=True):
    """V05-A (sigma = 0) or V06-A (sigma > 0) reductions for one eigenwave case."""
    spec = parse_wave_name(meta["case"])
    metrics = {"case": meta["case"], "steps": meta["steps"], "dt_s": meta["dt_s"], "q": meta["q"],
               "elapsed_seconds": meta.get("elapsed_seconds")}
    if spec is None:
        metrics.update({"failures": ["unknown case name"], "status": "fail"})
        return metrics, []
    a, b, p, sigma = spec["a"], spec["b"], spec["p"], spec["sigma"]
    c = 3 - a - b
    spacing, cells, dt_v1, steps_v1, k, omega_d = v01_like(p, EPS_R)
    roles = (a, b, c)
    failures = geometry_failures(meta, roles, cells, spacing, dt_v1, steps_v1, fixed_suite)
    if (meta["kind"] != "wave" or meta["roles"] != list(roles) or meta["p"] != p or meta["eps_r"] != EPS_R
            or meta["sigma_S_per_m"] != sigma or meta["i_int"] != 0):
        failures.append("case flags inconsistent with name")
    dt, steps = meta["dt_s"], meta["steps"]
    eta = ETA0 / math.sqrt(EPS_R)
    sign = 1 if (a + 1) % 3 == b else -1
    metrics.update({"a": a, "b": b, "p": p, "sigma_S_per_m": sigma, "sign": sign})
    trace = []
    if sigma == 0:
        fits, times, worst = wave_fits(meta, probes, spec, failures, 0.5 * AMPLITUDE / eta)
        metrics.update({"continuum_cap": V05A_CAPS[p], "omega_discrete": omega_d,
                        "predicted_continuum_error": abs(omega_d * math.sqrt(EPS_R) / (k * C0) - 1)})
        omega_m = None
        if (0, "e") in fits and (steps, "e") in fits:
            omega_m = cmath.phase(fits[steps, "e"] / fits[0, "e"]) / (steps * dt)
            if not omega_m > 0:
                failures.append("measured frequency not positive")
                omega_m = None
        else:
            failures.append("missing initial/final active E fit")
        amplitude = {"e": 0.0, "h": 0.0}
        for (n, family), coefficient in fits.items():
            scale = 1.0 if family == "e" else eta
            amplitude[family] = worse(amplitude[family], abs(abs(coefficient) * scale / AMPLITUDE - 1))
        impedance = 0.0
        if omega_m is not None:
            metrics["continuum_error"] = abs(omega_m * math.sqrt(EPS_R) / (k * C0) - 1)
            metrics["discrete_error"] = abs(omega_m / omega_d - 1)
            for n in range(steps + 1):
                if (n, "e") not in fits or (n, "h") not in fits:
                    failures.append("state %d lacks an E/H fit for the impedance" % n)
                    continue
                try:
                    z = native_impedance(fits[n, "e"], fits[n, "h"], times[n, "e"], times[n, "h"], omega_m,
                                         0.5 * AMPLITUDE / eta)
                except ValueError as error:
                    failures.append("state %d impedance rejected: %s" % (n, error))
                    continue
                error = abs(z / (sign * eta) - 1)
                impedance = worse(impedance, error)
                trace.append({"case": meta["case"], "state": n, "quantity": "impedance", "re": z.real, "im": z.imag,
                              "error": error})
            if exceeds(metrics["continuum_error"], V05A_CAPS[p]):
                failures.append("continuum phase-speed error exceeds cap")
            if exceeds(metrics["discrete_error"], STRUCTURE_LIMIT):
                failures.append("discrete frequency error exceeds limit")
        else:
            metrics["continuum_error"] = metrics["discrete_error"] = None
        metrics.update({"omega_measured": omega_m, "max_amplitude_error_e": amplitude["e"],
                        "max_amplitude_error_h": amplitude["h"], "max_residual_e": worst["residual_e"],
                        "max_residual_h": worst["residual_h"], "max_condition": worst["condition"],
                        "max_inactive": worst["inactive"], "max_impedance_error": impedance,
                        "reference_impedance_ohm": sign * eta})
        if exceeds(amplitude["e"], STRUCTURE_LIMIT) or exceeds(amplitude["h"], STRUCTURE_LIMIT):
            failures.append("fitted amplitude error exceeds limit")
        if exceeds(impedance, IMPEDANCE_LIMIT):
            failures.append("complex impedance error exceeds limit")
    else:
        eps = EPS_R * EPS0
        z = lossy_step_root(dt, kappa(k, spacing[0]), eps, sigma)
        alpha = sigma / (2 * eps)
        omega_l = math.sqrt((C0 * k)**2 / EPS_R - alpha**2)
        x = sigma * dt / (2 * eps)
        metrics.update({"z": [z.real, z.imag], "x": x, "alpha": alpha, "omega_prime": omega_l,
                        "decay_cap": V06_DECAY_CAPS[p, sigma], "phase_cap": V06_PHASE_CAPS[p],
                        "predicted_decay_error": abs(-math.log(abs(z)) / dt / alpha - 1),
                        "predicted_phase_error": abs(cmath.phase(z) / dt / omega_l - 1)})
        if "z" in meta:
            metrics["generator_z_difference"] = abs(complex(*meta["z"]) / z - 1)
        # The V01 floors: 0.5 A on E and 0.5 A/eta on H (the H floor read 0.25 A/eta
        # before the 2026-09-25 review; the smallest measured H amplitude is 0.760 A/eta).
        fits, times, worst = wave_fits(meta, probes, spec, failures, 0.5 * AMPLITUDE / eta)
        ratios, h_ratios = [], []
        discrete = h_discrete = 0.0
        floor = math.inf
        for n in range(steps + 1):
            if (n, "e") in fits:
                floor = lower(floor, abs(fits[n, "e"]))
            if n == steps:
                break
            if (n, "e") in fits and (n + 1, "e") in fits:
                rho = fits[n + 1, "e"] / fits[n, "e"]
                ratios.append(rho)
                discrete = worse(discrete, abs(rho / z - 1))
                trace.append({"case": meta["case"], "state": n, "quantity": "rho_e", "re": rho.real, "im": rho.imag,
                              "error": abs(rho / z - 1)})
            else:
                failures.append("state %d/%d lacks an E fit for the growth factor" % (n, n + 1))
            if (n, "h") in fits and (n + 1, "h") in fits:
                rho_h = fits[n + 1, "h"] / fits[n, "h"]
                h_ratios.append(rho_h)
                h_discrete = worse(h_discrete, abs(rho_h / z - 1))
        metrics.update({"max_discrete_ratio_error": discrete, "max_magnetic_ratio_error_reported": h_discrete,
                        "min_amplitude": floor if math.isfinite(floor) else None, "max_residual_e": worst["residual_e"],
                        "max_residual_h": worst["residual_h"], "max_condition": worst["condition"],
                        "max_inactive": worst["inactive"]})
        if ratios and len(ratios) == steps:
            rho_m = sum(ratios) / len(ratios)
            decay_m, phase_m = -math.log(abs(rho_m)) / dt, cmath.phase(rho_m) / dt
            metrics.update({"decay_measured": decay_m, "phase_measured": phase_m,
                            "decay_error": abs(decay_m / alpha - 1), "phase_error": abs(phase_m / omega_l - 1)})
            if exceeds(metrics["decay_error"], V06_DECAY_CAPS[p, sigma]):
                failures.append("decay-rate error exceeds cap")
            if exceeds(metrics["phase_error"], V06_PHASE_CAPS[p]):
                failures.append("phase error exceeds cap")
        else:
            metrics.update({"decay_error": None, "phase_error": None})
            failures.append("growth factor not measured at every step")
        if exceeds(discrete, V06_DISCRETE_LIMIT):
            failures.append("per-step ratio differs from the exact growth factor z beyond 1e-9")
        if not floor >= 0.5 * AMPLITUDE:
            failures.append("E amplitude below the 0.5 A floor")
    if exceeds(worst["residual_e"], STRUCTURE_LIMIT) or exceeds(worst["residual_h"], STRUCTURE_LIMIT):
        failures.append("fit residual exceeds limit")
    if exceeds(worst["inactive"], STRUCTURE_LIMIT):
        failures.append("inactive line samples exceed limit")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace


# ---- V05-B: TE-mode interface -----------------------------------------------------
def parse_interface_name(name):
    parts = name.split("-")
    if len(parts) != 3 or parts[0] != "interface" or parts[1] not in AXES or not parts[2].startswith("p"):
        return None
    try:
        p = int(parts[2][1:])
    except ValueError:
        return None
    a = AXES.index(parts[1])
    if p not in (16, 32, 64) or (p == 64 and a != 0):
        return None
    return {"a": a, "p": p}


def expected_interface_names():
    return ["interface-%s-p%d" % (AXES[a], p) for p in (16, 32) for a in range(3)] + ["interface-x-p64"]


def band():
    return [F0 * (V05B_BAND[0] + (V05B_BAND[1] - V05B_BAND[0]) * i / (V05B_BAND_POINTS - 1))
            for i in range(V05B_BAND_POINTS)]


def analyze_interface(meta, probes, fixed_suite=True):
    """V05-B reductions for one orientation; returns (metrics, trace rows, probe series)."""
    spec = parse_interface_name(meta["case"])
    metrics = {"case": meta["case"], "steps": meta["steps"], "dt_s": meta["dt_s"], "q": meta["q"],
               "elapsed_seconds": meta.get("elapsed_seconds")}
    if spec is None:
        metrics.update({"failures": ["unknown case name"], "status": "fail"})
        return metrics, [], None
    a, p = spec["a"], spec["p"]
    roles = (a, (a + 1) % 3, (a + 2) % 3)
    g = v05b_geometry(p)
    failures = geometry_failures(meta, roles, g["cells"], g["spacing"], g["dt"], g["steps"], fixed_suite)
    if (meta["kind"] != "sheet" or meta["roles"] != list(roles) or meta["i_int"] != g["i_int"]
            or meta["i_src"] != g["i_src"] or meta["i_p1"] != g["i_p1"] or meta["i_p2"] != g["i_p2"]
            or meta["gate"] != g["gate"] or meta["eps_r"] != EPS_R or meta["sigma_S_per_m"] != 0):
        failures.append("case layout or material flags differ from v1")
    dt, steps = meta["dt_s"], meta["steps"]
    n_c = g["cells"][2]
    b = roles[1]
    lines, duplicates = group_probes(probes)
    if duplicates:
        failures.append("duplicate probe samples")
    line_keys = [to_xyz(roles, (g["i_p1"], 0, k)) for k in range(n_c + 1)]
    point_keys = {"p2": to_xyz(roles, (g["i_p2"], 0, n_c // 2)), "p1b": to_xyz(roles, (g["i_p1"], 1, n_c // 2)),
                  "p2b": to_xyz(roles, (g["i_p2"], 1, n_c // 2))}
    prescribed = sorted(line_keys + list(point_keys.values()))
    shape = [math.sin(PI * k / n_c) for k in range(n_c + 1)]
    series = {"p1": [], "p2": [], "p1b": [], "p2b": []}
    projections = []
    invariance = 0
    complete = True
    for n in range(steps + 1):
        samples = lines.get((n, b), {})
        if sorted(samples) != prescribed or any(key != (n, b) for key in lines if key[0] == n and key[1] != b):
            failures.append("state %d does not hold exactly the prescribed E_b samples" % n)
            complete = False
            continue
        values = [samples[key][0] for key in line_keys]
        if not all(math.isfinite(v) for v in values + [samples[key][0] for key in point_keys.values()]):
            failures.append("state %d holds a non-finite E_b sample" % n)
            complete = False
            continue
        projections.append(project(values, shape))
        series["p1"].append(samples[line_keys[n_c // 2]][0])
        for label, key in point_keys.items():
            series[label].append(samples[key][0])
        if series["p1b"][-1] != series["p1"][-1] or series["p2b"][-1] != series["p2"][-1]:
            invariance += 1
    peak = max((abs(amplitude) for amplitude, _ in projections), default=0.0)
    floor = PURITY_FLOOR * peak
    purity = purity_v1 = 0.0
    below = 0
    for amplitude, residual in projections:
        if abs(amplitude) < floor:
            below += 1
        if amplitude != 0:
            purity_v1 = worse(purity_v1, residual / abs(amplitude))
        scale = max(abs(amplitude), floor)
        if scale == 0:
            if residual != 0:
                failures.append("the line is not a pure TE_1 profile at zero amplitude")
        else:
            purity = worse(purity, residual / scale)
    metrics.update({"a": a, "p": p, "gate": g["gate"], "max_purity_residual": purity,
                    "max_purity_residual_v1_reported": purity_v1, "purity_peak_amplitude": peak,
                    "purity_states_below_floor": below, "b_plane_mismatches": invariance,
                    "continuum_cap": V05B_R_CAPS[p]})
    if not purity <= STRUCTURE_LIMIT:
        failures.append("line projection residual exceeds 1e-9 of max(amplitude, 1e-4 record peak)")
    if invariance:
        failures.append("E_b differs between the two b planes at %d states" % invariance)
    trace = []
    if complete and fixed_suite:
        s1, s2 = series["p1"][1:], series["p2"][1:]
        d_a = g["spacing"][0]
        worst = {"discrete": 0.0, "imag": 0.0, "r": 0.0, "t": 0.0}
        for f in band():
            inc = dft_at(s1, dt, f, 0, g["gate"])
            ref = dft_at(s1, dt, f, g["gate"], steps)
            tra = dft_at(s2, dt, f)
            r_d, t_d, k1, k2 = discrete_reflection(f, g)
            r_m = ref / inc * cmath.exp(2j * k1 * (g["i_int"] - g["i_p1"]) * d_a)
            t_m = tra / inc * cmath.exp(1j * (k1 * (g["i_int"] - g["i_p1"]) + k2 * (g["i_p2"] - g["i_int"])) * d_a)
            b1, b2 = beta_continuum(f, 1.0), beta_continuum(f, EPS_R)
            r_c, t_c = (b1 - b2) / (b1 + b2), 2 * b1 / (b1 + b2)
            row = {"case": meta["case"], "f_hz": f, "R_re": r_m.real, "R_im": r_m.imag, "T_re": t_m.real,
                   "T_im": t_m.imag, "R_d": r_d.real, "T_d": t_d.real, "R_c": r_c, "T_c": t_c,
                   "discrete_error": worse(abs(r_m - r_d), abs(t_m - t_d)),
                   "continuum_error": worse(abs(abs(r_m) - abs(r_c)), abs(abs(t_m) - abs(t_c)))}
            trace.append(row)
            worst["discrete"] = worse(worst["discrete"], row["discrete_error"])
            worst["imag"] = worse(worst["imag"], abs(r_m.imag))
            worst["r"] = worse(worst["r"], abs(abs(r_m) - abs(r_c)))
            worst["t"] = worse(worst["t"], abs(abs(t_m) - abs(t_c)))
        metrics.update({"max_discrete_error": worst["discrete"], "max_imag_R": worst["imag"],
                        "max_R_continuum_error": worst["r"], "max_T_continuum_error": worst["t"],
                        "continuum_error": worse(worst["r"], worst["t"])})
        if not worst["discrete"] <= V05B_DISCRETE_LIMIT:
            failures.append("measured R/T differ from the closed-form discrete coefficients beyond 1e-4")
        if not worst["imag"] <= V05B_DISCRETE_LIMIT:
            failures.append("imaginary part of R exceeds 1e-4")
        if not (worst["r"] <= V05B_R_CAPS[p] and worst["t"] <= V05B_T_CAPS[p]):
            failures.append("continuum |R|/|T| error exceeds cap")
    elif fixed_suite:
        failures.append("incomplete probe record: R/T not evaluated")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace, series


def orientation_agreement(series_by_name, p):
    """V05-B: the three orientations' probe series at one p agree within 1e-12 normalized."""
    names = ["interface-%s-p%d" % (axis, p) for axis in AXES]
    failures = []
    if any(series_by_name.get(name) is None for name in names):
        return {"p": p, "status": "fail", "failures": ["missing orientation series"], "max_difference": None}
    reference = series_by_name[names[0]]
    if not all(reference[label] for label in ("p1", "p2")):
        return {"p": p, "status": "fail", "failures": ["empty x-orientation series"], "max_difference": None}
    scale = worst_of(abs(v) for label in ("p1", "p2") for v in reference[label]) or 1.0
    worst = 0.0
    for name in names[1:]:
        other = series_by_name[name]
        for label in ("p1", "p2"):
            if len(other[label]) != len(reference[label]):
                failures.append("%s %s record length differs" % (name, label))
                continue
            worst = worse(worst, worst_of(abs(x - y) for x, y in zip(reference[label], other[label])) / scale)
    if exceeds(worst, ORIENTATION_LIMIT):
        failures.append("orientation series differ by %.3g normalized" % worst)
    return {"p": p, "max_difference": worst, "failures": failures, "status": "pass" if not failures else "fail"}


# ---- V05-C: slab-loaded cavity ----------------------------------------------------
def parse_slab_name(name):
    parts = name.split("-")
    if len(parts) != 4 or parts[0] != "slab" or parts[1] not in AXES:
        return None
    try:
        mode, p = int(parts[2][1:]), int(parts[3][1:])
    except ValueError:
        return None
    if not (parts[2].startswith("m") and parts[3].startswith("p")) or mode not in (1, 2) or p not in (24, 48, 96):
        return None
    return {"a": AXES.index(parts[1]), "mode": mode, "p": p}


def expected_slab_names():
    return ["slab-%s-m%d-p%d" % (AXES[a], mode, p) for a in range(3) for mode in (1, 2) for p in (24, 48, 96)]


_SLAB_CACHE = {}


def slab_prediction(p, mode):
    """(geometry, f_c, f_d) from the audit's characteristic functions (cached)."""
    key = p, mode
    if key not in _SLAB_CACHE:
        g = v05c_geometry(p)
        start = V05B_KC * C0 / 2 / PI * 1.001
        f_c = roots(slab_continuum, start, 1e6, 5 * F0, 2)[mode - 1]
        f_d = roots(lambda f: slab_discrete(f, g), start, 1e6, 5 * F0, mode)[mode - 1]
        _SLAB_CACHE[key] = (g, f_c, f_d)
    return _SLAB_CACHE[key]


def slab_shape(g, f_d):
    k1, k2 = reduced_wavenumbers(f_d, g)[0]
    d_a, n_a, i_int = g["spacing"][0], g["cells"][0], g["i_int"]
    scale = math.sin(k1 * i_int * d_a) / math.sin(k2 * (n_a - i_int) * d_a)
    return [math.sin(k1 * i * d_a) if i <= i_int else scale * math.sin(k2 * (n_a - i) * d_a) for i in range(n_a + 1)]


def analyze_slab(meta, probes, fixed_suite=True):
    spec = parse_slab_name(meta["case"])
    metrics = {"case": meta["case"], "steps": meta["steps"], "dt_s": meta["dt_s"], "q": meta["q"],
               "elapsed_seconds": meta.get("elapsed_seconds")}
    if spec is None:
        metrics.update({"failures": ["unknown case name"], "status": "fail"})
        return metrics, []
    a, mode, p = spec["a"], spec["mode"], spec["p"]
    roles = (a, (a + 1) % 3, (a + 2) % 3)
    g, f_c, f_d = slab_prediction(p, mode)
    steps_v1 = math.ceil(2 / f_c / g["dt"])
    failures = geometry_failures(meta, roles, g["cells"], g["spacing"], g["dt"], steps_v1, fixed_suite)
    if (meta["kind"] != "slab" or meta["roles"] != list(roles) or meta["mode"] != mode or meta["i_int"] != g["i_int"]
            or meta["eps_r"] != EPS_R or meta["sigma_S_per_m"] != 0):
        failures.append("case layout or material flags differ from v1")
    dt, steps = meta["dt_s"], meta["steps"]
    cap = V05C_CAPS[mode, p]
    metrics.update({"a": a, "mode": mode, "p": p, "f_c_hz": f_c, "f_d_hz": f_d, "continuum_cap": cap,
                    "predicted_continuum_error": abs(f_d / f_c - 1)})
    if "f_d_hz" in meta:
        metrics["generator_f_d_difference"] = abs(meta["f_d_hz"] / f_d - 1)
    shape = slab_shape(g, f_d)
    n_a, n_c = g["cells"][0], g["cells"][2]
    keys = [to_xyz(roles, (i, 0, n_c // 2)) for i in range(n_a + 1)]
    lines, duplicates = group_probes(probes)
    if duplicates:
        failures.append("duplicate probe samples")
    b = roles[1]
    amplitudes, residual, complete = [], 0.0, True
    for n in range(steps + 1):
        samples = lines.get((n, b), {})
        if sorted(samples) != sorted(keys) or any(key[0] == n and key[1] != b for key in lines):
            failures.append("state %d does not hold exactly the prescribed E_b line" % n)
            complete = False
            continue
        try:
            amplitude, fit_residual = project([samples[key][0] for key in keys], shape)
        except RuntimeError as error:
            failures.append("state %d projection rejected: %s" % (n, error))
            complete = False
            continue
        amplitudes.append(amplitude)
        residual = worse(residual, fit_residual / AMPLITUDE)
    trace = []
    omega_m = None
    if complete and steps >= 2:
        try:
            omega_m = recurrence_frequency(amplitudes, dt)
        except RuntimeError as error:
            failures.append("recurrence frequency rejected: %s" % error)
    if omega_m is not None:
        f_m = omega_m / (2 * PI)
        amplitude_error = worst_of(abs(x / AMPLITUDE - math.cos(omega_m * n * dt)) for n, x in enumerate(amplitudes))
        for n, x in enumerate(amplitudes):
            trace.append({"case": meta["case"], "state": n, "quantity": "a_n", "re": x, "im": 0.0,
                          "error": abs(x / AMPLITUDE - math.cos(omega_m * n * dt))})
        metrics.update({"f_measured_hz": f_m, "continuum_error": abs(f_m / f_c - 1),
                        "discrete_error": abs(f_m / f_d - 1), "max_amplitude_error": amplitude_error,
                        "max_normalized_residual": residual})
        if exceeds(metrics["continuum_error"], cap):
            failures.append("continuum resonance error exceeds cap")
        if exceeds(metrics["discrete_error"], STRUCTURE_LIMIT):
            failures.append("discrete frequency error exceeds limit")
        if exceeds(amplitude_error, STRUCTURE_LIMIT):
            failures.append("modal amplitude error exceeds limit")
        if exceeds(residual, STRUCTURE_LIMIT):
            failures.append("projection residual exceeds limit")
    else:
        metrics.update({"continuum_error": None, "discrete_error": None, "max_amplitude_error": None,
                        "max_normalized_residual": residual})
        if complete:
            failures.append("frequency not measured")
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace


# ---- V06-B: closed-grid dissipation identity --------------------------------------
def expected_dissipation_names():
    return ["dissipation-q99", "dissipation-q50"]


def analyze_dissipation(meta, diagnostics, fixed_suite=True):
    name = meta["case"]
    metrics = {"case": name, "steps": meta["steps"], "dt_s": meta["dt_s"], "q": meta["q"],
               "elapsed_seconds": meta.get("elapsed_seconds")}
    failures = []
    if name not in expected_dissipation_names():
        metrics.update({"failures": ["unknown case name"], "status": "fail"})
        return metrics, []
    q = 0.99 if name.endswith("q99") else 0.5
    dt_v1 = q / (C0 * math.sqrt(sum(1 / d**2 for d in V06B_SPACING)))
    if (meta["cells"] != V06B_CELLS or len(meta["spacing_m"]) != 3
            or any(exceeds(abs(x / y - 1), 5e-15) for x, y in zip(meta["spacing_m"], V06B_SPACING))):
        failures.append("grid differs from the V03 fixture")
    if exceeds(abs(meta["q"] / q - 1), 5e-15) or exceeds(abs(meta["dt_s"] / dt_v1 - 1), 5e-15):
        failures.append("q/dt differ from v1 definition")
    if fixed_suite and meta["steps"] != V06B_STEPS:
        failures.append("steps %d differ from v1 %d" % (meta["steps"], V06B_STEPS))
    if (meta["kind"] != "modular" or meta["eps_r"] != V06B_EPS_R or meta["sigma_S_per_m"] != V06B_SIGMA
            or not meta["diagnostics"]):
        failures.append("case flags or material differ from v1")
    rows = []
    for index, row in enumerate(diagnostics):
        values = {key: float(value) for key, value in row.items()}
        if int(values["state"]) != index:
            failures.append("diagnostic state %d out of order" % index)
        rows.append(values)
    steps = meta["steps"]
    if len(rows) != steps + 1:
        failures.append("expected %d diagnostic states, found %d" % (steps + 1, len(rows)))
    nonfinite = next((n for n, r in enumerate(rows) if any(not math.isfinite(v) for v in r.values())), None)
    if nonfinite is not None:
        failures.append("nonfinite diagnostic at state %d" % nonfinite)
    trace = []
    if rows and nonfinite is None and len(rows) == steps + 1:
        q0 = rows[0]["Q_J"]
        balance = monotone = 0.0
        bound_violation = negative = increase = None
        if rows[0]["D_J"] != 0:
            failures.append("state 0 carries a dissipation value")
        for n, row in enumerate(rows):
            if row["D_J"] < 0 and negative is None:
                negative = n
            u, qn = row["U_J"], row["Q_J"]
            if bound_violation is None and not ((1 - q) * u - BALANCE_LIMIT * q0 <= qn <= (1 + q) * u + BALANCE_LIMIT * q0):
                bound_violation = n
            if n == steps:
                break
            nxt = rows[n + 1]
            residual = abs(nxt["Q_J"] - qn + nxt["D_J"])
            # The balance is relative to Q_n and applies where Q_n > 0; monotonicity
            # applies at every state (the 2026-09-25 review found it skipped at Q_n <= 0).
            if increase is None and exceeds(nxt["Q_J"], qn * (1 + MONOTONE_LIMIT)):
                increase = n
            if qn > 0:
                balance = worse(balance, residual / qn)
                monotone = worse(monotone, (nxt["Q_J"] - qn) / qn)
            trace.append({"case": name, "state": n, "quantity": "balance", "re": residual, "im": nxt["D_J"],
                          "error": residual / qn if qn > 0 else 0.0})
        final = rows[-1]["Q_J"] / q0 if q0 > 0 else math.nan
        metrics.update({"Q0_J": q0, "U0_J": rows[0]["U_J"], "max_balance_error": balance,
                        "max_relative_Q_increase": monotone, "bound_violation_state": bound_violation,
                        "first_negative_D_state": negative, "final_Q_ratio": final})
        if not q0 > 0:
            failures.append("initial invariant is not positive")
        if exceeds(balance, BALANCE_LIMIT):
            failures.append("dissipation balance Q_(n+1)-Q_n+D_n exceeds 1e-8 Q_n")
        if increase is not None or exceeds(monotone, MONOTONE_LIMIT):
            failures.append("invariant increases beyond 1e-12 relative (first at state %s)" % increase)
        if negative is not None:
            failures.append("negative dissipation at state %d" % negative)
        if bound_violation is not None:
            failures.append("energy bounds violated at state %d" % bound_violation)
        if fixed_suite and not final <= FINAL_ENERGY_LIMIT:
            failures.append("final Q_N/Q_0 %.3g exceeds 1e-4" % final)
    metrics["failures"] = failures
    metrics["status"] = "pass" if not failures else "fail"
    return metrics, trace
