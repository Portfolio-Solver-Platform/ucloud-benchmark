#!/usr/bin/env python3
"""Benchmark 5 instances via the PSP platform (cp-sat @ 8 cores, 3 reps).

Writes results to a CSV matching benchmark_solvers.py columns so local vs
platform results can be compared directly.
"""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# Make the example-python-client importable. Override with PSP_CLIENT_SRC if the
# psp repo lives somewhere else on this machine.
_DEFAULT_CLIENT_SRC = Path(__file__).resolve().parents[3] / "psp" / "example-python-client" / "src"
CLIENT_SRC = Path(os.environ.get("PSP_CLIENT_SRC", _DEFAULT_CLIENT_SRC))
if not CLIENT_SRC.is_dir():
    sys.exit(f"example-python-client src not found at {CLIENT_SRC}. Set PSP_CLIENT_SRC.")
sys.path.insert(0, str(CLIENT_SRC))

from auth.device_auth import DeviceAuth  # noqa: E402
from config import Config  # noqa: E402
from solver_director import (  # noqa: E402
    create_project,
    get_project_solution,
    get_project_status,
)

SOLVER_ID = 3
CORES = 8
MEMORY_GIB = 20.0
TIMEOUT_S = 1200
REPETITIONS = 3
POLL_INTERVAL_S = 30

# (problem_id, instance_id, problem_name, instance_name, model_name)
INSTANCES = [
    (21, 156, "EchoSched",            "14-10-0-2_3",    "JSP0"),
    (23, 165, "fbd1",                 "FBDk07",         "FBD1"),
    ( 3,  19, "atsp",                 "instance4_0p15", "atsp"),
    (36, 296, "hitori",               "h14-1",          "hitori"),
    (39, 323, "ihtc-2024-kletzander", "test03",         "model4_opt"),
]

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "results" / "platform-local-vs-platform"
CSV_COLUMNS = ["solver", "cores", "problem", "name", "model", "time_ms", "objective", "status"]


def build_project_config():
    return {
        "name": "local-vs-platform: cp-sat 8c",
        "timeout": TIMEOUT_S,
        "vcpus": CORES,
        "memory_gib": MEMORY_GIB,
        "problem_groups": [{
            "problem_group": 1,
            "problems": [
                {"problem": p, "instances": [i]}
                for p, i, *_ in INSTANCES
            ],
            "extras": {
                "repetitions": REPETITIONS,
                "solvers": [{"id": SOLVER_ID, "vcpus": CORES, "memory_gib": MEMORY_GIB}],
            },
        }],
    }


def wait_for_finish(token, project_id):
    while True:
        try:
            status = get_project_status(token, project_id)
            if status["status"]["isFinished"]:
                return
            print(f"[{time.strftime('%H:%M:%S')}] not finished, sleeping {POLL_INTERVAL_S}s")
        except requests.HTTPError as e:
            if e.response.status_code != 503:
                raise
            print(f"[{time.strftime('%H:%M:%S')}] solver controller not ready (503), retrying")
        time.sleep(POLL_INTERVAL_S)


def extract_objective(solution_text: str) -> str:
    m = re.search(r"objective\s*=\s*(-?\d+)", solution_text or "")
    return m.group(1) if m else ""


def write_results_csv(results, path: Path):
    lookup = {(p, i): (prob, inst, model) for p, i, prob, inst, model in INSTANCES}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in results:
            payload = json.loads(r["result"])
            inner = payload["result"]
            problem_name, instance_name, model_name = lookup[(r["problem_id"], r["instance_id"])]
            w.writerow([
                "cp-sat",
                r["vcpus"],
                problem_name,
                instance_name,
                model_name,
                f"{inner['solve_time'] * 1000:.0f}",
                extract_objective(inner.get("solution", "")),
                inner["kind"].capitalize(),
            ])


def main():
    token = DeviceAuth(Config).token()

    print("Creating project...")
    project = create_project(token, build_project_config())
    project_id = project["id"]
    print(f"Project ID: {project_id}")

    print("Waiting for completion...")
    wait_for_finish(token, project_id)

    print("Fetching results...")
    results = get_project_solution(token, project_id)

    csv_path = OUTPUT_DIR / "results.csv"
    write_results_csv(results, csv_path)
    print(f"Wrote {csv_path} ({len(results)} rows)")


if __name__ == "__main__":
    main()
