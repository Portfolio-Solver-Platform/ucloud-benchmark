#!/usr/bin/env python3
"""Parse `psp projects results -w <id>` JSON output into a CSV matching
benchmark_solvers.py columns (solver, cores, problem, name, model, time_ms,
objective, status).

Usage:
    psp projects results -w <project-id> > raw.json
    python parse_results.py raw.json [-o results.csv]
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

# (problem_id, instance_id) -> (problem_name, instance_name, model_name)
LOOKUP = {
    (21, 156): ("EchoSched",            "14-10-0-2_3",    "JSP0"),
    (23, 165): ("fbd1",                 "FBDk07",         "FBD1"),
    ( 3,  19): ("atsp",                 "instance4_0p15", "atsp"),
    (36, 296): ("hitori",               "h14-1",          "hitori"),
    (39, 323): ("ihtc-2024-kletzander", "test03",         "model4_opt"),
}

OBJ_RE = re.compile(r"(?:objective|obj)\s*=\s*(-?\d+)")


def extract_objective(solution_text: str) -> str:
    m = OBJ_RE.search(solution_text or "")
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="JSON file from `psp projects results -w`")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output CSV (default: <input>.csv)")
    args = ap.parse_args()

    results = json.loads(args.input.read_text())
    out_path = args.output or args.input.with_suffix(".csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["solver", "cores", "problem", "name", "model", "time_ms", "objective", "status"])
        for r in results:
            inner = json.loads(r["result"])["result"]
            key = (r["problem_id"], r["instance_id"])
            if key not in LOOKUP:
                print(f"Unknown (problem_id, instance_id) = {key}, skipping", file=sys.stderr)
                continue
            problem, name, model = LOOKUP[key]
            w.writerow([
                "cp-sat",
                r["vcpus"],
                problem,
                name,
                model,
                f"{inner['solve_time'] * 1000:.0f}",
                extract_objective(inner.get("solution", "")),
                inner["kind"].capitalize(),
            ])
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
