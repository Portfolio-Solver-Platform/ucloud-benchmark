#!/usr/bin/env python3
"""
Per-problem runner: invokes benchmark_parasol.py once per problem so that an
OOM/timeout/crash on one problem doesn't kill the rest of the run.

Model: presence in CSV = problem has been attempted, leave it alone.
Absence = needs running. For each absent problem, run it in a fresh subprocess;
write the resulting row (a success row from benchmark_parasol on a clean run,
or an error row constructed here for OOM/TIMEOUT/crash). One row per (problem,
name, model) triple - the row is canonical for that problem and is never
overwritten by a subsequent invocation.

This is meant to be run-to-completion. If the wrapper itself is killed
mid-loop, some expected problems will have no row yet; the orchestrator
detects this and resubmits, and on resume this script picks up the missing
problems.

CSV layout (matches benchmark_parasol.py):
  schedule, problem, name, model, time_ms, objective, optimal, last_result_from
"""
from __future__ import annotations
import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from discover import discover_problems

CSV_HEADERS = ["schedule", "problem", "name", "model", "time_ms",
               "objective", "optimal", "last_result_from"]
# Simple model: presence in CSV = problem has been attempted, leave it alone.
# Absence = needs running. The wrapper writes ONE row per attempt (success row
# from benchmark_parasol.py for clean runs; an error row constructed here for
# OOM/TIMEOUT/crash). Once a row exists, it is canonical for that problem.


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--portfolio", required=True)
    p.add_argument("--year", required=True, type=int)
    p.add_argument("--rep", required=True, type=int)
    p.add_argument("--schedule", required=True, type=Path,
                   help="Path to schedule CSV (e.g. ../solvers/cpsat8.csv)")
    p.add_argument("--problems-path", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--timeout", required=True, type=int,
                   help="benchmark_parasol.py -t value (seconds per problem)")
    p.add_argument("--cores", default=8, type=int)
    p.add_argument("--benchmark-script", default=HERE / "benchmark_parasol.py",
                   type=Path, help="Path to benchmark_parasol.py")
    p.add_argument("parasol_args", nargs=argparse.REMAINDER,
                   help="After --, args to pass through to parasol")
    return p.parse_args()


def load_existing_rows(csv_path: Path) -> dict[tuple[str, str, str], dict]:
    """Read existing CSV; return {(problem,name,model): row}. Dedupes by keeping last."""
    if not csv_path.exists():
        return {}
    out: dict[tuple[str, str, str], dict] = {}
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r.get("problem", ""), r.get("name", ""), r.get("model", ""))
            out[key] = r
    return out


