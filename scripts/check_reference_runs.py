"""REF-04 independent CLI/artifact and S07 synthetic audit; no physics gate.

Python 3.9+, standard library. Retains all outputs below --output-root.
Optional psutil records peak working set (Windows high-water value) during runs.
"""
import argparse
import cmath
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from reference_measurements import fit_harmonic, native_impedance

C0 = 299792458.0
MU0 = 1.25663706127e-6
ETA0 = C0*MU0
EPS0 = 1/(MU0*C0*C0)
NAMES = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rejects(function):
    try:
        function()
    except (ValueError, RuntimeError, FileNotFoundError, KeyError):
        return
    raise RuntimeError("Invalid input/artifact was accepted")


def synthetic():
    worst = 0
    for direction in (-1, 1):
        for sign in (-1, 1):
            # Independent prescribed frequency; no discrete dispersion formula.
            p, spacing, k, omega, dt = 24, .0125, 2*math.pi/.3, 6e9, 3e-11
            first = None
            for state in (0, 1, 2):
                et, ht = state*dt, (state-.5)*dt
                e = [(i*spacing, math.cos(k*i*spacing-direction*omega*et)) for i in range(p, 2*p)]
                h = [((i+.5)*spacing, direction*sign/ETA0*math.cos(k*(i+.5)*spacing-direction*omega*ht))
                     for i in range(p, 2*p)]
                ef, er, ec = fit_harmonic(e, k, p, .5)
                hf, hr, hc = fit_harmonic(h, k, p, .5/ETA0)
                if state == 0:
                    first = ef
                else:
                    measured = cmath.phase(ef/first)/(state*dt)
                    require(abs(measured/(direction*omega)-1) <= 1e-12, "Synthetic direction/frequency")
                z = native_impedance(ef, hf, et, ht, direction*omega, .5/ETA0)
                worst = max(worst, abs(z/(direction*sign*ETA0)-1))
                require(er <= 1e-12 and hr*ETA0 <= 1e-12 and ec < 2 and hc < 2, "Synthetic fit")
    require(worst <= 1e-12, "S07 signed native complex ratio")
    for amplitude in (0, .1/ETA0):
        rejects(lambda: fit_harmonic([(i*.0125, amplitude*math.cos(k*i*.0125)) for i in range(24)], k, 24, .5/ETA0))
        rejects(lambda: native_impedance(1+0j, complex(amplitude), 0, -dt/2, omega, .5/ETA0))
    rejects(lambda: fit_harmonic([(0, 1)]*24, k, 24, .5))
    rejects(lambda: fit_harmonic([(0, 1)], k, 24, .5))
    rejects(lambda: fit_harmonic([(float("nan"), 1)]*24, k, 24, .5))
    print("PASS S07 synthetic native fit, weak/singular rejection; worst complex ratio error=%.5g" % worst)
    return worst


def read_json(path):
    def invalid(value):
        raise ValueError("Nonfinite JSON: " + value)
    return json.loads(path.read_text(), parse_constant=invalid)


