#!/usr/bin/env python3
"""
UCloud orchestrator for 63 benchmark jobs (3 portfolios x 7 years x 3 reps).

Constraints:
- Per-portfolio in-flight cap: 7
- Gurobi license pool: 7 licenses x 2 slots = 14 (only ek1/k1 consume; cpsat free)

Each task's wrapper invokes per_problem_runner.py, which:
  - Reads existing results.csv
  - Iterates expected problems for the year
  - Skips ones with status Optimal/Unsat
  - Runs each non-success problem in a fresh subprocess (so OOM/crash on one
    problem doesn't kill the rest)
  - Appends a row (success or error) for each attempted problem

Orchestrator job:
  - Track state of each (portfolio, year, rep) task
  - Dispatch fresh tasks; resubmit if wrapper itself died mid-run
  - Cap dispatched in-flight per portfolio at 7
  - Manage gurobi license pool (14 slots) for ek1/k1
  - Drain partial tasks before fresh ones (two-pass dispatch)
  - Crash-safe: state.json written atomically after every change

Auth: requires UCLOUD_TOKEN env var (a personal access token).
"""
from __future__ import annotations
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

# ---------------- config ----------------
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from discover import discover_problems  # noqa: E402

STATE_FILE = HERE / "state.json"
TEMPLATE_SPEC = HERE / "template-spec.json"

UCLOUD_BASE = "https://cloud.sdu.dk"

WRAPPER_DRIVE_DIR_PROD = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers"
WRAPPER_DRIVE_DIR_TEST = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers-test"
WRAPPER_DRIVE_DIR = WRAPPER_DRIVE_DIR_PROD

LOCAL_BENCHMARK_ROOT = Path("/work/benchmark")
PROBLEMS_LOCAL_DIR = LOCAL_BENCHMARK_ROOT / "data" / "mzn-challenge"
RESULTS_LOCAL_DIR_PROD = LOCAL_BENCHMARK_ROOT / "results" / "final-many-reps"
RESULTS_LOCAL_DIR_TEST = LOCAL_BENCHMARK_ROOT / "results" / "test-orchestrator"
RESULTS_LOCAL_DIR = RESULTS_LOCAL_DIR_PROD

PORTFOLIOS = ["cpsat8", "k1-8c-8s-v1", "ek1-8c-8s-v2"]
YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
REPS = [1, 2, 3]

LICENSES = ["alessio", "astrid", "malthe", "mikkel", "felix", "jonas", "default"]
SLOTS_PER_LICENSE = 2

PER_PORTFOLIO_CAP = 7
POLL_INTERVAL_SEC = 30
RETRY_LIMIT = 3  # how many times we resubmit a wrapper if it itself died mid-run

FINAL_STATES = {"SUCCESS", "FAILURE", "CANCELED", "EXPIRED"}
SUCCESS_STATUSES = {"Optimal", "Unsat"}


def need_token() -> str:
    t = os.environ.get("UCLOUD_TOKEN", "").strip()
    if not t:
        sys.exit("Set UCLOUD_TOKEN env var to your UCloud personal access token.")
    return t


# ---------------- queue ----------------
def build_queue() -> list[dict]:
    out = []
    for year in YEARS:
        for rep in REPS:
            for portfolio in PORTFOLIOS:
                out.append({"portfolio": portfolio, "year": year, "rep": rep})
    return out


def task_key(t: dict) -> str:
    return f"{t['portfolio']}-{t['year']}-r{t['rep']}"


def task_results_dir(task: dict) -> Path:
    return RESULTS_LOCAL_DIR / task["portfolio"] / f"{task['portfolio']}-{task['year']}-r{task['rep']}"


def wrapper_drive_path_for(portfolio: str, year: int, rep: int, license_name: Optional[str]) -> str:
    if portfolio == "cpsat8":
        return f"{WRAPPER_DRIVE_DIR}/run-{portfolio}-{year}-r{rep}.sh"
    return f"{WRAPPER_DRIVE_DIR}/run-{portfolio}-{year}-r{rep}-{license_name}.sh"


# ---------------- problem enumeration / classify ----------------
_PROBLEM_CACHE: dict[int, list[tuple[str, str, str]]] = {}


def get_problem_keys(year: int) -> list[tuple[str, str, str]]:
    """Ordered (problem, name, model) tuples for a year, matching results.csv columns."""
    if year not in _PROBLEM_CACHE:
        problems = discover_problems(PROBLEMS_LOCAL_DIR / str(year), None)
        _PROBLEM_CACHE[year] = [
            (m.parent.name, (d.stem if d else m.stem), m.stem)
            for m, d in problems
        ]
    return _PROBLEM_CACHE[year]