def write_csv(csv_path: Path, rows: dict[tuple, dict]) -> None:
    """Atomically write CSV from rows dict."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        for key, row in rows.items():
            # Only write fields the writer knows about
            w.writerow({k: row.get(k, "") for k in CSV_HEADERS})
    tmp.replace(csv_path)


def run_one_problem(
    *,
    benchmark_script: Path,
    schedule: Path,
    problems_path: Path,
    timeout: int,
    cores: int,
    parasol_args: list[str],
    model_path: Path,
    data_path: Path | None,
    schedule_stem: str,
    problem_dir: str,
    name: str,
    model_stem: str,
) -> dict:
    """Invoke benchmark_parasol.py for one problem; return a result row dict."""
    rel_model = model_path.relative_to(problems_path)
    instance_spec = f"{rel_model}:{data_path.relative_to(problems_path)}" if data_path else str(rel_model)

    tmpdir = Path(tempfile.mkdtemp(prefix="per-problem-"))
    cmd = [
        sys.executable, str(benchmark_script),
        "-s", str(schedule),
        "-r", "1",
        "-t", str(timeout),
        "-o", str(tmpdir),
        "--problems-path", str(problems_path),
        "--instances", instance_spec,
        "--", *parasol_args,
    ]

    # Hard wall: a bit more than benchmark_parasol's own -t, since it adds setup overhead.
    hard_wall = timeout + 60
    start = time.time()
    rc: int | str = 0
    try:
        result = subprocess.run(cmd, timeout=hard_wall, capture_output=True, text=True)
        rc = result.returncode
    except subprocess.TimeoutExpired:
        rc = "PY_TIMEOUT"
    elapsed_ms = int((time.time() - start) * 1000)

    if rc == 0:
        # Try to read the row from the subprocess's CSV
        sub_csv = tmpdir / "results.csv"
        if sub_csv.exists():
            with open(sub_csv, newline="") as f:
                rows = list(csv.DictReader(f))
            shutil.rmtree(tmpdir, ignore_errors=True)
            if rows:
                # Take the last row (in case of multi-row output for some reason)
                return rows[-1]

    # Couldn't get a clean result: classify the failure.
    shutil.rmtree(tmpdir, ignore_errors=True)
    if rc == "PY_TIMEOUT":
        status = "TIMEOUT"
    elif isinstance(rc, int) and rc < 0:
        # Killed by signal. -9 = SIGKILL (likely OOM); others mark generic ERROR
        status = "OOM" if rc == -9 else "ERROR"
    else:
        status = "ERROR"

    return {
        "schedule": schedule_stem,
        "problem": problem_dir,
        "name": name,
        "model": model_stem,
        "time_ms": str(elapsed_ms),
        "objective": "",
        "optimal": status,
        "last_result_from": "",
    }


def main() -> None:
    args = parse_args()
    parasol_args = args.parasol_args
    if parasol_args and parasol_args[0] == "--":
        parasol_args = parasol_args[1:]

    schedule_stem = args.schedule.stem
    problems = discover_problems(args.problems_path, None)

    out_csv = args.output_dir / "results.csv"
    rows = load_existing_rows(out_csv)

    print(f"per_problem_runner: {args.portfolio} {args.year} r{args.rep} - "
          f"{len(problems)} expected problems, {len(rows)} existing rows")
    sys.stdout.flush()

    n_skip = n_attempt = n_success = n_fail = 0

    for model_path, data_path in problems:
        problem_dir = model_path.parent.name
        name = (data_path.stem if data_path else model_path.stem)
        model_stem = model_path.stem
        key = (problem_dir, name, model_stem)

        if key in rows:
            # Row already exists for this problem (any status). Skip.
            n_skip += 1
            continue

        print(f"  attempting {problem_dir}/{name}", flush=True)

        # Pre-write a placeholder row before launching the subprocess. If the
        # subprocess (or the entire container) gets killed, this row remains so
        # the next wrapper invocation skips past this problem instead of getting
        # killed on it again. If the run completes normally, this placeholder is
        # overwritten with the actual result below.
        placeholder = {
            "schedule": schedule_stem,
            "problem": problem_dir,
            "name": name,
            "model": model_stem,
            "time_ms": "0",
            "objective": "",
            "optimal": "WRAPPER_KILLED",
            "last_result_from": "",
        }
        rows[key] = placeholder
        write_csv(out_csv, rows)

        new_row = run_one_problem(
            benchmark_script=args.benchmark_script,
            schedule=args.schedule,
            problems_path=args.problems_path,
            timeout=args.timeout,
            cores=args.cores,
            parasol_args=parasol_args,
            model_path=model_path,
            data_path=data_path,
            schedule_stem=schedule_stem,
            problem_dir=problem_dir,
            name=name,
            model_stem=model_stem,
        )
        rows[key] = new_row
        write_csv(out_csv, rows)

        n_attempt += 1
        status = new_row.get("optimal", "")
        if status in {"Optimal", "Unsat", "Unknown"}:
            n_success += 1
        else:
            n_fail += 1
        print(f"    -> status={new_row.get('optimal')} time_ms={new_row.get('time_ms')}",
              flush=True)

    print(f"\nDone: skipped={n_skip} attempted={n_attempt} "
          f"({n_success} success, {n_fail} non-success). Total rows in CSV: {len(rows)}.")


if __name__ == "__main__":
    main()
