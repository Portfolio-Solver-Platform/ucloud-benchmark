#!/usr/bin/env python3
"""
UCloud orchestrator for 63 benchmark jobs (3 portfolios x 7 years x 3 reps).

Constraints:
- Per-portfolio in-flight cap: 7
- Gurobi license pool: 7 licenses x 2 slots = 14 (only ek1/k1 consume; cpsat free)

Crash-safe: state persisted to state.json after every change. On restart,
queries UCloud for actual state of running jobs and resumes.

Auth: requires UCLOUD_TOKEN env var (a personal access token).
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# ---------------- config ----------------
HERE = Path(__file__).parent
STATE_FILE = HERE / "state.json"
TEMPLATE_SPEC = HERE / "template-spec.json"

UCLOUD_BASE = "https://cloud.sdu.dk"

# UCloud drive path where wrappers live (matches the mount /work/benchmark)
WRAPPER_DRIVE_DIR_PROD = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers"
WRAPPER_DRIVE_DIR_TEST = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers-test"
WRAPPER_DRIVE_DIR = WRAPPER_DRIVE_DIR_PROD  # overridden by --test

PORTFOLIOS = ["cpsat8", "k1-8c-8s-v1", "ek1-8c-8s-v2"]  # dispatch order per (year, rep)
YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
REPS = [1, 2, 3]

LICENSES = ["alessio", "astrid", "malthe", "mikkel", "felix", "jonas", "default"]
SLOTS_PER_LICENSE = 2  # 7 * 2 = 14 ek1+k1 slots

PER_PORTFOLIO_CAP = 7
POLL_INTERVAL_SEC = 30

FINAL_STATES = {"SUCCESS", "FAILURE", "CANCELED", "EXPIRED"}


def need_token() -> str:
    t = os.environ.get("UCLOUD_TOKEN", "").strip()
    if not t:
        sys.exit("Set UCLOUD_TOKEN env var to your UCloud personal access token.")
    return t


# ---------------- queue ----------------
def build_queue() -> list[dict]:
    """For each (year, rep) interleave portfolios. Newest year first."""
    out = []
    for year in YEARS:
        for rep in REPS:
            for portfolio in PORTFOLIOS:
                out.append({"portfolio": portfolio, "year": year, "rep": rep})
    return out


def task_key(t: dict) -> str:
    return f"{t['portfolio']}-{t['year']}-r{t['rep']}"


def wrapper_path_for(portfolio: str, year: int, rep: int, license_name: Optional[str]) -> str:
    """Drive path of the wrapper script for this task."""
    if portfolio == "cpsat8":
        return f"{WRAPPER_DRIVE_DIR}/run-{portfolio}-{year}-r{rep}.sh"
    return f"{WRAPPER_DRIVE_DIR}/run-{portfolio}-{year}-r{rep}-{license_name}.sh"


# ---------------- state ----------------
@dataclass
class JobState:
    portfolio: str
    year: int
    rep: int
    job_id: Optional[str] = None
    license: Optional[str] = None
    state: str = "pending"  # pending | running | success | failure | canceled | expired
    submitted_at: Optional[float] = None
    finished_at: Optional[float] = None


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
        with urllib.request.urlopen(req, timeout=30) as r:
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
    """Build payload from template-spec.json, override name + batchScript path, POST."""
    spec = json.loads(TEMPLATE_SPEC.read_text())
    spec["name"] = task_key(task)
    bs = spec["parameters"]["batchScript"]
    bs["path"] = wrapper_path_for(task["portfolio"], task["year"], task["rep"], license_name)
    bs["value"] = None
    spec["allowDuplicateJob"] = True

    body = {"items": [spec], "type": "bulk"}
    resp = api_request("POST", "/api/jobs", token, body)
    # response shape: {"responses": [{"id": "<job_id>"}]}
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


# ---------------- main loop ----------------
def reconcile(state: dict, token: str) -> None:
    """On startup, sync local state with what UCloud actually says."""
    for k, j in state["jobs"].items():
        if j["state"] == "running" and j.get("job_id"):
            try:
                s = get_job_state(j["job_id"], token)
                if s in FINAL_STATES:
                    print(f"  reconciled {k}: was running, now {s}")
                    j["state"] = s.lower()
                    j["finished_at"] = j.get("finished_at") or time.time()
            except Exception as e:
                print(f"  reconcile error for {k}: {e}")
    save_state(state)


def main() -> None:
    global WRAPPER_DRIVE_DIR, STATE_FILE
    if "--test" in sys.argv:
        WRAPPER_DRIVE_DIR = WRAPPER_DRIVE_DIR_TEST
        STATE_FILE = HERE / "state-test.json"
        print(f"TEST MODE: wrappers={WRAPPER_DRIVE_DIR}, state={STATE_FILE.name}")

    token = need_token()
    if not TEMPLATE_SPEC.exists():
        sys.exit(f"Missing {TEMPLATE_SPEC}. It should have been written next to this script.")

    queue = build_queue()
    state = load_state()
    for task in queue:
        k = task_key(task)
        if k not in state["jobs"]:
            state["jobs"][k] = asdict(JobState(**task))
    save_state(state)

    n_running = sum(1 for j in state["jobs"].values() if j["state"] == "running")
    if n_running:
        print(f"Reconciling {n_running} jobs marked running...")
        reconcile(state, token)

    while True:
        # 1. update statuses of running jobs
        for k, j in state["jobs"].items():
            if j["state"] == "running" and j.get("job_id"):
                try:
                    s = get_job_state(j["job_id"], token)
                    if s in FINAL_STATES:
                        j["state"] = s.lower()
                        j["finished_at"] = time.time()
                        print(f"  finished {k}: {s} (license={j.get('license')})")
                except Exception as e:
                    print(f"  poll error {k}: {e}")
        save_state(state)

        # 2. count in-flight per portfolio
        running_per = {p: 0 for p in PORTFOLIOS}
        for j in state["jobs"].values():
            if j["state"] == "running":
                running_per[j["portfolio"]] = running_per.get(j["portfolio"], 0) + 1

        # 3. dispatch new jobs in queue order
        for task in queue:
            k = task_key(task)
            j = state["jobs"][k]
            if j["state"] != "pending":
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
            j["job_id"] = job_id
            j["license"] = license
            j["state"] = "running"
            j["submitted_at"] = time.time()
            running_per[p] += 1
            print(f"  submitted {k} (license={license}) -> {job_id}")
            save_state(state)

        # 4. progress + termination
        total = len(queue)
        done = sum(1 for j in state["jobs"].values()
                   if j["state"] in ("success", "failure", "canceled", "expired"))
        running = sum(1 for j in state["jobs"].values() if j["state"] == "running")
        pending = total - done - running
        print(f"[{time.strftime('%H:%M:%S')}] done={done} running={running} pending={pending}")
        if pending == 0 and running == 0:
            print("All jobs done.")
            break
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