def audit(root):
    marker = read_json(root / "COMPLETE.json")
    require(marker["schema"] == "reference-v1-raw-1" and marker["physical_acceptance"] == "not evaluated", "Completion contract")
    directories = sorted(p for p in root.iterdir() if p.is_dir())
    require(len(directories) == marker["cases"], "Incomplete suite")
    if marker["suite"] == "smoke":
        require([p.name for p in directories] == ["prop-xy-p24-primary", "stable-q99-driven", "stable-q99-initial"], "Smoke identity")
    for directory in directories:
        meta = read_json(directory / "metadata.json")
        config = read_json(directory / "configuration.json")
        require(config["case_status"] == "incomplete" and config["fixture_checks_status"] == "pending", "Provisional configuration status")
        for key in ("case", "source_snapshot_sha256", "cells", "spacing_m", "dt_s", "q", "steps", "source", "initialization"):
            require(config[key] == meta[key], "Retained configuration mismatch")
        require(meta["case"] == directory.name and meta["schema"] == marker["schema"], "Metadata identity")
        require(meta["case_status"] == "raw_complete" and meta["fixture_checks_status"] == "passed", "Incomplete case metadata")
        require(len(meta["source_snapshot_sha256"]) == 64, "Source fingerprint")
        require(meta["c0"] == C0 and meta["mu0"] == MU0 and meta["epsilon0"] == EPS0 and meta["eta0"] == ETA0, "Pinned constants")
        cells, spacing, dt, steps = meta["cells"], meta["spacing_m"], meta["dt_s"], meta["steps"]
        expected_dt = meta["q"]/(C0*math.sqrt(sum(1/d**2 for d in spacing)))
        require(abs(dt/expected_dt-1) <= 5e-15, "Independent CFL metadata")
        extents = [[cells[a]+int(a != id) if id < 3 else cells[a]+int(a == id-3) for a in range(3)] for id in range(6)]
        require(meta["extents"] == extents, "Six extents")
        payload = 8*sum(math.prod(shape) for shape in extents)
        require(meta["field_bytes"] == payload and 2*payload <= meta["working_bytes_budgeted"] <= 2**31, "Transient memory budget")
        require(meta["fixture_max_divergence_error"] <= 1e-11 and meta["fixture_max_plateau_error"] <= 1e-11, "Fixture report")
        with (directory / "probes.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        expected_probes = 6*meta["p"] if meta["propagation"] else 6
        require(len(rows) == (steps+1)*expected_probes, "Native row count")
        seen = set()
        for row in rows:
            n, id = int(row["state"]), NAMES.index(row["component"])
            index = tuple(int(row[key]) for key in ("i", "j", "k"))
            expected_time = (n-(0 if id < 3 else .5))*dt
            actual_time = float(row["time_s"])
            value = float(row["value"])
            require(math.isfinite(value) and abs(actual_time-expected_time) <= 5e-15*max(dt, abs(expected_time)), "Native time/value")
            key = n, id, index
            require(0 <= n <= steps and key not in seen, "Unique state/sample")
            seen.add(key)
            positions = []
            for a, name in enumerate(("x_m", "y_m", "z_m")):
                half = .5 if (a == id if id < 3 else a != id-3) else 0
                expected_position = (index[a]+half)*spacing[a]
                position = float(row[name])
                require(0 <= index[a] < extents[id][a] and abs(position-expected_position) <= 5e-15*max(spacing[a], abs(expected_position)), "Native location")
                positions.append(position)
            if n == 0 and meta["propagation"]:
                a, b = meta["a"], meta["b"]
                k = 2*math.pi/.3
                omega = 2/dt*math.asin(C0*dt/spacing[a]*math.sin(k*spacing[a]/2))
                phase = k*(positions[a]-(.6 if meta["enlarged"] else 0))-omega*expected_time
                sign = 1 if (a+1)%3 == b else -1
                expected = math.cos(phase) if id == b else sign/ETA0*math.cos(phase) if id == 6-a-b else 0
                require(abs(value-expected)*(1 if id < 3 else ETA0) <= 1e-11, "Independent raw initial plateau")
            if n == 0 and meta["driven"]:
                require(value == 0, "Driven initial zero")
        with (directory / "diagnostics.csv").open(newline="") as handle:
            energy = list(csv.DictReader(handle))
        require(len(energy) == (0 if meta["propagation"] else steps+1), "Diagnostic rows")
        for n, row in enumerate(energy):
            require(int(row["state"]) == n and all(math.isfinite(float(v)) for v in row.values()), "Finite diagnostic state")
            require(float(row["e_time_s"]) == n*dt and float(row["h_time_s"]) == (n-.5)*dt, "Diagnostic native time")
            require(float(row["U_J"]) >= 0 and all(float(row["max_"+name]) >= 0 for name in NAMES), "Positive norm/maxima")
        if energy:
            require(float(energy[0]["Q_J"]) == float(energy[0]["U_J"]), "Initial zero-H energy identity")
    return directories


def run(app, arguments):
    started = time.perf_counter()
    process = subprocess.Popen([str(app)]+arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    peak = None
    try:
        import psutil
        observed = psutil.Process(process.pid)
        while process.poll() is None:
            if time.perf_counter()-started > 60:
                process.kill()
                process.communicate()
                raise RuntimeError("Smoke subprocess timed out; check compiler runtime DLL PATH")
            try:
                memory = observed.memory_info()
                peak = max(peak or 0, getattr(memory, "peak_wset", memory.rss))
                if peak > 2**31:
                    process.kill()
                    process.communicate()
                    raise RuntimeError("Measured process memory exceeds 2 GiB")
            except psutil.NoSuchProcess:
                break
            time.sleep(.01)
    except ImportError:
        pass
    try:
        out, err = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError("Smoke subprocess timed out; check compiler runtime DLL PATH")
    return {"status": process.returncode, "stdout": out.decode(), "stderr": err.decode(),
            "elapsed_seconds": time.perf_counter()-started, "peak_working_set_bytes": peak}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix="ref04-", dir=str(args.output_root.resolve())))
    results = {"synthetic_complex_error": synthetic(), "runs": []}
    common = ["--benchmark", "reference-v1", "--suite", "smoke", "--output"]
    for name in ("first", "repeat"):
        result = run(args.app.resolve(), common+[str(evidence/name)])
        results["runs"].append(result)
        require(result["status"] == 0 and result["stderr"] == "", "Smoke CLI failed: " + str(result))
        audit(evidence/name)
    for path in (evidence/"first").glob("*/*.csv"):
        require(path.read_bytes() == (evidence/"repeat"/path.parent.name/path.name).read_bytes(), "Nondeterministic raw CSV")
    first_before = {str(p.relative_to(evidence/"first")): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (evidence/"first").rglob("*") if p.is_file()}
    result = run(args.app.resolve(), common+[str(evidence/"first")])
    require(result["status"] != 0, "Overwrite accepted")
    require(first_before == {str(p.relative_to(evidence/"first")): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (evidence/"first").rglob("*") if p.is_file()}, "Overwrite changed evidence")
    for count in ("0", "-1", "1.5", "+2", "18446744073709551616", "4503599627370496", "9"):
        target = evidence/("invalid-"+count.replace("+", "plus"))
        result = run(args.app.resolve(), common+[str(target), "--steps", count])
        require(result["status"] != 0 and not target.exists(), "Invalid count/guard created output")
    for suffix in (["--suite", "smoke"], ["--unknown", "1"], ["--steps"], ["--output", ""]):
        target = evidence/"malformed"
        result = run(args.app.resolve(), common+[str(target)]+suffix)
        require(result["status"] != 0 and not target.exists(), "Malformed CLI created output")
    target = evidence/"fixed-override"
    result = run(args.app.resolve(), ["--benchmark", "reference-v1", "--suite", "stability", "--output", str(target), "--steps", "2"])
    require(result["status"] != 0 and not target.exists(), "Fixed suite override accepted")
    # Simulated incomplete evidence must be rejected by the independent reader.
    incomplete = evidence/"incomplete"
    incomplete.mkdir()
    rejects(lambda: audit(incomplete))
    (incomplete/"COMPLETE.json").write_text((evidence/"first"/"COMPLETE.json").read_text())
    rejects(lambda: audit(incomplete))
    (evidence/"audit.json").write_text(json.dumps(results, indent=2)+"\n")
    print("PASS independent raw metadata/CSV, deterministic rerun, invalid CLI, overwrite and incomplete-artifact audit")
    print("Evidence:", evidence)
    for item in results["runs"]:
        print("Smoke elapsed=%.4f s peak_working_set_bytes=%s" % (item["elapsed_seconds"], item["peak_working_set_bytes"]))
    print("LIMIT: no V01-V03 physical acceptance or full suite measurements")


if __name__ == "__main__":
    main()
