"""MAT-01 analytical specification audit for V04-V07; no solver import.

Python 3.9+, standard library only. Prints deterministic predictions for the
Phase 2 closed-domain benchmarks (PEC cavity, dielectric, conductivity,
spectra) and checks the fixed version-1 caps, guards, estimator precision and
fault detection on synthetic data. Nothing here is a measured solver result.
See docs/validation/MAT-01-closed-domain-benchmarks.md, version 1.
"""

import cmath
import math

C0 = 299792458.0
MU0 = 1.25663706127e-6
EPS0 = 1 / (MU0 * C0 * C0)
ETA0 = MU0 * C0
PI = math.pi
LAMBDA = 0.3  # m, V01 wavelength reused as the P2 length unit
F0 = C0 / LAMBDA
T0 = 1 / F0


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def field_count(cells):
    x, y, z = cells
    return (x*(y+1)*(z+1) + (x+1)*y*(z+1) + (x+1)*(y+1)*z
            + (x+1)*y*z + x*(y+1)*z + x*y*(z+1))


def mib(cells):
    return 8 * field_count(cells) / 2**20


def cfl_dt(spacing, q):
    return q / (C0 * math.sqrt(sum(1 / d**2 for d in spacing)))


def kappa(k, d):
    """Discrete wavenumber of a centred difference acting on a harmonic."""
    return 2 / d * math.sin(k * d / 2)


def discrete_omega(dt, big_k, eps_r=1.0):
    """Physical-branch discrete frequency for a lossless uniform medium."""
    argument = C0 * dt * big_k / (2 * math.sqrt(eps_r))
    require(0 < argument < 1, "discrete dispersion argument outside (0,1)")
    return 2 / dt * math.asin(argument)


def cyclic(a):
    return a, (a + 1) % 3, (a + 2) % 3


# --------------------------------------------------------------------------
# V04 - PEC cavity
# --------------------------------------------------------------------------
V04_BASE_CELLS = (12, 16, 20)
V04_BASE_SPACING = (0.01, 0.015, 0.02)   # m, at s=1
V04_MODES = ((1, 1), (2, 1), (1, 2))    # (n_b, n_c) transverse mode indices
V04_PERIODS = 2                         # observation length in continuum periods
V04_CAPS = {1: 0.0052, 2: 0.0013, 4: 0.000325}  # continuum cap per refinement s
V04_HALF_Q_CAP = 0.0028
V04_DISCRETE_LIMIT = 1e-9
V04_STRUCTURE_LIMIT = 1e-9


def cavity(s, q=0.99):
    cells = tuple(c * s for c in V04_BASE_CELLS)
    spacing = tuple(d / s for d in V04_BASE_SPACING)
    lengths = tuple(c * d for c, d in zip(cells, spacing))
    return cells, spacing, lengths, cfl_dt(spacing, q)


def cavity_mode(s, a, nb, nc, q=0.99):
    cells, spacing, lengths, dt = cavity(s, q)
    _, b, c = cyclic(a)
    kb, kc = nb * PI / lengths[b], nc * PI / lengths[c]
    omega_c = C0 * math.hypot(kb, kc)
    big_kb, big_kc = kappa(kb, spacing[b]), kappa(kc, spacing[c])
    omega_d = discrete_omega(dt, math.hypot(big_kb, big_kc))
    steps = math.ceil(V04_PERIODS * 2 * PI / omega_c / dt)
    return {"cells": cells, "spacing": spacing, "lengths": lengths, "dt": dt, "kb": kb, "kc": kc,
            "Kb": big_kb, "Kc": big_kc, "omega_c": omega_c, "omega_d": omega_d, "steps": steps,
            "error": abs(omega_d / omega_c - 1)}


def recurrence_frequency(samples, dt):
    """cos(omega dt) from the exact three-term recurrence of a discrete harmonic.

    Least squares over all interior states; independent of any solver code.
    """
    rows = [(samples[n], samples[n+1] + samples[n-1]) for n in range(1, len(samples) - 1)]
    require(len(rows) >= 2, "too few states for the recurrence estimator")
    numerator = math.fsum(x * y for x, y in rows)
    denominator = 2 * math.fsum(x * x for x, _ in rows)
    require(denominator > 0, "zero-energy recurrence")
    cosine = numerator / denominator
    require(-1 < cosine < 1, "recurrence outside the oscillatory range")
    return math.acos(cosine) / dt


def project(values, shape):
    """Single-parameter least-squares amplitude of a known spatial shape."""
    ss = math.fsum(v * v for v in shape)
    require(ss > 0, "zero shape")
    amplitude = math.fsum(y * v for y, v in zip(values, shape)) / ss
    residual = max(abs(y - amplitude * v) for y, v in zip(values, shape))
    return amplitude, residual


