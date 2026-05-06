#!/usr/bin/env python3
"""
UCloud orchestrator for 63 benchmark jobs (3 portfolios x 7 years x 3 reps).

Constraints:
- Per-portfolio in-flight cap: 7
- Gurobi license pool: 7 licenses x 2 slots = 14 (only ek1/k1 consume; cpsat free)

Crash-safe + resume-aware:
- state persisted to state.json after every change
- On startup, queries UCloud for actual state of "running" jobs
- Scans existing results.csv per task to detect partial completions
- For partial tasks: identifies the culprit (problem after last completed),
  marks it as OOM in results.csv, and submits a resume job that skips it
- Per-task retry cap to avoid infinite loops on broken tasks

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

# UCloud drive path where wrappers live (matches the mount /work/benchmark)
WRAPPER_DRIVE_DIR_PROD = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers"
WRAPPER_DRIVE_DIR_TEST = "/1096288/Jobs/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/wrappers-test"
WRAPPER_DRIVE_DIR = WRAPPER_DRIVE_DIR_PROD

# Where the orchestrator (running inside a UCloud container) sees the filesystem.
LOCAL_BENCHMARK_ROOT = Path("/work/benchmark")
DRIVE_BENCHMARK_ROOT = "/1096288/Jobs/benchmark"

PROBLEMS_LOCAL_DIR = LOCAL_BENCHMARK_ROOT / "data" / "mzn-challenge"
RESULTS_LOCAL_DIR_PROD = LOCAL_BENCHMARK_ROOT / "results" / "final-many-reps"
RESULTS_LOCAL_DIR_TEST = LOCAL_BENCHMARK_ROOT / "results" / "test-orchestrator"
RESULTS_LOCAL_DIR = RESULTS_LOCAL_DIR_PROD  # overridden by --test

# Runtime wrappers (one file per resume submission, written on the fly)
RUNTIME_WRAPPERS_LOCAL = LOCAL_BENCHMARK_ROOT / "ucloud-benchmark" / "run-final-portfolios-more-reps" / "wrappers-runtime"
RUNTIME_WRAPPERS_DRIVE = f"{DRIVE_BENCHMARK_ROOT}/ucloud-benchmark/run-final-portfolios-more-reps/wrappers-runtime"

PORTFOLIOS = ["cpsat8", "k1-8c-8s-v1", "ek1-8c-8s-v2"]
YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
REPS = [1, 2, 3]

LICENSES = ["alessio", "astrid", "malthe", "mikkel", "felix", "jonas", "default"]
SLOTS_PER_LICENSE = 2  # 7 * 2 = 14 ek1+k1 slots

PER_PORTFOLIO_CAP = 7
POLL_INTERVAL_SEC = 30
RETRY_LIMIT = 5

FINAL_STATES = {"SUCCESS", "FAILURE", "CANCELED", "EXPIRED"}


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


# ---------------- problem enumeration / resume detection ----------------
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


def parse_csv_keys(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def classify_task(task: dict) -> tuple[str, dict]:
    """Inspect this task's existing results.csv. Returns (state, info) where state is one of:
       'pending'           — no partial results
       'complete'          — results.csv has all expected rows
       'partial'           — results.csv exists but incomplete; info has resume + culprit
       'skip_then_complete'— last completed was the second-last problem; only the very last (culprit) remains
    """
    csv_path = task_results_dir(task) / "results.csv"
    rows = parse_csv_keys(csv_path)
    if not rows:
        return ('pending', {})

    actual = [(r["problem"], r["name"], r["model"]) for r in rows
              if r.get("optimal") != "OOM"]  # OOM markers don't count
    expected = get_problem_keys(task["year"])
    if not expected:
        return ('pending', {})

    if len(actual) >= len(expected):
        return ('complete', {})

    last = actual[-1] if actual else None
    if last is None:
        return ('pending', {})
    try:
        idx = expected.index(last)
    except ValueError:
        return ('partial', {'error': f'last problem {last} not found in expected list'})

    if idx + 1 >= len(expected):
        return ('complete', {})

    culprit = expected[idx + 1]
    if idx + 2 >= len(expected):
        return ('skip_then_complete', {'culprit': culprit})

    resume = expected[idx + 2]
    return ('partial', {
        'culprit': list(culprit),
        'resume_name': resume[1],  # 'name' column value, used by --start-from-instance
    })


def append_oom_marker(task: dict, culprit: list) -> None:
    """Idempotently append an OOM row to results.csv for the culprit problem."""
    csv_path = task_results_dir(task) / "results.csv"
    if not csv_path.exists():
        return
    rows = parse_csv_keys(csv_path)
    for r in rows:
        if (r.get("optimal") == "OOM" and r.get("name") == culprit[1]
                and r.get("problem") == culprit[0] and r.get("model") == culprit[2]):
            return  # already marked
    schedule = task["portfolio"]  # cpsat8 / ek1-8c-8s-v2 / k1-8c-8s-v1
    new_row = [schedule, culprit[0], culprit[1], culprit[2], "0", "", "OOM", ""]
    with open(csv_path, "a", newline="") as f:
        csv.writer(f).writerow(new_row)


# ---------------- runtime resume wrapper generation ----------------
def generate_resume_wrapper(task: dict, license_name: Optional[str], resume_name: str, retry: int) -> str:
    portfolio = task["portfolio"]
    year = task["year"]
    rep = task["rep"]

    if portfolio == "cpsat8":
        sched = f"../solvers/{portfolio}.csv"
    elif portfolio == "ek1-8c-8s-v2":
        sched = f"../schedules-eligible/{portfolio}.csv"
    else:  # k1-8c-8s-v1
        sched = f"../schedules/{portfolio}.csv"

    if portfolio == "cpsat8" or license_name == "default":
        src_line = "source /work/minizinc/scripts/setup-env.sh"
    else:
        src_line = (f"source /work/minizinc/scripts/setup-env.sh "
                    f"--gurobi-license /work/minizinc/solvers/gurobi/gurobi-{license_name}.lic")

    is_test = (RESULTS_LOCAL_DIR == RESULTS_LOCAL_DIR_TEST)
    timeout = 2 if is_test else 1200
    out_root = "test-orchestrator" if is_test else "final-many-reps"

    fname = f"resume-{portfolio}-{year}-r{rep}-{license_name or 'cpsat'}-try{retry}.sh"
    RUNTIME_WRAPPERS_LOCAL.mkdir(parents=True, exist_ok=True)
    local_path = RUNTIME_WRAPPERS_LOCAL / fname
    content = f"""#!/bin/bash
