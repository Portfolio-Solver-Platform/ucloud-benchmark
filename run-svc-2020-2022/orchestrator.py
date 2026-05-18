#!/usr/bin/env python3
"""
UCloud orchestrator for 63 benchmark jobs (3 portfolios x 7 years x 3 reps).

Constraints:
- Per-portfolio in-flight cap: 7
- Gurobi license pool: 7 licenses x 2 slots = 14 (only ek1/k1 consume; cpsat free)

Model: per_problem_runner.py (called inside the wrapper) writes ONE row per
expected problem - either a real benchmark result row or an error row if the
problem's subprocess crashed/OOMed/timed out. Once a row exists, that problem
is considered done; rows are never overwritten.

So the orchestrator only needs to think in terms of presence:
  - 'pending'  - no CSV yet
  - 'partial'  - CSV exists but missing rows for some expected problems
                 (means the wrapper itself died mid-loop)
  - 'complete' - every expected problem has a row (any status)

Failed machines (UCloud jobs ending in FAILURE/EXPIRED/CANCELED, or finishing
with a partial CSV) are appended to failures.jsonl with the problem that was
in flight when the job died.

Orchestrator job:
  - Cap in-flight per portfolio at 7
  - Manage gurobi license pool (14 slots) for ek1/k1
  - Drain partial tasks before fresh ones (two-pass dispatch)
  - Resubmit partial tasks up to RETRY_LIMIT
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

WRAPPER_DRIVE_DIR = "/1096288/Jobs/benchmark/ucloud-benchmark/run-svc-2020-2022/wrappers"

LOCAL_BENCHMARK_ROOT = Path("/work/benchmark")
PROBLEMS_LOCAL_DIR = LOCAL_BENCHMARK_ROOT / "data" / "mzn-challenge"
RESULTS_LOCAL_DIR = LOCAL_BENCHMARK_ROOT / "results" / "svc-2020-2022"

PORTFOLIOS = ["svc-k1", "svc-ek1"]
YEARS = [2022, 2021, 2020]
REPS = [1, 2, 3]

LICENSES = ["alessio", "astrid", "malthe", "mikkel", "felix", "jonas", "default"]
SLOTS_PER_LICENSE = 2

PER_PORTFOLIO_CAP = 7
POLL_INTERVAL_SEC = 30
RETRY_LIMIT = 15  # max wrapper resubmits per task. With the placeholder fix in
                  # per_problem_runner, each container-killing problem only burns
                  # ONE retry (next wrapper sees the placeholder and skips past).
                  # 15 is enough to absorb that many killing problems per task.

FINAL_STATES = {"SUCCESS", "FAILURE", "CANCELED", "EXPIRED"}
NONFINAL_UCLOUD_FAILURES = {"FAILURE", "CANCELED", "EXPIRED"}
FAILURE_LOG = HERE / "failures.jsonl"  # one JSON object per machine that didn't finish


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
       'partial'  - CSV exists but at least one expected (problem, name, model)
                    has no row in it
       'complete' - every expected (problem, name, model) has a row in CSV
                    (regardless of status; the row itself is the canonical record)
    """
    csv_path = task_results_dir(task) / "results.csv"
    rows = parse_csv_rows(csv_path)
    if not rows:
        return ('pending', {})

    expected = get_problem_keys(task["year"])
    if not expected:
        return ('pending', {})

    present = {(r["problem"], r["name"], r["model"]) for r in rows}
    missing = [k for k in expected if k not in present]

    if not missing:
        return ('complete', {'rows': len(rows)})
    return ('partial', {
        'missing_count': len(missing),
        'rows': len(rows),
        'in_flight': missing[0],  # the first missing key — what was running when the wrapper died
    })


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
    retry_count: int = 0  # number of resubmits after the initial dispatch
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
    """Always re-evaluate based on disk truth, except for jobs UCloud says are running.
    Disk is authoritative: stale state.json entries get corrected to match.
    """
    for task in queue:
        k = task_key(task)
        j = state["jobs"][k]
        if j["state"] == "running":
            continue  # leave for reconcile
        cls, info = classify_task(task)
        prev_state = j["state"]
        if cls == "complete":
            j["state"] = "success"
            if prev_state != "success":
                print(f"  scan {k}: complete ({info.get('rows')} rows)")
        elif cls == "partial":
            n_expected = len(get_problem_keys(task['year']))
            j["state"] = "partial"
            tag = "" if prev_state not in ("success", "failed") else f" (was '{prev_state}')"
            print(f"  scan {k}: partial ({info['missing_count']}/{n_expected} missing){tag}")
        else:
            j["state"] = "pending"
            if prev_state in ("success", "failed"):
                print(f"  scan {k}: was '{prev_state}' but no CSV — re-queuing")


