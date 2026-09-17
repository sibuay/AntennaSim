"""Compare two reference-v1 analyzer summaries for reproduction evidence.

Python 3.9+, standard library. Reads two ``metrics.json`` files written by
``analyze_reference_benchmarks.py`` and checks that they describe the same
deterministic measurements: identical case enumeration, thresholds, source
snapshot, statuses, and every numeric or textual metric except the measured
timing/resource observations (``elapsed_seconds``, ``root``, ``input``,
``resources``, ``analysis_environment``), which legitimately differ between
runs. Floating-point values must agree within ``--tolerance`` (default 0, i.e.
bit-for-bit as printed). Exits nonzero on any mismatch or if either summary
does not report ``pass``.
"""
import argparse
import json
import math
import sys
from pathlib import Path

IGNORED_KEYS = {"elapsed_seconds", "root", "input", "resources", "analysis_environment",
                "resources_error"}


def compare(reference, candidate, path, tolerance, mismatches, counter):
    if isinstance(reference, dict) and isinstance(candidate, dict):
        keys = set(reference) | set(candidate)
        for key in sorted(keys):
            if key in IGNORED_KEYS:
                continue
            if key not in reference or key not in candidate:
                mismatches.append("%s.%s: present in only one summary" % (path, key))
                continue
            compare(reference[key], candidate[key], "%s.%s" % (path, key), tolerance, mismatches, counter)
        return
    if isinstance(reference, list) and isinstance(candidate, list):
        if len(reference) != len(candidate):
            mismatches.append("%s: length %d versus %d" % (path, len(reference), len(candidate)))
            return
        for index, (left, right) in enumerate(zip(reference, candidate)):
            compare(left, right, "%s[%d]" % (path, index), tolerance, mismatches, counter)
        return
    counter["leaves"] += 1
    if isinstance(reference, bool) or isinstance(candidate, bool) or reference is None or candidate is None:
        # Python treats True == 1, so a boolean-to-number schema change would
        # pass a plain equality test; require the same type as well.
        if type(reference) is not type(candidate) or reference != candidate:
            mismatches.append("%s: %r versus %r" % (path, reference, candidate))
        return
    if isinstance(reference, (int, float)) and isinstance(candidate, (int, float)):
        if isinstance(reference, float) or isinstance(candidate, float):
            counter["floats"] += 1
            if math.isnan(reference) or math.isnan(candidate) or math.isinf(reference) or math.isinf(candidate):
                if not (repr(reference) == repr(candidate)):
                    mismatches.append("%s: %r versus %r" % (path, reference, candidate))
                return
            difference = abs(float(reference) - float(candidate))
            counter["max_difference"] = max(counter["max_difference"], difference)
            scale = max(abs(float(reference)), abs(float(candidate)), 1.0)
            if difference > tolerance * scale:
                mismatches.append("%s: %r versus %r (difference %.3e)" % (path, reference, candidate, difference))
            return
        if reference != candidate:
            mismatches.append("%s: %r versus %r" % (path, reference, candidate))
        return
    if reference != candidate:
        mismatches.append("%s: %r versus %r" % (path, reference, candidate))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True, help="tracked or earlier metrics.json")
    parser.add_argument("--candidate", type=Path, required=True, help="metrics.json from the reproduction")
    parser.add_argument("--tolerance", type=float, default=0.0,
                        help="allowed relative difference for floating-point metrics (default exact)")
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance < 0.0:
        parser.error("--tolerance must be a finite, nonnegative number (got %r)" % args.tolerance)
    reference = json.loads(args.reference.read_text())
    candidate = json.loads(args.candidate.read_text())
    mismatches = []
    counter = {"leaves": 0, "floats": 0, "max_difference": 0.0}
    for name, summary in (("reference", reference), ("candidate", candidate)):
        if summary.get("status") != "pass":
            mismatches.append("%s summary status is %r, not pass" % (name, summary.get("status")))
    reference_suites = [s.get("suite") for s in reference.get("suites", [])]
    candidate_suites = [s.get("suite") for s in candidate.get("suites", [])]
    if reference_suites != candidate_suites:
        mismatches.append("suite lists differ: %r versus %r" % (reference_suites, candidate_suites))
    else:
        compare(reference, candidate, "summary", args.tolerance, mismatches, counter)
    cases = sum(len(s.get("cases", [])) for s in reference.get("suites", []))
    print("suites %s; %d cases; %d compared leaves (%d floating-point); max absolute difference %.3e"
          % (reference_suites, cases, counter["leaves"], counter["floats"], counter["max_difference"]))
    print("reference source snapshots %s" % reference.get("source_snapshots"))
    print("candidate source snapshots %s" % candidate.get("source_snapshots"))
    if mismatches:
        print("%d mismatch(es):" % len(mismatches))
        for entry in mismatches:
            print("  " + entry)
        return 1
    print("summaries agree within tolerance %g" % args.tolerance)
    return 0


if __name__ == "__main__":
    sys.exit(main())
