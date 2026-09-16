"""REF-05 reduction validation before physical results are accepted.

1. Synthetic pass/failure-detection checks of the analyzer's V01/V02/V03
   reductions on prescribed data (no solver output).
2. With --app: run the CLI smoke suite and compare its stability diagnostics and
   centre probes with an independent pure-Python transcription of the FND-03
   update equations, the V03 fixture and the FND-04 weighted U/Q diagnostic, and
   apply the V01/V02 measurements to the two-step propagation smoke case.

Python 3.9+, standard library. No production operator is imported.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import json

from analyze_reference_benchmarks import (analyze_propagation, analyze_stability, check_resources,
                                          compare_enlarged, discrete_frequency, expected_case, load_case,
                                          refinement, K, NAMES, ETA0, C0)

MU0 = 1.25663706127e-6
EPS0 = 1/(MU0*C0*C0)
PI = math.pi


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def half_offsets(id):
    return [0.5 if (axis == id if id < 3 else axis != id-3) else 0.0 for axis in range(3)]


def synthetic_case(a, b, p=24, variant="primary", omega=None, amplitude=1.0, h_sign=1, direction=1,
                   inactive=0.0, drop=None, steps=None):
    spec = expected_case(a, b, p, variant)
    steps = spec["steps"] if steps is None else steps
    meta = {"case": spec["case"], "a": a, "b": b, "p": p, "q": spec["q"], "dt_s": spec["dt_s"], "steps": steps,
            "cells": spec["cells"], "spacing_m": spec["spacing_m"], "enlarged": variant == "enlarged",
            "propagation": True, "driven": False, "elapsed_seconds": 0.0}
    c = 3-a-b
    sign = 1 if (a+1) % 3 == b else -1
    dt, spacing, cells = spec["dt_s"], spec["spacing_m"], spec["cells"]
    omega = discrete_frequency(dt, spacing[a]) if omega is None else omega
    shift = 0.6 if variant == "enlarged" else 0.0
    rows = []
    for n in range(steps+1):
        for id in range(6):
            half = half_offsets(id)
            for axial in range(p, 2*p):
                index = [cells[0]//2, cells[1]//2, cells[2]//2]
                index[a] = axial+(2*p if variant == "enlarged" else 0)
                position = [(index[axis]+half[axis])*spacing[axis] for axis in range(3)]
                time = (n-(0 if id < 3 else 0.5))*dt
                phase = K*(position[a]-shift)-direction*omega*time
                if id == b:
                    value = amplitude*math.cos(phase)
                elif id == c+3:
                    value = h_sign*sign*amplitude/ETA0*math.cos(phase)
                else:
                    value = inactive
                rows.append({"state": str(n), "component": NAMES[id], "i": str(index[0]), "j": str(index[1]),
                             "k": str(index[2]), "x_m": repr(position[0]), "y_m": repr(position[1]),
                             "z_m": repr(position[2]), "time_s": repr(time), "value": repr(value)})
    if drop is not None:
        del rows[drop]
    return meta, rows


def has_failure(metrics, text):
    return any(text in failure for failure in metrics["failures"])


def synthetic_propagation():
    checks = 0
    worst = {"continuum": 0.0, "discrete": 0.0, "impedance": 0.0}
    for a in range(3):
        for b in range(3):
            if a == b:
                continue
            for p, variant in ((24, "primary"), (48, "primary"), (96, "primary"), (24, "enlarged"),
                               (24, "half-q"), (24, "cubic")):
                meta, rows = synthetic_case(a, b, p, variant)
                metrics, trace = analyze_propagation(meta, rows)
                require(metrics["status"] == "pass", "synthetic %s: %s" % (meta["case"], metrics["failures"]))
                require(len(trace) == meta["steps"]+1, "trace per state")
                worst["continuum"] = max(worst["continuum"],
                                         abs(metrics["continuum_error"]-metrics["predicted_continuum_error"]))
                worst["discrete"] = max(worst["discrete"], metrics["discrete_error"])
                worst["impedance"] = max(worst["impedance"], metrics["max_impedance_error"])
                checks += 1
    require(worst["continuum"] <= 1e-12 and worst["discrete"] <= 1e-12 and worst["impedance"] <= 1e-12,
            "synthetic measurement precision")
    a, b = 1, 2
    omega = discrete_frequency(expected_case(a, b, 24, "primary")["dt_s"], 0.3/24)
    cases = [
        (dict(omega=omega*(1+3e-9)), "discrete frequency error"),
        (dict(amplitude=1+2e-9), "fitted amplitude error"),
        (dict(h_sign=-1), "complex impedance error"),
        (dict(direction=-1), "measured frequency not positive"),
        (dict(inactive=2e-9), "inactive line samples"),
        (dict(drop=5), "native samples"),
        (dict(steps=2), "differ from v1"),
        (dict(omega=omega*1.005), "continuum phase-speed error"),
    ]
    for kwargs, text in cases:
        meta, rows = synthetic_case(a, b, **kwargs)
        metrics, _ = analyze_propagation(meta, rows)
        require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected: " + text)
        checks += 1
    meta, rows = synthetic_case(a, b, steps=2)
    metrics, _ = analyze_propagation(meta, rows, fixed_suite=False)
    require(metrics["status"] == "pass", "smoke-length synthetic")
    meta, rows = synthetic_case(a, b)
    meta["cells"][0] += 1
    require(has_failure(analyze_propagation(meta, rows)[0], "cells"), "geometry mismatch undetected")
    meta, rows = synthetic_case(a, b)
    rows[3]["time_s"] = repr(float(rows[3]["time_s"])+1e-13)
    require(has_failure(analyze_propagation(meta, rows)[0], "mixes sample times"), "time mismatch undetected")
    # A consistently relocated line (index and coordinate) still lies in the uniform
    # plateau; only the prescribed-line check can reject it.
    meta, rows = synthetic_case(a, b)
    for row in rows:
        if row["component"] == "Ey":
            row["i"] = str(int(row["i"])+3)
            row["x_m"] = repr(float(row["x_m"])+3*meta["spacing_m"][0])
    require(has_failure(analyze_propagation(meta, rows)[0], "prescribed native line"), "relocated line undetected")
    checks += 4
    # Refinement and enlarged comparisons.
    errors = {p: abs(discrete_frequency(expected_case(a, b, p, "primary")["dt_s"], 0.3/p)/(K*C0)-1)
              for p in (24, 48, 96)}
    result = refinement(errors)
    require(result["status"] == "pass" and all(1.8 <= o <= 2.2 for o in result["orders"]), "refinement pass")
    for bad in ({24: 1e-3, 48: 3e-4, 96: 1.5e-4}, {24: 1e-3, 48: 1e-3, 96: 2.5e-4}, {24: 0.0, 48: 0.0, 96: 0.0},
                {24: 1e-3, 48: None, 96: 1e-4}, {24: 1e-3, 48: 2.5e-4, 96: 1.2e-4}):
        require(refinement(bad)["status"] == "fail", "undetected refinement failure %s" % bad)
    checks += 6
    primary = synthetic_case(a, b, 24, "primary")
    enlarged = synthetic_case(a, b, 24, "enlarged")
    result = compare_enlarged(primary, enlarged)
    require(result["status"] == "pass" and result["matched_samples"] == 144*4 and result["shift_cells"] == [
        48 if a == 0 else 32 if b == 0 else 24, 48 if a == 1 else 32 if b == 1 else 24,
        48 if a == 2 else 32 if b == 2 else 24] and result["max_normalized_difference"] <= 1e-14,
        "enlarged synthetic pass")
    perturbed = synthetic_case(a, b, 24, "enlarged")
    perturbed[1][7]["value"] = repr(float(perturbed[1][7]["value"])+2e-10)
    require(compare_enlarged(primary, perturbed)["status"] == "fail", "enlarged perturbation undetected")
    short = (primary[0], primary[1][:-1])
    require(compare_enlarged(short, enlarged)["status"] == "fail", "unmatched enlarged sample undetected")
    checks += 3
    print("PASS synthetic V01/V02 reductions: %d checks; worst continuum/discrete/impedance deviation %.3g/%.3g/%.3g"
          % (checks, worst["continuum"], worst["discrete"], worst["impedance"]))
    return checks


def resource_and_retention_checks():
    checks = 0
    good = {"suites": {"propagation": {"status": 0, "peak_working_set_bytes": 10**9}}}
    require(check_resources(good, ["propagation"])["status"] == "pass", "resource pass")
    for bad in (None, {"suites": {}},
                {"suites": {"propagation": {"status": 2, "peak_working_set_bytes": 10**9}}},
                {"suites": {"propagation": {"status": 0, "peak_working_set_bytes": None}}},
                {"suites": {"propagation": {"status": 0, "peak_working_set_bytes": 2**31+1}}}):
        require(check_resources(bad, ["propagation"])["status"] == "fail", "undetected resource fault %s" % (bad,))
    checks += 6
    # A corrupt metadata file must still produce a written failure report.
    root = Path(tempfile.mkdtemp(prefix="ref05-retention-"))
    suite = root/"stability"
    (suite/"stable-q50-initial").mkdir(parents=True)
    (suite/"COMPLETE.json").write_text('{"schema":"reference-v1-raw-1","suite":"stability","cases":1,'
                                       '"physical_acceptance":"not evaluated"}\n')
    (suite/"stable-q50-initial"/"metadata.json").write_text('{"case":"stable-q50-initial","q":0.5')
    for name in ("configuration.json", "probes.csv", "diagnostics.csv"):
        (suite/"stable-q50-initial"/name).write_text("")
    analyzer = Path(__file__).resolve().parent/"analyze_reference_benchmarks.py"
    result = subprocess.run([sys.executable, str(analyzer), "--input", str(root), "--output", str(root/"analysis"),
                             "--suite", "stability"], capture_output=True, text=True, timeout=120)
    metrics = root/"analysis"/"metrics.json"
    require(result.returncode == 1 and metrics.is_file() and (root/"analysis"/"report.md").is_file(),
            "analyzer did not retain a failure report for malformed metadata: " + result.stderr[-400:])
    summary = json.loads(metrics.read_text())
    require(summary["status"] == "fail" and any(s["suite"] == "provenance" for s in summary["suites"])
            and any("unreadable" in f for s in summary["suites"] for f in s["failures"]), "malformed metadata not reported")
    checks += 2
    print("PASS resource budget and failure-retention checks: %d checks" % checks)
    return checks


def synthetic_diagnostics(q, driven, steps, drift=5e-9, swing=0.5, nonfinite_at=None, ratio=None):
    n_ref = 8 if driven else 0
    rows = []
    for n in range(steps+1):
        if driven and n < n_ref:
            u = 1e-12*n
            qn = u*(1+0.1*n)
        elif ratio is not None and n == n_ref+5:
            u, qn = ratio, 1.0
        else:
            u = 1+swing*math.sin(0.1*(n-n_ref))
            qn = 1+drift*math.sin(0.37*(n-n_ref))
        if driven and n == n_ref:
            u = 1.0
        if nonfinite_at == n:
            qn = float("nan")
        row = {"state": str(n), "e_time_s": "0", "h_time_s": "0", "U_J": repr(u), "Q_J": repr(qn)}
        row.update({"max_"+name: repr(0.5*(1+abs(math.sin(n)))) for name in NAMES})
        rows.append(row)
    return rows


def synthetic_stability():
    checks = 0
    for q, driven in ((0.5, False), (0.5, True), (0.99, False), (0.99, True)):
        steps = 20008 if driven else 20000
        meta = {"case": "stable-%s-%s" % ("q50" if q == 0.5 else "q99", "driven" if driven else "initial"),
                "q": q, "driven": driven, "propagation": False, "steps": steps, "dt_s": 1e-11,
                "cells": [12, 14, 16], "spacing_m": [0.01, 0.015, 0.02], "diagnostic_reference_state": 8 if driven else 0,
                "elapsed_seconds": 0.0}
        swing = 0.3
        metrics, blocks = analyze_stability(meta, synthetic_diagnostics(q, driven, steps, swing=swing))
        require(metrics["status"] == "pass", "synthetic stability %s: %s" % (meta["case"], metrics["failures"]))
        require(len(blocks) == 20 and blocks[0]["first_state"] == metrics["reference_state"]+1
                and blocks[-1]["last_state"] == steps and all(b["last_state"]-b["first_state"] == 999 for b in blocks),
                "block partition")
        require(abs(metrics["max_invariant_error"]-5e-9) <= 1e-10, "invariant maximum")
        checks += 3
        for kwargs, text in ((dict(drift=2e-8), "invariant drift"), (dict(nonfinite_at=17), "nonfinite diagnostic"),
                             (dict(ratio=1000.0), "energy bound")):
            metrics, _ = analyze_stability(meta, synthetic_diagnostics(q, driven, steps, swing=swing, **kwargs))
            require(metrics["status"] == "fail" and has_failure(metrics, text), "undetected: " + text)
            checks += 1
        metrics, _ = analyze_stability(meta, synthetic_diagnostics(q, driven, steps, swing=swing)[:-1])
        require(has_failure(metrics, "diagnostic states"), "short trace undetected")
        metrics, _ = analyze_stability({**meta, "steps": 30}, synthetic_diagnostics(q, driven, 30, swing=swing),
                                       fixed_suite=False)
        require(metrics["status"] == "pass" and metrics["source_free_blocks"] == 0, "short non-fixed trace")
        checks += 2
    print("PASS synthetic V03 reductions: %d checks" % checks)
    return checks


class Oracle:
    """Independent FND-03 transcription on nested lists; no permutation helper."""

    def __init__(self, cells, spacing):
        self.cells, self.spacing = cells, spacing

    def extents(self, id):
        return [self.cells[axis]+(0 if half else 1) for axis, half in enumerate(half_offsets(id))]

    def make(self, id):
        sx, sy, sz = self.extents(id)
        return [[[0.0]*sz for _ in range(sy)] for _ in range(sx)]

    def indices(self, id):
        sx, sy, sz = self.extents(id)
        for i in range(sx):
            for j in range(sy):
                for k in range(sz):
                    yield i, j, k

    def wall(self, id, index):
        if id >= 3:
            return index[id-3] in (0, self.cells[id-3])
        return any(index[axis] in (0, self.cells[axis]) for axis in range(3) if axis != id)

    def weight(self, id, index):
        weight = 1.0
        for axis in range(3):
            integer = axis != id if id < 3 else axis == id-3
            if integer and index[axis] in (0, self.cells[axis]):
                weight *= 0.5
        return weight

    def curl_h(self, h, id, i, j, k):
        """(curl H) at the E location (i,j,k) using backward differences."""
        dx, dy, dz = self.spacing
        hx, hy, hz = h
        if id == 0:
            return (hz[i][j][k]-hz[i][j-1][k])/dy-(hy[i][j][k]-hy[i][j][k-1])/dz
        if id == 1:
            return (hx[i][j][k]-hx[i][j][k-1])/dz-(hz[i][j][k]-hz[i-1][j][k])/dx
        return (hy[i][j][k]-hy[i-1][j][k])/dx-(hx[i][j][k]-hx[i][j-1][k])/dy

    def curl_e(self, e, id, i, j, k):
        """(curl E) at the H location (i,j,k) using forward differences."""
        dx, dy, dz = self.spacing
        ex, ey, ez = e
        if id == 3:
            return (ez[i][j+1][k]-ez[i][j][k])/dy-(ey[i][j][k+1]-ey[i][j][k])/dz
        if id == 4:
            return (ex[i][j][k+1]-ex[i][j][k])/dz-(ez[i+1][j][k]-ez[i][j][k])/dx
        return (ey[i+1][j][k]-ey[i][j][k])/dx-(ex[i][j+1][k]-ex[i][j][k])/dy

    def fixture(self):
        d_min = min(self.spacing)
        potential = []
        for id in (3, 4, 5):
            array = self.make(id)
            half = half_offsets(id)
            for i, j, k in self.indices(id):
                index = (i, j, k)
                distances = [min((index[axis]+half[axis]), self.cells[axis]-(index[axis]+half[axis])) for axis in range(3)]
                if min(distances) <= 2:
                    continue
                array[i][j][k] = d_min*(((17*i+31*j+43*k+13*(id-3)) % 101)-50)/50
            potential.append(array)
        shape = [self.make(id) for id in range(3)]
        maximum = 0.0
        for id in range(3):
            for i, j, k in self.indices(id):
                if self.wall(id, (i, j, k)):
                    continue
                shape[id][i][j][k] = self.curl_h(potential, id, i, j, k)
                maximum = max(maximum, abs(shape[id][i][j][k]))
        require(maximum > 0, "zero oracle shape")
        for id in range(3):
            for i, j, k in self.indices(id):
                shape[id][i][j][k] /= maximum
        return shape

    def step(self, e, h, dt, current=None):
        for id in (3, 4, 5):
            for i, j, k in self.indices(id):
                h[id-3][i][j][k] -= dt/MU0*self.curl_e(e, id, i, j, k)
        for id in (0, 1, 2):
            for i, j, k in self.indices(id):
                if self.wall(id, (i, j, k)):
                    continue
                increment = self.curl_h(h, id, i, j, k)
                if current is not None:
                    increment -= current[id][i][j][k]
                e[id][i][j][k] += dt/EPS0*increment

    def diagnostics(self, e, h, dt):
        electric, magnetic, cross, maxima = [], [], [], []
        for id in range(6):
            array = (e+h)[id]
            maximum = 0.0
            for i, j, k in self.indices(id):
                value = array[i][j][k]
                maximum = max(maximum, abs(value))
                weight = self.weight(id, (i, j, k))
                if id < 3:
                    electric.append(weight*value*value)
                else:
                    magnetic.append(weight*value*value)
                    cross.append(weight*value*self.curl_e(e, id, i, j, k))
            maxima.append(maximum)
        volume = self.spacing[0]*self.spacing[1]*self.spacing[2]
        u = volume/2*(EPS0*math.fsum(electric)+MU0*math.fsum(magnetic))
        return u, u-volume*dt/2*math.fsum(cross), maxima


def close(actual, expected, scale, tolerance=1e-12):
    if expected == 0:
        return actual == 0
    return abs(actual-expected) <= tolerance*max(abs(expected), scale)


def oracle_against_smoke(root):
    checks = 0
    for name in ("stable-q99-initial", "stable-q99-driven"):
        meta, probes, diagnostics = load_case(root/name)
        require(meta["cells"] == [12, 14, 16] and meta["spacing_m"] == [0.01, 0.015, 0.02], "smoke fixture grid")
        oracle = Oracle(meta["cells"], meta["spacing_m"])
        dt = meta["dt_s"]
        expected_dt = 0.99/(C0*math.sqrt(sum(1/d**2 for d in meta["spacing_m"])))
        require(abs(dt/expected_dt-1) <= 5e-15, "independent CFL")
        shape = oracle.fixture()
        e = [oracle.make(id) for id in range(3)]
        h = [oracle.make(id) for id in (3, 4, 5)]
        if not meta["driven"]:
            for id in range(3):
                for i, j, k in oracle.indices(id):
                    e[id][i][j][k] = shape[id][i][j][k]
        centre = [c//2 for c in meta["cells"]]
        for n in range(meta["steps"]+1):
            u, q, maxima = oracle.diagnostics(e, h, dt)
            row = diagnostics[n]
            scale = max(u, 1e-300)
            require(close(float(row["U_J"]), u, scale) and close(float(row["Q_J"]), q, scale), "%s U/Q state %d" % (name, n))
            for id, name_id in enumerate(NAMES):
                require(close(float(row["max_"+name_id]), maxima[id], maxima[id] or 1e-300), "%s maxima state %d" % (name, n))
            for row in probes:
                if int(row["state"]) != n:
                    continue
                id = NAMES.index(row["component"])
                require([int(row[x]) for x in "ijk"] == centre, "centre probe index")
                value = (e+h)[id][centre[0]][centre[1]][centre[2]]
                require(close(float(row["value"]), value, maxima[id] or 1e-300), "%s probe %s state %d" % (name, row["component"], n))
            checks += 8
            if n == meta["steps"]:
                break
            current = None
            if meta["driven"] and n < 8:
                factor = 0.01*EPS0/dt*math.sin(PI*(n+0.5)/8)
                current = [[[[factor*v for v in column] for column in plane] for plane in shape[id]] for id in range(3)]
            oracle.step(e, h, dt, current)
        print("PASS oracle %s: %d states of U/Q/maxima/centre probes within 1e-12" % (name, meta["steps"]+1))
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    checks = synthetic_propagation()+synthetic_stability()+resource_and_retention_checks()
    if args.app is None:
        print("PASS %d synthetic reduction checks; LIMIT: no solver output examined (pass --app)" % checks)
        return
    require(args.output_root is not None, "--output-root is required with --app")
    args.output_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix="ref05-", dir=str(args.output_root.resolve())))
    command = [str(args.app.resolve()), "--benchmark", "reference-v1", "--suite", "smoke", "--output", str(evidence/"smoke")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    require(result.returncode == 0 and result.stderr == "", "Smoke CLI failed: " + result.stdout+result.stderr)
    checks += oracle_against_smoke(evidence/"smoke")
    meta, probes, _ = load_case(evidence/"smoke"/"prop-xy-p24-primary")
    metrics, _ = analyze_propagation(meta, probes, fixed_suite=False)
    require(metrics["status"] == "pass", "two-step smoke propagation measurement: %s" % metrics["failures"])
    print("PASS two-step smoke measurement: continuum error %.9g (cap %.4g), discrete %.3g, impedance %.3g"
          % (metrics["continuum_error"], metrics["continuum_cap"], metrics["discrete_error"], metrics["max_impedance_error"]))
    print("PASS %d reduction/oracle checks; evidence: %s" % (checks+1, evidence))
    print("LIMIT: smoke-length runs only; V01-V03 acceptance requires the full fixed suites")


if __name__ == "__main__":
    main()