def parse_csv_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def classify_task(task: dict) -> tuple[str, dict]:
    """Returns (state, info).
       'pending'  - CSV doesn't exist
       'partial'  - CSV exists but some expected problem has no row
       'complete' - every expected problem has a row (any status)
    """
    csv_path = task_results_dir(task) / "results.csv"
    rows = parse_csv_rows(csv_path)
    if not rows:
        return ('pending', {})

    present = {(r["problem"], r["name"], r["model"]) for r in rows}
    expected = get_problem_keys(task["year"])
    if not expected:
        return ('pending', {})

    missing = [k for k in expected if k not in present]
    if not missing:
        return ('complete', {'rows': len(rows)})
    return ('partial', {'missing_count': len(missing), 'rows': len(rows)})


# ---------------- state ----------------
@dataclass
class JobState:
    portfolio: str
    year: int
    rep: int
    job_id: Optional[str] = None
    license: Optional[str] = None
    state: str = "pending"  # pending | partial | running | success | failed
    submitted_at: Optional[float] = None
    finished_at: Optional[float] = None
    retry_count: int = 0
    last_missing_count: Optional[int] = None
    last_error: Optional[str] = None


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"jobs": {}}


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


# ---------------- ucloud api ----------------
def api_request(method: str, path: str, token: str, body: Optional[dict] = None) -> dict:
    url = UCLOUD_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {text}") from e
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_text": text}


def submit_job(task: dict, license_name: Optional[str], token: str) -> str:
    spec = json.loads(TEMPLATE_SPEC.read_text())
    spec["name"] = task_key(task)
    spec["parameters"]["batchScript"]["path"] = wrapper_drive_path_for(
        task["portfolio"], task["year"], task["rep"], license_name)
    spec["parameters"]["batchScript"]["value"] = None
    spec["allowDuplicateJob"] = True
    resp = api_request("POST", "/api/jobs", token, {"items": [spec], "type": "bulk"})
    if "responses" in resp and resp["responses"]:
        return resp["responses"][0]["id"]
    raise RuntimeError(f"unexpected submit response: {resp}")


def get_job_state(job_id: str, token: str) -> str:
    resp = api_request("GET", f"/api/jobs/retrieve?id={job_id}", token)
    return resp.get("status", {}).get("state") or "UNKNOWN"


# ---------------- license pool ----------------
def needs_license(portfolio: str) -> bool:
    return portfolio != "cpsat8"


def in_use_licenses(state: dict) -> list[str]:
    return [j["license"] for j in state["jobs"].values()
            if j["state"] == "running" and j.get("license")]


def pick_license(state: dict) -> Optional[str]:
    in_use = in_use_licenses(state)
    for lic in LICENSES:
        if in_use.count(lic) < SLOTS_PER_LICENSE:
            return lic
    return None


# ---------------- classification helpers ----------------
def initial_scan(state: dict, queue: list[dict]) -> None:
    for task in queue:
        k = task_key(task)
        j = state["jobs"][k]
        if j["state"] in ("running", "success", "failed"):
            continue
        cls, info = classify_task(task)
        if cls == "complete":
            if j["state"] != "success":
                print(f"  scan {k}: complete ({info.get('rows')} rows)")
            j["state"] = "success"
        elif cls == "partial":
            print(f"  scan {k}: partial ({info['missing_count']} missing of {len(get_problem_keys(task['year']))})")
            j["state"] = "partial"
            j["last_missing_count"] = info["missing_count"]
        else:
            j["state"] = "pending"


def post_finish_classify(task: dict, j: dict) -> None:
    """After a job ends, re-check the CSV.
    Per_problem_runner is meant to fill every row, so 'complete' is the happy path.
    If the wrapper itself died mid-loop, we'd see 'partial'; resubmit up to RETRY_LIMIT.
    'partial with no progress' (same missing_count as before) means the wrapper
    is failing fast for some reason — failed.
    """
    cls, info = classify_task(task)
    if cls == "complete":
        j["state"] = "success"
        return

    if cls == "pending":
        # CSV gone or never created. Treat as fresh partial; cap retries.
        if j.get("retry_count", 0) >= RETRY_LIMIT:
            j["state"] = "failed"
            j["last_error"] = "wrapper produced no CSV"
        else:
            j["state"] = "partial"
        return

    # cls == "partial"
    new_missing = info["missing_count"]
    prev_missing = j.get("last_missing_count")
    progressed = (prev_missing is None) or (new_missing < prev_missing)
    j["last_missing_count"] = new_missing

    if progressed:
        j["state"] = "partial"
        # don't bump retry_count on progress
    else:
        if j.get("retry_count", 0) >= RETRY_LIMIT:
            j["state"] = "failed"
            j["last_error"] = f"no progress: {new_missing} missing rows after {j.get('retry_count')} retries"
        else:
            j["state"] = "partial"