def cavity_synthetic(mode, amplitude_error=0.0, frequency_factor=1.0, h_sign=1, phase_shift=0.0):
    """Exact discrete standing mode sampled on the V04 native lines."""
    dt, steps = mode["dt"], mode["steps"]
    omega = mode["omega_d"] * frequency_factor
    big_omega = 2 / dt * math.sin(omega * dt / 2)
    kb, kc, big_kb, big_kc = mode["kb"], mode["kc"], mode["Kb"], mode["Kc"]
    # Lines are enumerated in role coordinates; the audit does not need the
    # x/y/z permutation to check the estimator algebra.
    nb, nc = mode["nb"], mode["nc"]
    db, dc = mode["db"], mode["dc"]
    jb = [j for j in range(nb + 1)]           # E_a and H_c lines along b
    kk = [k for k in range(nc)]               # H_b line along c
    fac_c = math.sin(kc * (nc // 4) * dc)     # E_a/H_c transverse factor at i_c=N_c/4
    fac_b = math.sin(kb * (nb // 4) * db)     # H_b transverse factor at i_b=N_b/4
    require(abs(fac_c) >= 0.5 and abs(fac_b) >= 0.5, "transverse factor below 0.5")
    shape_e = [math.sin(kb * j * db) * fac_c for j in jb]
    shape_hc = [math.cos(kb * (j + 0.5) * db) * fac_c for j in jb]
    shape_hb = [math.cos(kc * (k + 0.5) * dc) * fac_b for k in kk]
    a_amp = 1.0 + amplitude_error
    hb_amp = -big_kc / (MU0 * big_omega)
    hc_amp = big_kb / (MU0 * big_omega)
    e_states, hb_states, hc_states = [], [], []
    for n in range(steps + 1):
        te, th = n * dt, (n - 0.5) * dt
        e_states.append([a_amp * math.cos(omega * te + phase_shift) * v for v in shape_e])
        hb_states.append([h_sign * hb_amp * math.sin(omega * th + phase_shift) * v for v in shape_hb])
        hc_states.append([h_sign * hc_amp * math.sin(omega * th + phase_shift) * v for v in shape_hc])
    return e_states, hb_states, hc_states, shape_e, shape_hb, shape_hc


def cavity_measure(mode, data):
    """The V04-A reduction: modal projections, recurrence frequency, E/H relation."""
    e_states, hb_states, hc_states, shape_e, shape_hb, shape_hc = data
    dt = mode["dt"]
    a_n, worst_res = [], 0.0
    for state in e_states:
        amp, res = project(state, shape_e)
        a_n.append(amp)
        worst_res = max(worst_res, res)
    omega_m = recurrence_frequency(a_n, dt)
    big_omega = 2 / dt * math.sin(omega_m * dt / 2)
    amp_err = max(abs(a - math.cos(omega_m * n * dt)) for n, a in enumerate(a_n))
    hb_ref, hc_ref = -mode["Kc"] / (MU0 * big_omega), mode["Kb"] / (MU0 * big_omega)
    h_err = 0.0
    for n, (hb, hc) in enumerate(zip(hb_states, hc_states)):
        th = (n - 0.5) * dt
        b, rb = project(hb, shape_hb)
        c, rc = project(hc, shape_hc)
        worst_res = max(worst_res, rb / abs(hb_ref), rc / abs(hc_ref))
        h_err = max(h_err, abs(b / hb_ref - math.sin(omega_m * th)), abs(c / hc_ref - math.sin(omega_m * th)))
    return omega_m, amp_err, h_err, worst_res


def audit_v04_eigenmodes():
    print("== V04-A PEC cavity eigenmodes (discrete/continuum predictions) ==")
    worst_precision = 0.0
    orders = []
    work = 0
    for a in range(3):
        _, b, c = cyclic(a)
        for nb, nc in V04_MODES:
            errors = []
            for s in (1, 2, 4):
                m = cavity_mode(s, a, nb, nc)
                m.update(nb=m["cells"][b], nc=m["cells"][c], db=m["spacing"][b], dc=m["spacing"][c])
                require(m["error"] < V04_CAPS[s], "V04 prediction exceeds cap s=%d" % s)
                errors.append(m["error"])
                work += math.prod(m["cells"]) * m["steps"]
                data = cavity_synthetic(m)
                omega_m, amp_err, h_err, res = cavity_measure(m, data)
                precision = max(abs(omega_m / m["omega_d"] - 1), amp_err, h_err, res)
                worst_precision = max(worst_precision, precision)
                if a == 0:
                    print("s=%d pol=%s mode=(%d,%d) cells=%s dt=%.6g steps=%d f_c=%.6f GHz f_d=%.6f GHz "
                          "error=%.9g cap=%g" % (s, "xyz"[a], nb, nc, m["cells"], m["dt"], m["steps"],
                                                m["omega_c"] / 2 / PI / 1e9, m["omega_d"] / 2 / PI / 1e9,
                                                m["error"], V04_CAPS[s]))
            order = [math.log(errors[i] / errors[i+1], 2) for i in (0, 1)]
            require(all(1.8 <= o <= 2.2 for o in order), "V04 refinement order")
            orders.extend(order)
    m = cavity_mode(1, 0, 1, 1)
    m.update(nb=m["cells"][1], nc=m["cells"][2], db=m["spacing"][1], dc=m["spacing"][2])
    # Fault detection on the s=1 (0,1,1)-family fixture.
    for kwargs, label, limit in ((dict(frequency_factor=1 + 3e-9), "frequency", V04_DISCRETE_LIMIT),
                                 (dict(amplitude_error=3e-9), "amplitude", V04_STRUCTURE_LIMIT),
                                 (dict(h_sign=-1), "H sign", V04_STRUCTURE_LIMIT),
                                 (dict(phase_shift=1e-6), "phase", V04_STRUCTURE_LIMIT)):
        omega_m, amp_err, h_err, res = cavity_measure(m, cavity_synthetic(m, **kwargs))
        detected = {"frequency": abs(omega_m / m["omega_d"] - 1), "amplitude": amp_err,
                    "H sign": h_err, "phase": max(amp_err, h_err)}[label]
        require(detected > limit, "undetected V04 fault: " + label)
    for a in range(3):
        m = cavity_mode(1, a, 1, 1, q=0.5)
        require(m["error"] < V04_HALF_Q_CAP, "V04 q=0.5 cap")
        work += math.prod(m["cells"]) * m["steps"]
        print("sensitivity q=0.5 s=1 pol=%s mode=(1,1) steps=%d error=%.9g cap=%g" %
              ("xyz"[a], m["steps"], m["error"], V04_HALF_Q_CAP))
    print("predicted refinement orders: min %.6f max %.6f" % (min(orders), max(orders)))
    print("synthetic V04-A estimator precision (frequency/amplitude/H relation/residual): %.3g" % worst_precision)
    require(worst_precision < 1e-11, "V04-A synthetic estimator precision")
    print("V04-A 30-case cell_steps=%d; fields at s=4 %.3f MiB" % (work, mib(cavity(4)[0])))
    return work


# ---- V04-B cavity spectrum -------------------------------------------------
V04B_STEPS = 32768
V04B_SHORT_STEPS = 16384            # truncated record for the resolution comparison
V04B_SOURCE_INDEX = (5, 7, 9)      # Ez edge at s=1: (i, j, k+1/2)
V04B_PROBE_INDEX = (7, 9, 13)      # Ez edge at s=1
V04B_TAU = 1.0 / (2 * PI * 1.5e9)  # s, differentiated-Gaussian time constant
V04B_FCUT = 2.27e9
V04B_STRENGTH_FLOOR = 0.05
V04B_PEAK_BIN_LIMIT = 0.25
V04B_HEIGHT_LIMIT = 0.15


def pulse_samples(dt, tau):
    """Antisymmetric differentiated-Gaussian samples at half times; sums to zero."""
    half = math.ceil(6 * tau / dt)
    samples = []
    for m in range(2 * half + 1):
        r = (half - m) * dt          # exact multiples: pairs cancel bitwise
        samples.append((r / tau) * math.exp(-(r / tau)**2 / 2))
    return samples


def pulse_spectrum(samples, dt, omega):
    return dt * sum(g * cmath.exp(-1j * omega * (m + 0.5) * dt) for m, g in enumerate(samples))


def cavity_lines(s):
    """Exact discrete cavity lines reachable from an Ez edge source to an Ez probe."""
    cells, spacing, lengths, dt = cavity(s)
    nx, ny, nz = cells
    src = tuple(v * s for v in V04B_SOURCE_INDEX)
    prb = tuple(v * s for v in V04B_PROBE_INDEX)
    samples = pulse_samples(dt, V04B_TAU)
    lines = []
    for m in range(1, nx):
        for n in range(1, ny):
            for p in range(0, nz):
                ks = (kappa(m * PI / lengths[0], spacing[0]), kappa(n * PI / lengths[1], spacing[1]),
                      kappa(p * PI / lengths[2], spacing[2]))
                big_k2 = sum(k * k for k in ks)
                omega_d = discrete_omega(dt, math.sqrt(big_k2))
                if omega_d / 2 / PI > 3 * V04B_FCUT:
                    continue
                omega_c = C0 * math.sqrt((m * PI / lengths[0])**2 + (n * PI / lengths[1])**2 + (p * PI / lengths[2])**2)
                transverse = 1 - ks[2]**2 / big_k2
                def phi(idx):
                    return (math.sin(m * PI * idx[0] / nx) * math.sin(n * PI * idx[1] / ny)
                            * math.cos(p * PI * (idx[2] + 0.5) / nz))
                norm = (nx / 2) * (ny / 2) * (nz if p == 0 else nz / 2)
                theta = omega_d * dt
                strength = (transverse * phi(src) * phi(prb) / norm / (EPS0 * math.cos(theta / 2))
                            * abs(pulse_spectrum(samples, dt, omega_d)))
                lines.append({"mode": (m, n, p), "omega_d": omega_d, "omega_c": omega_c,
                              "strength": abs(strength), "signed": strength})
    lines.sort(key=lambda line: line["omega_d"])
    return lines, dt, samples, src, prb


def fft(values):
    """Iterative radix-2 FFT (complex list, power-of-two length)."""
    n = len(values)
    require(n and n & (n - 1) == 0, "FFT length must be a power of two")
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    length = 2
    while length <= n:
        w_len = cmath.exp(-2j * PI / length)
        for start in range(0, n, length):
            w = 1
            for k in range(length // 2):
                u = out[start + k]
                v = out[start + k + length // 2] * w
                out[start + k] = u + v
                out[start + k + length // 2] = u - v
                w *= w_len
        length *= 2
    return out


def hann(n):
    return [0.5 - 0.5 * math.cos(2 * PI * (i + 0.5) / n) for i in range(n)]


def spectral_peaks(series, dt, zero_pad=4):
    """Hann-windowed, zero-padded magnitude spectrum with parabolic peak refinement.

    Returns (bin_hz, peaks) with peaks as (frequency_hz, height) sorted by height.
    """
    n = len(series)
    window = hann(n)
    padded = [complex(x * w) for x, w in zip(series, window)] + [0j] * (zero_pad * n - n)
    spectrum = [abs(v) for v in fft(padded)]
    half = len(padded) // 2
    peaks = []
    for i in range(1, half):
        if spectrum[i] > spectrum[i-1] and spectrum[i] >= spectrum[i+1] and spectrum[i] > 0:
            lo, mid, hi = (math.log(max(spectrum[i + o], 1e-300)) for o in (-1, 0, 1))
            denominator = lo - 2 * mid + hi
            delta = 0.5 * (lo - hi) / denominator if denominator < 0 else 0.0
            peaks.append(((i + delta) / (zero_pad * n * dt), spectrum[i] * dt))
    peaks.sort(key=lambda p: -p[1])
    return 1 / (n * dt), peaks


def audit_v04_spectrum():
    print("== V04-B cavity spectrum (mode lines, separations, synthetic identification) ==")
    lines, dt, samples, src, prb = cavity_lines(1)
    require(math.fsum(samples) == 0.0, "pulse samples must sum to exactly zero")
    below = [line for line in lines if line["omega_d"] / 2 / PI < V04B_FCUT]
    s_max = max(line["strength"] for line in below)
    required = [line for line in below if line["strength"] >= V04B_STRENGTH_FLOOR * s_max]
    visible = [line for line in below if line["strength"] >= 0.01 * s_max]
    print("s=1 dt=%.6g pulse_samples=%d tau=%.4g s source=%s probe=%s lines<f_cut=%d required=%d" %
          (dt, len(samples), V04B_TAU, src, prb, len(below), len(required)))
    for line in required:
        print("  mode=%s f_d=%.6f GHz f_c=%.6f GHz dispersion=%.3e strength=%.3f" %
              (line["mode"], line["omega_d"] / 2 / PI / 1e9, line["omega_c"] / 2 / PI / 1e9,
               abs(line["omega_d"] / line["omega_c"] - 1), line["strength"] / s_max))
    # Synthetic identification: sum of exact modal responses after the pulse,
    # sampled at E times, with the modal phase from the discrete Green's function.
    n_pulse = len(samples)
    phases = {}
    for line in lines:
        theta = line["omega_d"] * dt
        pulse = sum((samples[m] - (samples[m-1] if m else 0.0)) * cmath.exp(-1j * theta * m)
                    for m in range(n_pulse)) + (-samples[-1]) * cmath.exp(-1j * theta * n_pulse)
        phases[line["mode"]] = cmath.phase(pulse)
    series = []
    for n in range(V04B_STEPS):
        t = n * dt
        value = 0.0
        if n >= n_pulse + 1:
            for line in lines:
                value += line["signed"] * math.sin(line["omega_d"] * t + phases[line["mode"]])
        series.append(value)
    for steps in (V04B_STEPS, V04B_SHORT_STEPS):
        bin_hz = 1 / (steps * dt)
        min_sep = min(abs(x["omega_d"] - y["omega_d"]) / 2 / PI / bin_hz
                      for i, x in enumerate(visible) for y in visible[i+1:])
        require(min_sep >= 4, "V04-B visible lines closer than four bins (%d states: %.2f)" % (steps, min_sep))
        bin_measured, peaks = spectral_peaks(series[:steps], dt)
        top = max(h for _, h in peaks)
        worst_bin, worst_height, spurious = 0.0, 0.0, 0
        for line in required:
            f_line = line["omega_d"] / 2 / PI
            nearest = min(peaks, key=lambda p: abs(p[0] - f_line))
            worst_bin = max(worst_bin, abs(nearest[0] - f_line) / bin_hz)
            worst_height = max(worst_height, abs(nearest[1] / top - line["strength"] / s_max))
        for f_peak, height in peaks:
            if f_peak < V04B_FCUT and height >= V04B_STRENGTH_FLOOR * top:
                if min(abs(f_peak - line["omega_d"] / 2 / PI) for line in below) > V04B_PEAK_BIN_LIMIT * bin_hz:
                    spurious += 1
        worst_continuum = max(abs(line["omega_d"] / line["omega_c"] - 1) for line in required)
        print("  record %d states: bin=%.4f MHz (%.2e of f_min) min_visible_separation=%.1f bins; synthetic worst "
              "required-line offset %.4f bins, relative height error %.4f, spurious peaks %d; max dispersion %.2e" %
              (steps, bin_hz / 1e6, bin_hz / (required[0]["omega_d"] / 2 / PI), min_sep, worst_bin, worst_height,
               spurious, worst_continuum))
        require(worst_bin < V04B_PEAK_BIN_LIMIT and worst_height < V04B_HEIGHT_LIMIT and spurious == 0,
                "V04-B synthetic identification exceeds its fixed limits")
    cells = cavity(1)[0]
    print("V04-B cell_steps: %d" % (math.prod(cells) * V04B_STEPS))
    return math.prod(cells) * V04B_STEPS


# ---- V04-C interior PEC enforcement ----------------------------------------
V04C_MARGIN = 3
V04C_SOURCE_INSIDE = (8, 10, 12)   # Ez edge index
V04C_SOURCE_OUTSIDE = (1, 1, 1)    # Ez edge index


def e_edges(cells, component):
    """All (i,j,k) storage indices of one E component on the FND-03 extents."""
    extents = [cells[axis] + (0 if axis == component else 1) for axis in range(3)]
    for i in range(extents[0]):
        for j in range(extents[1]):
            for k in range(extents[2]):
                yield (i, j, k)


def pec_marked(component, index, box, shell):
    """Independent endpoint enumeration of the pec_box / pec_shell rules."""
    lo = [box[0][0], box[1][0], box[2][0]]
    hi = [box[0][1], box[1][1], box[2][1]]
    a = component
    if not (lo[a] <= index[a] < hi[a]):
        return False
    on_face = False
    for axis in range(3):
        if axis == a:
            continue
        if not (lo[axis] <= index[axis] <= hi[axis]):
            return False
        if index[axis] in (lo[axis], hi[axis]):
            on_face = True
    return on_face if shell else True


def audit_v04_enforcement():
    print("== V04-C interior PEC enforcement (mask enumeration, fixture compatibility) ==")
    cells = tuple(c + 2 * V04C_MARGIN for c in V04_BASE_CELLS)
    box = tuple((V04C_MARGIN, V04C_MARGIN + c) for c in V04_BASE_CELLS)
    counts = {"shell": [0, 0, 0], "box": [0, 0, 0]}
    conflicts = {"shell": 0, "box": 0}
    inner = tuple((lo + 1, hi - 1) for lo, hi in box)
    for a in range(3):
        _, b, c = cyclic(a)
        for index in e_edges(cells, a):
            # Support of the shifted (1,1) mode with polarization a: integer
            # transverse indices strictly inside the cavity, any a index inside.
            support = (box[a][0] <= index[a] < box[a][1] and inner[b][0] <= index[b] <= inner[b][1]
                       and inner[c][0] <= index[c] <= inner[c][1])
            for kind, shell in (("shell", True), ("box", False)):
                marked = pec_marked(a, index, box, shell)
                counts[kind][a] += marked
                conflicts[kind] += marked and support
    require(conflicts["shell"] == 0, "V04-C mode support touches the shell mask")
    require(conflicts["box"] > 0, "solid box must conflict with the cavity mode (S09 rejection case)")
    require(not pec_marked(2, V04C_SOURCE_INSIDE, box, True) and
            all(box[axis][0] < V04C_SOURCE_INSIDE[axis] < box[axis][1] for axis in range(3)),
            "C2 source must be strictly inside and unmasked")
    require(pec_marked(2, V04C_SOURCE_INSIDE, box, False), "C2 source must be masked by the solid box")
    require(any(V04C_SOURCE_OUTSIDE[axis] < box[axis][0] for axis in range(3)) and
            not pec_marked(2, V04C_SOURCE_OUTSIDE, box, True), "C3 source must be outside")
    # The outer closure equals the shell of the whole domain.
    whole = tuple((0, c) for c in cells)
    for a in range(3):
        for index in e_edges(cells, a):
            wall = any(index[axis] in (0, cells[axis]) for axis in range(3) if axis != a)
            require(pec_marked(a, index, whole, True) == wall, "outer closure is the whole-domain shell")
    print("cells=%s shell=%s edges=%d per component %s; solid box edges=%d; mode/solid conflicts=%d; "
          "sources inside=%s outside=%s" % (cells, box, sum(counts["shell"]), counts["shell"],
                                            sum(counts["box"]), conflicts["box"], V04C_SOURCE_INSIDE,
                                            V04C_SOURCE_OUTSIDE))
    return sum(counts["shell"])


# --------------------------------------------------------------------------
# V05 - dielectric propagation, interface and slab-loaded cavity
# --------------------------------------------------------------------------
EPS_R = 4.0
V05A_CAPS = {24: 0.003, 48: 0.00075, 96: 0.0001875}


def v01_like(p, eps_r, q=0.99):
    spacing = tuple(LAMBDA * r / p for r in (1, 1.5, 2))
    cells = (3 * p, 2 * p, 2 * p)
    dt = cfl_dt(spacing, q)
    period = math.sqrt(eps_r) * LAMBDA / C0
    steps = math.floor(0.1 * period / dt)
    k = 2 * PI / LAMBDA
    omega = discrete_omega(dt, kappa(k, spacing[0]), eps_r)
    return spacing, cells, dt, steps, k, omega


def audit_v05_homogeneous():
    print("== V05-A homogeneous dielectric eigenwave (eps_r=%g) ==" % EPS_R)
    errors = []
    work = 0
    for p in (24, 48, 96):
        spacing, cells, dt, steps, k, omega = v01_like(p, EPS_R)
        error = abs(omega * math.sqrt(EPS_R) / (C0 * k) - 1)
        require(error < V05A_CAPS[p], "V05-A cap")
        require(p - 0.5 > 2 * steps + 6, "V05-A isolation guard")
        errors.append(error)
        work += 6 * math.prod(cells) * steps
        print("p=%d steps=%d phase=%.6f rad error=%.12g cap=%g guard %.1f>%d eta=%.9f ohm" %
              (p, steps, omega * steps * dt, error, V05A_CAPS[p], p - 0.5, 2 * steps + 6,
               ETA0 / math.sqrt(EPS_R)))
    orders = [math.log(errors[i] / errors[i+1], 2) for i in (0, 1)]
    require(all(1.8 <= o <= 2.2 for o in orders), "V05-A order")
    print("predicted orders: %s; 18-case cell_steps=%d" % (", ".join("%.9f" % o for o in orders), work))


# ---- V05-B TE-mode interface ----------------------------------------------
V05B_P = (16, 32, 64)
V05B_LC = 2.0 * LAMBDA              # transverse height; TE_1 cutoff at f0/4
V05B_SIGMA_F = 0.15 * F0            # Gaussian spectral width of the pulse
V05B_BAND = (0.75, 1.25)            # analysed band in units of f0
V05B_BAND_POINTS = 21
V05B_LAYOUT = {"back": 15.0, "l1": 2.0, "l2": 8.0, "l3": 2.0, "l4": 5.0}  # in LAMBDA units
V05B_GATE = 15.0                    # T0 units: incident/reflected split at probe 1
V05B_END = 29.0                     # T0 units: end of record
V05B_R_CAPS = {16: 0.06, 32: 0.0135, 64: 0.0034}
V05B_T_CAPS = {16: 0.06, 32: 0.0135, 64: 0.0034}
V05B_DISCRETE_LIMIT = 1e-4
V05B_KC = PI / V05B_LC


def v05b_geometry(p):
    d = (LAMBDA / p, 1.5 * LAMBDA / p, 2 * LAMBDA / p)
    lay = V05B_LAYOUT
    i_src = round(lay["back"] * p)
    i_p1 = i_src + round(lay["l1"] * p)
    i_int = i_p1 + round(lay["l2"] * p)
    i_p2 = i_int + round(lay["l3"] * p)
    n_a = i_p2 + round(lay["l4"] * p)
    n_c = round(V05B_LC / d[2])
    require(abs(n_c * d[2] - V05B_LC) < 1e-12, "V05-B transverse count")
    dt = cfl_dt(d, 0.99)
    steps = math.ceil(V05B_END * T0 / dt)
    gate = math.ceil(V05B_GATE * T0 / dt)
    return {"p": p, "spacing": d, "cells": (n_a, 2, n_c), "i_src": i_src, "i_p1": i_p1, "i_int": i_int,
            "i_p2": i_p2, "dt": dt, "steps": steps, "gate": gate}


def gaussian_pulse(dt, steps):
    tau = 1 / (2 * PI * V05B_SIGMA_F)
    t0 = 4 * tau
    return [math.exp(-(((m + 0.5) * dt - t0) / tau)**2 / 2) * math.cos(2 * PI * F0 * ((m + 0.5) * dt - t0))
            for m in range(steps)]


def beta_continuum(f, eps_r):
    value = eps_r * (2 * PI * f / C0)**2 - V05B_KC**2
    require(value > 0, "below cutoff")
    return math.sqrt(value)



def reduced_wavenumbers(f, geometry):
    d_a, _, d_c = geometry["spacing"]
    dt = geometry["dt"]
    big_omega = 2 / dt * math.sin(PI * f * dt)
    big_kc = kappa(V05B_KC, d_c)
    out = []
    for eps_r in (1.0, EPS_R):
        k2 = eps_r * big_omega**2 / C0**2 - big_kc**2
        require(k2 > 0, "reduced system below cutoff")
        arg = math.sqrt(k2) * d_a / 2
        require(arg < 1, "axial wavenumber not representable")
        out.append(2 / d_a * math.asin(arg))
    return out, big_omega, big_kc


def discrete_reflection(f, geometry):
    """Closed-form discrete R,T of the averaged-node interface (phase origin at the node)."""
    (k1, k2), big_omega, big_kc = reduced_wavenumbers(f, geometry)
    d_a = geometry["spacing"][0]
    eps_avg = (1.0 + EPS_R) / 2 * EPS0
    g = cmath.exp(-1j * k2 * d_a) - 2 - d_a**2 * (big_kc**2 - MU0 * eps_avg * big_omega**2)
    r = -(g + cmath.exp(1j * k1 * d_a)) / (g + cmath.exp(-1j * k1 * d_a))
    return r, 1 + r, k1, k2


def reduced_oracle(geometry, back_extra=0, far_extra=0):
    """Pure-Python time stepping of the reduced TE system with a J_b sheet source."""
    d_a, _, d_c = geometry["spacing"]
    dt, steps = geometry["dt"], geometry["steps"]
    n_a = geometry["cells"][0] + back_extra + far_extra
    shift = back_extra
    i_src, i_p1, i_int, i_p2 = (geometry[k] + shift for k in ("i_src", "i_p1", "i_int", "i_p2"))
    big_kc = kappa(V05B_KC, d_c)
    eps_node = [EPS0] * (n_a + 1)
    for i in range(n_a + 1):
        left = EPS0 * (EPS_R if i - 1 >= i_int else 1.0)
        right = EPS0 * (EPS_R if i >= i_int else 1.0)
        eps_node[i] = (left + right) / 2 if 0 < i < n_a else right
    cb = [dt / e for e in eps_node]
    e = [0.0] * (n_a + 1)
    ha = [0.0] * (n_a + 1)
    hc = [0.0] * n_a
    pulse = gaussian_pulse(dt, steps)
    p1, p2 = [], []
    for n in range(steps):
        for i in range(n_a + 1):
            ha[i] += dt / MU0 * big_kc * e[i]
        for i in range(n_a):
            hc[i] -= dt / MU0 * (e[i+1] - e[i]) / d_a
        for i in range(1, n_a):
            curl = -big_kc * ha[i] - (hc[i] - hc[i-1]) / d_a
            if i == i_src:
                curl -= pulse[n]
            e[i] += cb[i] * curl
        p1.append(e[i_p1])
        p2.append(e[i_p2])
    return p1, p2


def dft_at(series, dt, f, start=0, stop=None):
    stop = len(series) if stop is None else stop
    return dt * sum(series[n] * cmath.exp(-2j * PI * f * (n + 1) * dt) for n in range(start, stop))


def audit_v05_interface():
    print("== V05-B TE-mode dielectric interface (closed-form discrete R/T, oracle isolation) ==")
    band = [F0 * (V05B_BAND[0] + (V05B_BAND[1] - V05B_BAND[0]) * i / (V05B_BAND_POINTS - 1))
            for i in range(V05B_BAND_POINTS)]
    for p in V05B_P:
        g = v05b_geometry(p)
        p1, p2 = reduced_oracle(g)
        p1_long, p2_long = reduced_oracle(g, back_extra=8 * p, far_extra=8 * p)
        scale = max(abs(v) for v in p1)
        isolation = max(max(abs(a - b) for a, b in zip(p1, p1_long)),
                        max(abs(a - b) for a, b in zip(p2, p2_long))) / scale
        require(isolation < 1e-10, "V05-B layout is not isolated from wall returns at p=%d" % p)
        worst_r, worst_t, worst_disc, worst_imag = 0.0, 0.0, 0.0, 0.0
        b1, b2 = beta_continuum(F0, 1.0), beta_continuum(F0, EPS_R)
        r_c0, r_d0 = (b1 - b2) / (b1 + b2), discrete_reflection(F0, g)[0]
        for f in band:
            inc = dft_at(p1, g["dt"], f, 0, g["gate"])
            ref = dft_at(p1, g["dt"], f, g["gate"], g["steps"])
            tra = dft_at(p2, g["dt"], f)
            r_d, t_d, k1, k2 = discrete_reflection(f, g)
            d_a = g["spacing"][0]
            r_m = ref / inc * cmath.exp(2j * k1 * (g["i_int"] - g["i_p1"]) * d_a)
            t_m = tra / inc * cmath.exp(1j * (k1 * (g["i_int"] - g["i_p1"]) + k2 * (g["i_p2"] - g["i_int"])) * d_a)
            b1, b2 = beta_continuum(f, 1.0), beta_continuum(f, EPS_R)
            r_c, t_c = (b1 - b2) / (b1 + b2), 2 * b1 / (b1 + b2)
            worst_disc = max(worst_disc, abs(r_m - r_d), abs(t_m - t_d))
            worst_imag = max(worst_imag, abs(r_d.imag))
            worst_r = max(worst_r, abs(abs(r_m) - abs(r_c)))
            worst_t = max(worst_t, abs(abs(t_m) - abs(t_c)))
        require(worst_disc < V05B_DISCRETE_LIMIT, "gated oracle disagrees with closed-form discrete R/T")
        require(worst_r < V05B_R_CAPS[p] and worst_t < V05B_T_CAPS[p], "V05-B caps at p=%d" % p)
        require(worst_imag < V05B_DISCRETE_LIMIT, "closed-form discrete R is not real")
        print("p=%d cells=%s steps=%d gate=%d dt=%.6g |R_c(f0)|=%.6f |R_d(f0)|=%.6f oracle-vs-closed-form %.2e "
              "max|Im R_d| %.1e isolation %.1e worst |R| error %.6g cap %g worst |T| error %.6g cap %g cell_steps=%d" %
              (p, g["cells"], g["steps"], g["gate"], g["dt"], abs(r_c0), abs(r_d0), worst_disc, worst_imag,
               isolation, worst_r, V05B_R_CAPS[p], worst_t, V05B_T_CAPS[p], math.prod(g["cells"]) * g["steps"]))


# ---- V05-C slab-loaded TE cavity -------------------------------------------
V05C_P = (24, 48, 96)
V05C_LA, V05C_LINT = LAMBDA, LAMBDA / 2
V05C_CAPS = {(1, 24): 0.00038, (1, 48): 0.000095, (1, 96): 0.000024,
             (2, 24): 0.0055, (2, 48): 0.0014, (2, 96): 0.00035}


def v05c_geometry(p):
    d = (LAMBDA / p, 2 * LAMBDA / p, LAMBDA / p)
    n_a = round(V05C_LA / d[0])
    i_int = round(V05C_LINT / d[0])
    n_c = round(V05B_LC / d[2])
    return {"p": p, "spacing": d, "cells": (n_a, 2, n_c), "i_int": i_int, "dt": cfl_dt(d, 0.99)}


def bisect(function, lo, hi, iterations=200):
    flo = function(lo)
    require(flo * function(hi) < 0, "root not bracketed")
    for _ in range(iterations):
        mid = (lo + hi) / 2
        fmid = function(mid)
        if fmid == 0:
            return mid
        if flo * fmid < 0:
            hi = mid
        else:
            lo, flo = mid, fmid
    return (lo + hi) / 2


def slab_continuum(f):
    """Pole-free TE slab-cavity characteristic function (roots are modes)."""
    b1, b2 = beta_continuum(f, 1.0), beta_continuum(f, EPS_R)
    l1, l2 = V05C_LINT, V05C_LA - V05C_LINT
    return b1 * math.cos(b1 * l1) * math.sin(b2 * l2) + b2 * math.sin(b1 * l1) * math.cos(b2 * l2)


def slab_discrete(f, g):
    """Pole-free discrete characteristic function of the averaged-node slab cavity."""
    (k1, k2), big_omega, big_kc = reduced_wavenumbers(f, g)
    d_a = g["spacing"][0]
    n_a, i_int = g["cells"][0], g["i_int"]
    eps_avg = (1.0 + EPS_R) / 2 * EPS0
    # e[i]=sin(k1 i d) for i<=i_int and B sin(k2 (n_a-i) d) for i>=i_int; the node
    # equation at i_int with the averaged permittivity, multiplied by s2, closes it.
    s1, s2 = math.sin(k1 * i_int * d_a), math.sin(k2 * (n_a - i_int) * d_a)
    left = math.sin(k1 * (i_int - 1) * d_a)
    right = math.sin(k2 * (n_a - i_int - 1) * d_a)
    c = big_kc**2 - MU0 * eps_avg * big_omega**2
    return (s1 * right - 2 * s1 * s2 + s2 * left) / d_a**2 - c * s1 * s2


def roots(function, start, step, limit, count):
    found = []
    lo, flo = start, function(start)
    while len(found) < count:
        hi = lo + step
        require(hi < limit, "no root found")
        fhi = function(hi)
        if flo * fhi < 0:
            found.append(bisect(function, lo, hi))
        lo, flo = hi, fhi
    return found


def audit_v05_slab():
    print("== V05-C slab-loaded TE cavity (continuum and discrete transcendental modes) ==")
    f_cut1 = V05B_KC * C0 / 2 / PI
    continuum = roots(slab_continuum, f_cut1 * 1.001, 1e6, 5 * F0, 2)
    work = 0
    for mode, f_c in enumerate(continuum, start=1):
        errors = []
        for p in V05C_P:
            g = v05c_geometry(p)
            f_d = roots(lambda f: slab_discrete(f, g), f_cut1 * 1.001, 1e6, 5 * F0, mode)[mode - 1]
            error = abs(f_d / f_c - 1)
            require(error < V05C_CAPS[mode, p], "V05-C cap at mode %d p=%d" % (mode, p))
            errors.append(error)
            steps = math.ceil(V04_PERIODS / f_c / g["dt"])
            work += 3 * math.prod(g["cells"]) * steps
            print("mode=%d p=%d cells=%s i_int=%d f_c=%.6f GHz f_d=%.6f GHz error=%.9g cap=%g steps=%d" %
                  (mode, p, g["cells"], g["i_int"], f_c / 1e9, f_d / 1e9, error, V05C_CAPS[mode, p], steps))
        orders = [math.log(errors[i] / errors[i+1], 2) for i in (0, 1)]
        require(all(1.8 <= o <= 2.2 for o in orders), "V05-C order")
        print("  predicted orders: %s" % ", ".join("%.9f" % o for o in orders))
    print("V05-C 18-case cell_steps=%d" % work)
    return work


# --------------------------------------------------------------------------
# V06 - constant conductivity
# --------------------------------------------------------------------------
V06_SIGMAS = (0.01, 0.1)   # S/m
V06_DECAY_CAPS = {(24, 0.01): 8.5e-6, (48, 0.01): 2.1e-6, (96, 0.01): 5.3e-7,
                  (24, 0.1): 8.5e-4, (48, 0.1): 2.1e-4, (96, 0.1): 5.3e-5}
V06_PHASE_CAPS = {24: 0.0035, 48: 0.0009, 96: 0.00022}
V06_DISCRETE_LIMIT = 1e-9


def lossy_step_root(dt, big_k, eps, sigma):
    """Exact per-step complex growth factor z of the lossy discrete eigenwave."""
    a = eps + sigma * dt / 2
    b = -2 * eps + dt * dt * big_k * big_k / MU0
    c = eps - sigma * dt / 2
    disc = b * b - 4 * a * c
    require(disc < 0, "V06 case is not oscillatory")
    return (-b + 1j * math.sqrt(-disc)) / (2 * a)


def modal_recursion(dt, big_k, eps, sigma, steps, z):
    """Two-amplitude transcription of the lossy update for one spatial harmonic.

    Returns the worst abs(ratio/z-1) over the record for the exact lossy
    initialization and for the lossless one (E at 0, H at -dt/2 from omega_d).
    """
    x = sigma * dt / (2 * eps)
    ca, cb = (1 - x) / (1 + x), (dt / eps) / (1 + x)
    z0 = cmath.exp(1j * discrete_omega(dt, big_k, eps / EPS0))
    results = []
    for root in (z, z0):
        h = (1j * dt * big_k / MU0) / (root**0.5 - root**-0.5) * root**-0.5
        e, worst = 1 + 0j, 0.0
        for _ in range(steps):
            h += (1j * dt * big_k / MU0) * e
            e_new = ca * e + cb * 1j * big_k * h
            worst = max(worst, abs(e_new / e / z - 1))
            e = e_new
        results.append(worst)
    return results[0], results[1]


def audit_v06():
    print("== V06-A lossy eigenwave (exact discrete growth factor vs continuum decay/phase) ==")
    eps = EPS_R * EPS0
    for sigma in V06_SIGMAS:
        decay_errors, phase_errors = [], []
        for p in (24, 48, 96):
            spacing, cells, dt, steps, k, _ = v01_like(p, EPS_R)
            alpha = sigma / (2 * eps)
            omega0 = C0 * k / math.sqrt(EPS_R)
            omega_l = math.sqrt(omega0**2 - alpha**2)
            z = lossy_step_root(dt, kappa(k, spacing[0]), eps, sigma)
            decay_m, phase_m = -math.log(abs(z)) / dt, cmath.phase(z) / dt
            decay_error = abs(decay_m / alpha - 1)
            phase_error = abs(phase_m / omega_l - 1)
            x = sigma * dt / (2 * eps)
            require(abs(abs(z) - math.sqrt((1 - x) / (1 + x))) < 1e-15, "exact modulus identity")
            require(decay_error < V06_DECAY_CAPS[p, sigma] and phase_error < V06_PHASE_CAPS[p], "V06 caps")
            require(abs(z)**steps >= 0.6, "amplitude floor over the record")
            decay_errors.append(decay_error)
            phase_errors.append(phase_error)
            worst_lossy, worst_lossless = modal_recursion(dt, kappa(k, spacing[0]), eps, sigma, steps, z)
            require(worst_lossy < 1e-12, "exact lossy initialization must reproduce z at every step")
            require(worst_lossless > V06_DISCRETE_LIMIT, "lossless initialization must be rejected")
            if p == 24:
                print("  modal recursion: lossy-initialized ratio/z-1 %.2e; lossless-initialized %.2e "
                      "(first ratio (z0-x)/(1+x))" % (worst_lossy, worst_lossless))
            print("sigma=%g p=%d x=sigma*dt/(2eps)=%.4g alpha=%.6g 1/s omega'=%.6g decay_error=%.6g cap=%g "
                  "phase_error=%.6g cap=%g final_amplitude=%.4f" %
                  (sigma, p, x, alpha, omega_l, decay_error, V06_DECAY_CAPS[p, sigma], phase_error,
                   V06_PHASE_CAPS[p], abs(z)**steps))
        for errors in (decay_errors, phase_errors):
            orders = [math.log(errors[i] / errors[i+1], 2) for i in (0, 1)]
            require(all(1.8 <= o <= 2.2 for o in orders), "V06 order")
    # Exact algebra of the lossy staggered invariant on one mode: h'=h-a e,
    # e'=Ca e + Cb a h', dissipation D = sigma-term with the time-centred field.
    from fractions import Fraction as Q
    checks = 0
    for e in (Q(-3, 7), Q(4, 9)):
        for h in (Q(-2, 5), Q(1, 3)):
            for a in (Q(1, 10), Q(99, 50)):
                for x in (Q(0), Q(1, 20), Q(1, 3)):
                    ca, cb = (1 - x) / (1 + x), 1 / (1 + x)
                    hn = h - a * e
                    en = ca * e + cb * a * hn
                    q_old = e * e + h * h - a * e * h
                    q_new = en * en + hn * hn - a * en * hn
                    ebar = (en + e) / 2
                    require(q_new - q_old == -4 * x * ebar * ebar, "lossy invariant algebra")
                    checks += 1
    print("PASS: %d exact modal dissipation identities (Q_new-Q_old=-4x*Ebar^2 in modal units)" % checks)
    # V06-B closed-grid dissipation budget on the V03 grid.
    spacing = (0.01, 0.015, 0.02)
    dt = cfl_dt(spacing, 0.99)
    eps_b = 2.25 * EPS0
    alpha = 0.01 / (2 * eps_b)
    print("V06-B cells=(12,14,16) eps_r=2.25 sigma=0.01 S/m q=0.99 dt=%.6g alpha*N*dt=%.3f over 2000 steps "
          "(x=%.4g)" % (dt, alpha * 2000 * dt, 0.01 * dt / (2 * eps_b)))


# --------------------------------------------------------------------------
# V07 - spectral processing on synthetic signals
# --------------------------------------------------------------------------
def dft_direct(values, times, f, dt):
    return dt * sum(x * cmath.exp(-2j * PI * f * t) for x, t in zip(values, times))


def audit_v07():
    print("== V07 synthetic spectra (closed forms, native times, window, FFT vs direct) ==")
    dt, n = 2.5e-11, 4096
    times = [i * dt for i in range(n)]
    worst = 0.0
    # 1. Sinusoid, rectangular window, closed-form geometric sum at on- and off-bin f.
    f1, phi = 17 / (n * dt), 0.3
    x = [math.cos(2 * PI * f1 * t + phi) for t in times]
    for f in (f1, f1 + 0.37 / (n * dt), 3 * f1):
        exact = 0
        for sign in (1, -1):
            ratio = cmath.exp(2j * PI * (sign * f1 - f) * dt)
            exact += 0.5 * cmath.exp(1j * sign * phi) * (n if abs(ratio - 1) < 1e-15 else (1 - ratio**n) / (1 - ratio))
        exact *= dt
        worst = max(worst, abs(dft_direct(x, times, f, dt) - exact) / (n * dt / 2))
    # 2. H native times: same sinusoid sampled at (i-1/2)dt equals E-time transform times exp(+i pi f dt).
    h_times = [(i - 0.5) * dt for i in range(n)]
    xh = [math.cos(2 * PI * f1 * t + phi) for t in h_times]
    worst = max(worst, abs(dft_direct(xh, h_times, f1, dt) - dft_direct(x, times, f1, dt)) / (n * dt / 2))
    # 3. Gaussian pulse against the continuous transform; truncation/aliasing bounded.
    tau, t0 = 40 * dt, n * dt / 2
    g = [math.exp(-((t - t0) / tau)**2 / 2) for t in times]
    for f in (0.0, 1 / (20 * tau), 1 / (8 * tau)):
        exact = math.sqrt(2 * PI) * tau * math.exp(-2 * (PI * f * tau)**2) * cmath.exp(-2j * PI * f * t0)
        worst = max(worst, abs(dft_direct(g, times, f, dt) - exact) / (math.sqrt(2 * PI) * tau))
    # 4. Parseval for the rectangular window on bin frequencies (FFT path).
    spectrum = fft([complex(v) for v in x])
    energy_t = dt * math.fsum(v * v for v in x)
    energy_f = math.fsum(abs(v)**2 for v in spectrum) * dt / n
    worst = max(worst, abs(energy_t - energy_f) / energy_t)
    # 5. FFT against the direct sum at every bin.
    worst = max(worst, max(abs(spectrum[m] * dt - dft_direct(x, times, m / (n * dt), dt))
                           for m in range(0, n, 97)) / (n * dt / 2))
    # 6. Hann coherent gain: on-bin peak magnitude equals 0.5*(n dt)/2.
    w = hann(n)
    peak = dft_direct([v * ww for v, ww in zip(x, w)], times, f1, dt)
    worst = max(worst, abs(abs(peak) / (0.5 * n * dt / 2) - 1))
    print("worst normalized closed-form/transform discrepancy: %.3g" % worst)
    require(worst < 1e-12, "V07 synthetic transform precision")
    # 7. Two-tone peak interpolation at four-bin separation with unequal amplitudes.
    bin_hz = 1 / (n * dt)
    fa, fb = 301.3 * bin_hz, 305.3 * bin_hz
    y = [math.cos(2 * PI * fa * t + 0.7) + 0.3 * math.cos(2 * PI * fb * t - 1.1) for t in times]
    _, peaks = spectral_peaks(y, dt)
    offsets = [min(abs(pk[0] - f) for pk in peaks[:2]) / bin_hz for f in (fa, fb)]
    print("two-tone (1.0 and 0.3 amplitudes, 4-bin separation) peak offsets: %.4f, %.4f bins" % tuple(offsets))
    require(max(offsets) < V04B_PEAK_BIN_LIMIT, "peak interpolation worse than the fixed 0.25-bin limit")


def audit_resources(work_v04a, work_v04b, work_v05c):
    """Calculated budget rows for the specification; cell-steps are not runtime."""
    print("== Resource budget (calculated; cells x steps, eight bytes per field sample) ==")
    rows = []
    rows.append(("V04-A cavity", 30, cavity(4)[0], work_v04a))
    rows.append(("V04-B cavity-spectrum", 1, cavity(1)[0], work_v04b))
    pec_cells = tuple(c + 6 for c in V04_BASE_CELLS)
    m = cavity_mode(1, 0, 1, 1)
    rows.append(("V04-C pec", 5, pec_cells, 3 * math.prod(pec_cells) * m["steps"] + 2 * math.prod(pec_cells) * 4096))
    work = 0
    for p in (24, 48, 96):
        _, cells, _, steps, _, _ = v01_like(p, EPS_R)
        work += 6 * math.prod(cells) * steps
    rows.append(("V05-A dielectric", 18, v01_like(96, EPS_R)[1], work))
    work = 0
    for p, orientations in ((16, 3), (32, 3), (64, 1)):
        g = v05b_geometry(p)
        work += orientations * math.prod(g["cells"]) * g["steps"]
    rows.append(("V05-B interface", 7, v05b_geometry(64)["cells"], work))
    rows.append(("V05-C slab-cavity", 18, v05c_geometry(96)["cells"], work_v05c))
    work = 0
    for p, orderings in ((24, 6), (48, 6), (96, 1)):
        _, cells, _, steps, _, _ = v01_like(p, EPS_R)
        work += 2 * orderings * math.prod(cells) * steps
    rows.append(("V06-A lossy", 26, v01_like(96, EPS_R)[1], work))
    rows.append(("V06-B dissipation", 2, (12, 14, 16), 2 * 12 * 14 * 16 * 2000))
    rows.append(("V06-C regression (V01-V03)", 40, (288, 192, 192), 865603584 + 215083008))
    total = 0
    for name, cases, cells, work in rows:
        total += work
        print("%-28s cases=%2d largest_cells=%-16s field_MiB=%8.3f cell_steps=%d" %
              (name, cases, cells, mib(cells), work))
    print("P2 suites total cell_steps=%d (P1 suites: %d)" % (total, 865603584 + 215083008))


def main():
    print("MAT-01 v1: DETERMINISTIC ANALYTICAL CALCULATIONS; NOT SOLVER RESULTS")
    print("c0=%.0f eta0=%.12f epsilon0=%.15g" % (C0, ETA0, EPS0))
    work_v04a = audit_v04_eigenmodes()
    work_v04b = audit_v04_spectrum()
    audit_v04_enforcement()
    audit_v05_homogeneous()
    audit_v05_interface()
    work_v05c = audit_v05_slab()
    audit_v06()
    audit_v07()
    audit_resources(work_v04a, work_v04b, work_v05c)
    print("PASS: V04-V07 predictions within fixed caps; guards, estimators and fault detection checked")
    print("LIMIT: no 3D fixture, kernel, physical benchmark, PEC mask or material array executed")


if __name__ == "__main__":
    main()