set -eo pipefail
{src_line}
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="{portfolio}"
CORES=8
year={year}
rep={rep}

{{
    echo "=== RESUME {portfolio} {year} r{rep} (license={license_name or 'default'}, resume_from={resume_name}, try={retry}) ==="
    python ../benchmark_parasol.py -s "{sched}" \\
        -r 1 -t {timeout} \\
        -o "../../results/{out_root}/${{PORTFOLIO}}/${{PORTFOLIO}}-${{year}}-r${{rep}}" \\
        --problems-path "../../data/mzn-challenge/${{year}}" \\
        --discover \\
        --start-from-instance "{resume_name}" \\
        -- --solver parasol -p ${{CORES}} --ai none --output-solver \\
        --solver-config-mode cache --verbosity error \\
        --static-runtime 100000000
}} 2>&1 | tee -a ${{PORTFOLIO}}-${{year}}-r${{rep}}-out.txt
"""
    local_path.write_text(content)
    local_path.chmod(0o755)
    return f"{RUNTIME_WRAPPERS_DRIVE}/{fname}"


# ---------------- state ----------------
@dataclass
class JobState:
    portfolio: str
    year: int
    rep: int
    job_id: Optional[str] = None
    license: Optional[str] = None
    state: str = "pending"  # pending | partial | running | success | failure | canceled | expired | failed
    submitted_at: Optional[float] = None
    finished_at: Optional[float] = None
    retry_count: int = 0
    resume_info: Optional[dict] = None  # {'culprit': [...], 'resume_name': str}
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


def submit_fresh(task: dict, license_name: Optional[str], token: str) -> str:
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


def submit_resume(task: dict, license_name: Optional[str], resume_name: str,
                  retry: int, token: str) -> str:
    drive_path = generate_resume_wrapper(task, license_name, resume_name, retry)
    spec = json.loads(TEMPLATE_SPEC.read_text())
    spec["name"] = f"{task_key(task)}-resume{retry}"
    spec["parameters"]["batchScript"]["path"] = drive_path
    spec["parameters"]["batchScript"]["value"] = None
    spec["allowDuplicateJob"] = True
    resp = api_request("POST", "/api/jobs", token, {"items": [spec], "type": "bulk"})
    if "responses" in resp and resp["responses"]:
        return resp["responses"][0]["id"]
    raise RuntimeError(f"unexpected resume submit response: {resp}")


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


# ---------------- classification + reconcile ----------------
def initial_scan(state: dict, queue: list[dict]) -> None:
    """For each task, classify based on existing results.csv and update its state."""
    for task in queue:
        k = task_key(task)
        j = state["jobs"][k]
        if j["state"] in ("running", "success", "failed"):
            # leave running for reconcile; success/failed are terminal
            continue
        cls, info = classify_task(task)
        if cls == "complete":
            if j["state"] != "success":
                print(f"  scan {k}: complete, marking success")
            j["state"] = "success"
        elif cls == "skip_then_complete":
            print(f"  scan {k}: only culprit {info['culprit'][1]} left, marking OOM and success")
            append_oom_marker(task, info["culprit"])
            j["state"] = "success"
        elif cls == "partial":
            print(f"  scan {k}: partial — culprit={info.get('culprit', ['?','?'])[1] if info.get('culprit') else '?'}, "
                  f"resume_from={info.get('resume_name','?')}")
            j["state"] = "partial"
            j["resume_info"] = info
            j["retry_count"] = j.get("retry_count", 0)
        else:
            j["state"] = "pending"


def reconcile(state: dict, token: str) -> None:
    for k, j in state["jobs"].items():
        if j["state"] == "running" and j.get("job_id"):
            try:
                s = get_job_state(j["job_id"], token)
                if s in FINAL_STATES:
                    print(f"  reconcile {k}: was running, now {s}")
                    j["state"] = s.lower()
                    j["finished_at"] = j.get("finished_at") or time.time()
            except Exception as e:
                print(f"  reconcile error {k}: {e}")
    save_state(state)


def post_finish_classify(task: dict, j: dict) -> None:
    """After a job ends, re-check results.csv to decide success/partial/failed."""
    cls, info = classify_task(task)
    if cls == "complete":
        j["state"] = "success"
    elif cls == "skip_then_complete":
        append_oom_marker(task, info["culprit"])
        j["state"] = "success"
    elif cls == "partial":
        if j.get("retry_count", 0) >= RETRY_LIMIT:
            j["state"] = "failed"
            j["last_error"] = "retry limit reached, still partial"
        else:
            j["state"] = "partial"
            j["resume_info"] = info
    else:  # pending — empty CSV after a run? treat as failed
        if j.get("retry_count", 0) >= RETRY_LIMIT:
            j["state"] = "failed"
        else:
            j["state"] = "partial"
            j["resume_info"] = {}


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

        # 3. dispatch pending + partial
        for task in queue:
            k = task_key(task)
            j = state["jobs"][k]
            if j["state"] not in ("pending", "partial"):
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
                if j["state"] == "partial":
                    info = j.get("resume_info") or {}
                    retry = j.get("retry_count", 0) + 1
                    if not info.get("resume_name"):
                        # No resume info available — fall back to fresh submit
                        job_id = submit_fresh(task, license, token)
                    else:
                        if info.get("culprit"):
                            append_oom_marker(task, info["culprit"])
                        job_id = submit_resume(task, license, info["resume_name"], retry, token)
                        j["retry_count"] = retry
                else:
                    job_id = submit_fresh(task, license, token)
            except Exception as e:
                print(f"  submit error {k}: {e}")
                continue
            j["job_id"] = job_id
            j["license"] = license
            j["state"] = "running"
            j["submitted_at"] = time.time()
            running_per[p] += 1
            print(f"  submitted {k} (license={license}, retry={j.get('retry_count', 0)}) -> {job_id}")
            save_state(state)

        # 4. progress + termination
        total = len(queue)
        done = sum(1 for j in state["jobs"].values() if j["state"] in ("success", "failed"))
        running = sum(1 for j in state["jobs"].values() if j["state"] == "running")
        partial = sum(1 for j in state["jobs"].values() if j["state"] == "partial")
        pending = sum(1 for j in state["jobs"].values() if j["state"] == "pending")
        print(f"[{time.strftime('%H:%M:%S')}] success+failed={done} running={running} partial={partial} pending={pending}")
        if done == total:
            print("All jobs done.")
            break
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
