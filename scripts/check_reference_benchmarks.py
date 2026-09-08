"""FND-04 analytical specification audit; no field evolution or solver import.

Python 3.9+, standard library only. Prints deterministic predictions, not measured
solver accuracy. See docs/validation/FND-04-reference-benchmarks.md, version 1.
"""

import cmath
from fractions import Fraction as Q
from itertools import product
import math

from check_yee_conventions import PLACEMENT, STENCIL, extents


C0 = 299792458.0
MU0 = 1.25663706127e-6
ETA0 = C0 * MU0
LAMBDA = 0.3


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def field_count(cells):
    x, y, z = cells
    return (x*(y+1)*(z+1) + (x+1)*y*(z+1) + (x+1)*(y+1)*z
            + (x+1)*y*z + x*(y+1)*z + x*y*(z+1))


def parameters(p, q=0.99, cubic=False):
    spacing = tuple(LAMBDA*r/p for r in ((1, 1, 1) if cubic else (1, 1.5, 2)))
    cells = (3*p, 3*p, 4*p) if cubic else (3*p, 2*p, 2*p)
    dt = q / (C0 * math.sqrt(sum(1/d**2 for d in spacing)))
    steps = math.floor(0.1 * LAMBDA / C0 / dt)
    k = 2*math.pi/LAMBDA
    omega = 2/dt * math.asin(C0*dt/spacing[0]*math.sin(k*spacing[0]/2))
    return spacing, cells, dt, steps, k, omega


def fit(samples, k):
    cc = ss = cs = yc = ys = 0.0
    for x, y in samples:
        c, s = math.cos(k*x), math.sin(k*x)
        cc += c*c
        ss += s*s
        cs += c*s
        yc += y*c
        ys += y*s
    det = cc*ss-cs*cs
    require(det > 0.1*cc*ss, "Ill-conditioned synthetic fit")
    return complex((yc*ss-ys*cs)/det, (ys*cc-yc*cs)/det)


def synthetic_fit_check(p, q):
    spacing, _, dt, n, k, omega = parameters(p, q)
    errors = []
    for direction in (-1, 1):
        electric = []
        for time in (0, n*dt):
            electric.append(fit([
                (i*spacing[0], math.cos(k*i*spacing[0]-direction*omega*time))
                for i in range(p, 2*p)], k))
        omega_measured = cmath.phase(electric[1]/electric[0])/(n*dt)
        require(abs(omega_measured/(direction*omega)-1) < 1e-12,
                "Synthetic phase-speed estimator")
        for sign in (-1, 1):
            amplitudes = []
            for offset, time, amplitude in ((0, n*dt, 1),
                                            (0.5, (n-0.5)*dt, sign/ETA0)):
                samples = []
                for i in range(p, 2*p):
                    x = (i+offset)*spacing[0]
                    samples.append((x, amplitude*math.cos(k*x-direction*omega*time)))
                amplitudes.append(fit(samples, k) * cmath.exp(-1j*omega_measured*time))
            z = amplitudes[0]/amplitudes[1]
            errors.append(abs(z/(sign*ETA0)-1))
    require(max(errors) < 1e-12, "Native-time signed impedance estimator")
    return max(errors)


def adjoint_check():
    # Reuse the *specification transcription*, never production code. This
    # checks finite-box summation by parts, not an implemented kernel.
    for cells in ((2, 3, 4), (5, 4, 3)):
        data = {}
        weights = {}
        names = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
        for component_id, name in enumerate(names):
            data[name] = {}
            for idx in product(*(range(s) for s in extents(name, cells))):
                faces = sum(PLACEMENT[name][a] == 0 and idx[a] in (0, cells[a])
                            for a in range(3))
                value = (17*idx[0]+31*idx[1]+43*idx[2]+13*component_id) % 101-50
                data[name][idx] = Q(0 if faces else value)
                weights[name, idx] = Q(1, 2**faces)
        dots = {"E": Q(0), "H": Q(0)}
        for name in names:
            for idx, value in data[name].items():
                if value == 0:
                    continue
                curl = Q(0)
                for sign, source, high, low, axis in STENCIL[name]:
                    hi = tuple(idx[a]+high[a] for a in range(3))
                    lo = tuple(idx[a]+low[a] for a in range(3))
                    curl += sign*(data[source][hi]-data[source][lo])/(2, 3, 5)[axis]
                if name[0] == "H":
                    curl = -curl  # H update stores minus curl E.
                dots[name[0]] += weights[name, idx]*value*curl
        require(dots["E"] == dots["H"] and dots["E"] != 0,
                "Nontrivial weighted adjoint identity")
        print("PASS: exact weighted curl adjoint cells=%s dot=%s" % (cells, dots["E"]))