def reconcile(state: dict, token: str) -> None:
    for k, j in state["jobs"].items():
        if j["state"] == "running" and j.get("job_id"):
            try:
                s = get_job_state(j["job_id"], token)
                if s in FINAL_STATES:
                    print(f"  reconcile {k}: was running, now {s}")
                    task = {"portfolio": j["portfolio"], "year": j["year"], "rep": j["rep"]}
                    j["finished_at"] = j.get("finished_at") or time.time()
                    post_finish_classify(task, j)
            except Exception as e:
                print(f"  reconcile error {k}: {e}")
    save_state(state)


# ---------------- main loop ----------------
def main() -> None:
    global WRAPPER_DRIVE_DIR, STATE_FILE, RESULTS_LOCAL_DIR
    if "--test" in sys.argv:
        WRAPPER_DRIVE_DIR = WRAPPER_DRIVE_DIR_TEST
        STATE_FILE = HERE / "state-test.json"
        RESULTS_LOCAL_DIR = RESULTS_LOCAL_DIR_TEST
        print(f"TEST MODE: wrappers={WRAPPER_DRIVE_DIR}")
        print(f"           state={STATE_FILE.name}")
        print(f"           results={RESULTS_LOCAL_DIR}")

    token = need_token()
    if not TEMPLATE_SPEC.exists():
        sys.exit(f"Missing {TEMPLATE_SPEC}")

    queue = build_queue()
    state = load_state()
    for task in queue:
        k = task_key(task)
        if k not in state["jobs"]:
            state["jobs"][k] = asdict(JobState(**task))

    n_running = sum(1 for j in state["jobs"].values() if j["state"] == "running")
    if n_running:
        print(f"Reconciling {n_running} jobs marked running...")
        reconcile(state, token)

    print("Scanning existing results...")
    initial_scan(state, queue)
    save_state(state)

    while True:
        # 1. poll running jobs; on completion, reclassify based on results
        for k, j in state["jobs"].items():
            if j["state"] == "running" and j.get("job_id"):
                try:
                    s = get_job_state(j["job_id"], token)
                    if s in FINAL_STATES:
                        j["finished_at"] = time.time()
                        task = {"portfolio": j["portfolio"], "year": j["year"], "rep": j["rep"]}
                        post_finish_classify(task, j)
                        print(f"  finished {k}: ucloud={s} -> {j['state']} (license={j.get('license')})")
                except Exception as e:
                    print(f"  poll error {k}: {e}")
        save_state(state)

        # 2. count in-flight per portfolio
        running_per = {p: 0 for p in PORTFOLIOS}
        for j in state["jobs"].values():
            if j["state"] == "running":
                running_per[j["portfolio"]] = running_per.get(j["portfolio"], 0) + 1

        # 3. dispatch — partials first, then pendings
        for desired_state in ("partial", "pending"):
            if desired_state == "pending" and any(j["state"] == "partial" for j in state["jobs"].values()):
                continue  # drain partials before starting fresh ones
            for task in queue:
                k = task_key(task)
                j = state["jobs"][k]
                if j["state"] != desired_state:
                    continue
                p = task["portfolio"]
                if running_per[p] >= PER_PORTFOLIO_CAP:
                    continue
                license = None
                if needs_license(p):
                    license = pick_license(state)
                    if not license:
                        continue
                try:
                    job_id = submit_job(task, license, token)
                except Exception as e:
                    print(f"  submit error {k}: {e}")
                    continue
                # Increment retry only for resubmits (partial state means we've been here before)
                if desired_state == "partial":
                    j["retry_count"] = j.get("retry_count", 0) + 1
                j["job_id"] = job_id
                j["license"] = license
                j["state"] = "running"
                j["submitted_at"] = time.time()
                running_per[p] += 1
                print(f"  submitted {k} (license={license}, retry={j.get('retry_count', 0)}) -> {job_id}")
                save_state(state)

        # 4. progress + termination
        total = len(queue)
        success = sum(1 for j in state["jobs"].values() if j["state"] == "success")
        failed = sum(1 for j in state["jobs"].values() if j["state"] == "failed")
        running = sum(1 for j in state["jobs"].values() if j["state"] == "running")
        partial = sum(1 for j in state["jobs"].values() if j["state"] == "partial")
        pending = sum(1 for j in state["jobs"].values() if j["state"] == "pending")
        print(f"[{time.strftime('%H:%M:%S')}] success={success} failed={failed} running={running} partial={partial} pending={pending}")
        if success + failed == total:
            print("All jobs done.")
            break
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
