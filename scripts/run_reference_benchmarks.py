"""Run the fixed reference-v1 suites serially and record measured resources.

Python 3.9+, standard library; optional psutil records the process peak working
set (Windows high-water value). Writes ROOT/<suite>/ raw artifacts through the
CLI and ROOT/resources.json. Exits nonzero if any suite fails.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


MEMORY_BUDGET = 2**31


def run(app, arguments, timeout, environment):
    started = time.perf_counter()
    process = subprocess.Popen([str(app)]+arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    peak = None
    exceeded = False
    try:
        import psutil
        observed = psutil.Process(process.pid)
        while process.poll() is None:
            if time.perf_counter()-started > timeout:
                process.kill()
                break
            try:
                memory = observed.memory_info()
                peak = max(peak or 0, getattr(memory, "peak_wset", memory.rss))
                if peak > MEMORY_BUDGET:
                    # The declared 2 GiB working budget is an acceptance limit; abort and retain evidence.
                    exceeded = True
                    process.kill()
                    break
            except psutil.NoSuchProcess:
                break
            time.sleep(0.05)
    except ImportError:
        pass
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
    status = process.returncode
    if exceeded and status == 0:
        status = -1
    return {"command": [str(app)]+arguments, "status": status, "budget_exceeded": exceeded,
            "budget_bytes": MEMORY_BUDGET, "stdout": out.decode(errors="replace"),
            "stderr": err.decode(errors="replace"), "elapsed_seconds": time.perf_counter()-started,
            "peak_working_set_bytes": peak}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suites", nargs="+", default=["propagation", "stability"])
    parser.add_argument("--runtime-path", type=Path, help="directory prepended to PATH for the compiler runtime")
    parser.add_argument("--timeout-hours", type=float, default=12.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)
    if args.runtime_path is not None:
        environment["PATH"] = str(args.runtime_path.resolve())+os.pathsep+environment.get("PATH", "")
    try:
        import psutil
        psutil_version = psutil.__version__
    except ImportError:
        psutil_version = None
    record = {"schema": "reference-v1-resources-1", "app": str(args.app.resolve()),
              "app_sha256": hashlib.sha256(args.app.read_bytes()).hexdigest(),
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "environment": {"platform": platform.platform(), "machine": platform.machine(),
                              "processor": platform.processor(), "python": sys.version.split()[0],
                              "psutil": psutil_version,
                              "cpu_identifier": os.environ.get("PROCESSOR_IDENTIFIER", "unavailable")},
              "suites": {}}
    failed = False
    for suite in args.suites:
        print("Running suite", suite, flush=True)
        result = run(args.app.resolve(), ["--benchmark", "reference-v1", "--suite", suite,
                                          "--output", str(args.output/suite)], args.timeout_hours*3600, environment)
        record["suites"][suite] = result
        failed = failed or result["status"] != 0
        print("suite=%s status=%s elapsed=%.3f s peak_working_set_bytes=%s" % (
            suite, result["status"], result["elapsed_seconds"], result["peak_working_set_bytes"]), flush=True)
        if result["budget_exceeded"]:
            print("suite %s aborted: peak working set exceeded the %d byte budget" % (suite, MEMORY_BUDGET), flush=True)
        if result["stderr"]:
            print("stderr:", result["stderr"], flush=True)
        (args.output/"resources.json").write_text(json.dumps(record, indent=1)+"\n")
    record["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (args.output/"resources.json").write_text(json.dumps(record, indent=1)+"\n")
    print("Raw suites complete; physical acceptance is evaluated separately by analyze_reference_benchmarks.py")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