def main():
    print("FND-04 v1: DETERMINISTIC ANALYTICAL CALCULATIONS; NOT SOLVER RESULTS")
    print("c0=%.0f eta0=%.12f epsilon0=%.15g" % (C0, ETA0, 1/(MU0*C0*C0)))
    continuum_errors = []
    total_work = 0
    worst_fit = 0.0
    for p, cap in ((24, 0.0015), (48, 0.000375), (96, 0.00009375)):
        spacing, cells, dt, n, k, omega = parameters(p)
        error = abs(omega/(C0*k)-1)
        continuum_errors.append(error)
        require(error < cap, "Predicted dispersion exceeds fixed continuum cap")
        # Half a cell accommodates either native line placement. A two-edge
        # dependency expansion per step plus six cells is deliberately generous.
        distance = min(p-0.5, p-0.5, p-0.5)
        require(distance > 2*n+6, "All-face isolation guard")
        work = math.prod(cells)*n
        total_work += 6*work
        worst_fit = max(worst_fit, synthetic_fit_check(p, 0.99))
        print("p=%d cells=%s dt=%.12g steps=%d phase=%.9f error=%.12g cap=%.9g "
              "guard=%.1f>%d field_MiB=%.6f cell_steps=%d" %
              (p, cells, dt, n, omega*n*dt, error, cap, distance, 2*n+6,
               8*field_count(cells)/2**20, work))
    orders = [math.log(continuum_errors[i]/continuum_errors[i+1], 2) for i in (0, 1)]
    require(all(1.8 <= order <= 2.2 for order in orders), "Refinement order budget")
    print("predicted refinement orders:", ", ".join("%.9f" % x for x in orders))
    for q, cubic in ((0.5, False), (0.99, True)):
        spacing, cells, dt, n, k, omega = parameters(24, q, cubic)
        require(23.5 > 2*n+6, "Sensitivity isolation guard")
        total_work += 6*math.prod(cells)*n
        error = abs(omega/(C0*k)-1)
        require(error < 0.003, "Sensitivity continuum cap")
        if not cubic:
            worst_fit = max(worst_fit, synthetic_fit_check(24, q))
        print("sensitivity q=%.2f cubic=%s steps=%d error=%.12g field_MiB=%.6f" %
              (q, cubic, n, error, 8*field_count(cells)/2**20))
    # Enlarged-domain runs add two wavelength margins on each side, at p=24.
    enlarged = (7*24, 14*24//3, 4*24)
    n = parameters(24)[3]
    total_work += 6*math.prod(enlarged)*n
    print("enlarged cells=%s field_MiB=%.6f" %
          (enlarged, 8*field_count(enlarged)/2**20))
    print("V01/V02 36-case total cell_steps=%d (not runtime)" % total_work)
    print("synthetic native-fit maximum normalized error=%.3g" % worst_fit)
    # Exact one-mode algebra of staggered invariant: h'=h-ae, e'=e+ah'.
    # This checks the sign/time convention, not the full grid adjoint identity.
    checks = 0
    for e in (Q(-3, 7), Q(0), Q(4, 9)):
        for h in (Q(-2, 5), Q(1, 3)):
            for a in (Q(1, 10), Q(1), Q(99, 50)):
                hn = h-a*e
                en = e+a*hn
                require(e*e+h*h-a*e*h == en*en+hn*hn-a*en*hn,
                        "Staggered invariant algebra")
                checks += 1
    print("PASS: %d exact modal invariant identities" % checks)
    adjoint_check()
    print("V03 cells=(12,14,16) field_MiB=%.6f total_cell_steps=%d" %
          (8*field_count((12, 14, 16))/2**20, 2*12*14*16*(20000+20008)))
    print("PASS: analytic budgets, all-face guards, signed fits, invariant algebra")
    print("LIMIT: no 3D fixture, kernel, physical benchmark, or long-time run executed")


if __name__ == "__main__":
    main()
