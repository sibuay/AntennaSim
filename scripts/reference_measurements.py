"""Independent native harmonic measurements (FND-04 S07 / future V01-V02).

No solver/fixture imports. k and locations are inputs, omega is measured later.
"""
import cmath
import math


def fit_harmonic(samples, k, minimum_samples, amplitude_floor):
    samples = list(samples)
    if (minimum_samples < 2 or len(samples) < minimum_samples or
            not math.isfinite(k) or k <= 0 or
            not math.isfinite(amplitude_floor) or amplitude_floor <= 0 or
            any(not math.isfinite(x) or not math.isfinite(y) for x, y in samples)):
        raise ValueError("Invalid/missing native harmonic samples")
    rows = [(math.cos(k*x), math.sin(k*x), y) for x, y in samples]
    cc = math.fsum(c*c for c, s, y in rows)
    ss = math.fsum(s*s for c, s, y in rows)
    cs = math.fsum(c*s for c, s, y in rows)
    yc = math.fsum(y*c for c, s, y in rows)
    ys = math.fsum(y*s for c, s, y in rows)
    gap = math.hypot(cc-ss, 2*cs)
    low, high = (cc+ss-gap)/2, (cc+ss+gap)/2
    if low <= 0 or math.sqrt(high/low) >= 2:
        raise ValueError("Ill-conditioned harmonic fit")
    det = cc*ss-cs*cs
    coefficient = complex((yc*ss-ys*cs)/det, (ys*cc-yc*cs)/det)
    if (not math.isfinite(coefficient.real) or not math.isfinite(coefficient.imag)
            or abs(coefficient) < amplitude_floor):
        raise ValueError("Weak/nonfinite harmonic coefficient")
    residual = max(abs(y-coefficient.real*c-coefficient.imag*s) for c, s, y in rows)
    return coefficient, residual, math.sqrt(high/low)


def native_impedance(e_fit, h_fit, e_time, h_time, omega, h_floor):
    if (not all(math.isfinite(v) for v in
                (e_fit.real, e_fit.imag, h_fit.real, h_fit.imag, e_time, h_time, omega, h_floor))
            or h_floor <= 0 or abs(h_fit) < h_floor):
        raise ValueError("Weak/nonfinite impedance input")
    value = (e_fit*cmath.exp(-1j*omega*e_time))/(h_fit*cmath.exp(-1j*omega*h_time))
    if not math.isfinite(value.real) or not math.isfinite(value.imag):
        raise ValueError("Nonfinite impedance")
    return value