def log_failure(task: dict, j: dict, ucloud_state: str, in_flight: Optional[tuple]) -> None:
    """Append a one-line JSON record of a machine that didn't complete its task."""
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": task_key(task),
        "job_id": j.get("job_id"),
        "license": j.get("license"),
        "ucloud_state": ucloud_state,
        "in_flight_problem": list(in_flight) if in_flight else None,
        "retry_count": j.get("retry_count", 0),
    }
    with open(FAILURE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def write_killed_placeholder(task: dict, in_flight: tuple) -> None:
    """The wrapper container died before writing a row for the in-flight problem.
    Write a WRAPPER_KILLED placeholder for it directly from the orchestrator so
    the next wrapper invocation skips past it.
    """
    csv_path = task_results_dir(task) / "results.csv"
    if not csv_path.exists():
        return  # nothing to append to
    # Read all rows; replace any existing row for this key (defensive); append placeholder.
    rows = parse_csv_rows(csv_path)
    by_key: dict[tuple, dict] = {(r["problem"], r["name"], r["model"]): r for r in rows}
    if in_flight in by_key:
        return  # already present, nothing to do
    placeholder = {
        "schedule": task["portfolio"],
        "problem": in_flight[0],
        "name": in_flight[1],
        "model": in_flight[2],
        "time_ms": "0",
        "objective": "",
        "optimal": "WRAPPER_KILLED",
        "last_result_from": "",
    }
    by_key[in_flight] = placeholder
    # Atomic rewrite
    tmp = csv_path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["schedule", "problem", "name", "model",
                                          "time_ms", "objective", "optimal",
                                          "last_result_from"])
        w.writeheader()
        for k_, r in by_key.items():
            w.writerow({k: r.get(k, "") for k in ["schedule", "problem", "name", "model",
                                                  "time_ms", "objective", "optimal",
                                                  "last_result_from"]})
    tmp.replace(csv_path)
    print(f"    wrote WRAPPER_KILLED placeholder for {in_flight[0]}/{in_flight[1]}")


def post_finish_classify(task: dict, j: dict, ucloud_state: str) -> None:
    """After a job ends, re-check CSV. Presence = done.
    If still partial, the wrapper died mid-loop; resubmit up to RETRY_LIMIT.
    If the container appeared to "succeed" but the CSV is still missing rows,
    the wrapper container itself was killed (typically by OOM on a hungry
    problem). In that case, write a WRAPPER_KILLED placeholder for the in-flight
    problem so the next wrapper invocation skips past it.
    """
    cls, info = classify_task(task)
    if cls == "complete":
        j["state"] = "success"
        return

    # Job didn't finish. Log the failure.
    in_flight = info.get("in_flight") if cls == "partial" else None
    if ucloud_state in NONFINAL_UCLOUD_FAILURES or cls != "complete":
        log_failure(task, j, ucloud_state, in_flight)

    # If UCloud says SUCCESS but CSV is partial → the wrapper container itself
    # was killed mid-problem. Write a placeholder so we don't loop on the same
    # killer problem forever.
    if cls == "partial" and ucloud_state == "SUCCESS" and in_flight:
        try:
            write_killed_placeholder(task, in_flight)
            # Re-classify after placeholder write (might now be complete or
            # advance the in_flight pointer).
            cls, info = classify_task(task)
            if cls == "complete":
                j["state"] = "success"
                return
        except Exception as e:
            print(f"    placeholder write failed: {e}")

    if j.get("retry_count", 0) >= RETRY_LIMIT:
        j["state"] = "failed"
        j["last_error"] = f"retry limit reached, ucloud={ucloud_state}, "\
                           f"missing={info.get('missing_count', '?')}"
    else:
        j["state"] = "partial" if cls == "partial" else "pending"


def reconcile(state: dict, token: str) -> None:
    for k, j in state["jobs"].items():
        if j["state"] == "running" and j.get("job_id"):
            try:
                s = get_job_state(j["job_id"], token)
                if s in FINAL_STATES:
                    print(f"  reconcile {k}: was running, now {s}")
                    task = {"portfolio": j["portfolio"], "year": j["year"], "rep": j["rep"]}
                    j["finished_at"] = j.get("finished_at") or time.time()
                    post_finish_classify(task, j, s)
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
                        post_finish_classify(task, j, s)
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
