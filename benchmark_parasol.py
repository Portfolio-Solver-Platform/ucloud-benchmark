#!/usr/bin/env python3
import argparse
import atexit
import csv
import glob
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from discover import discover_problems

PROBLEMS = [
    # --- Stress tests (specifically designed to stress solvers) ---
    ("search_stress/search_stress.mzn", "search_stress/08_08.dzn"),  # Search stress
    ("slow_convergence/slow_convergence.mzn", "slow_convergence/0300.dzn"),  # Slow bound convergence

    # --- Pure SAT puzzles (different constraint structures) ---
    ("hitori/hitori.mzn", "hitori/h11-1.dzn"),  # Grid-based SAT
    ("nonogram/non.mzn", "nonogram/non_fast_3.dzn"),  # Line-based constraints
    ("fillomino/fillomino.mzn", "fillomino/6x6_0.dzn"),  # Region-based SAT

    # --- Hard combinatorial problems ---
    ("costas-array/CostasArray.mzn", "costas-array/14.dzn"),  # All-different + math
    ("ghoulomb/ghoulomb.mzn", "ghoulomb/3-8-20.dzn"),  # Golomb ruler variant

    # --- Geometric/packing problems ---
    ("rectangle-packing/rect_packing.mzn", "rectangle-packing/rpp09_false.dzn"),  # 2D packing (UNSAT)
    ("rectangle-packing/rect_packing.mzn", "rectangle-packing/rpp12_true.dzn"),  # 2D packing (SAT)
    ("pentominoes/pentominoes-int.mzn", "pentominoes/03.dzn"),  # Polyomino placement

    # --- Routing/TSP variants ---
    ("atsp/atsp.mzn", "atsp/instance5_0p15.dzn"),  # Asymmetric TSP
    ("cvrp/cvrp.mzn", "cvrp/simple2.dzn"),  # Capacitated VRP (small)
    ("tsptw/tsptw.mzn", "tsptw/n20w160.001.dzn"),  # TSP with time windows

    # --- Job shop scheduling variants ---
    ("fjsp/fjsp.mzn", "fjsp/easy01.dzn"),  # Flexible job shop (easy)
    ("fjsp/fjsp.mzn", "fjsp/med04.dzn"),  # Flexible job shop (medium)
    ("openshop/openshop.mzn", "openshop/gp10-4.dzn"),  # Open shop scheduling

    # --- Global constraint heavy ---
    ("multi-knapsack/mknapsack.mzn", "multi-knapsack/mknap1-5.dzn"),  # Multi-dim knapsack
    ("black-hole/black-hole.mzn", "black-hole/4.dzn"),  # Card game (global constraints)

    # --- Classic puzzles ---
    ("mqueens/mqueens2.mzn", "mqueens/n13.dzn"),  # N-queens variant

]


SOLVERS = ["fzn-cp-sat", "fzn-gecode", "fzn-chuffed", "fzn-huub", "cplex", "choco", "fzn-choco.sh", "picat", "fzn-picat", "java", "minizinc", "parasol", "fzn-dexter", "fzn-izplus", "pumpkin-solver", "yuck"]


def kill_solvers():
    for solver in SOLVERS:
        subprocess.run(["pkill", "-9", solver], capture_output=True)


def signal_handler(sig, frame):
    print("\nInterrupted, killing solvers...")
    kill_solvers()
    sys.exit(1)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(kill_solvers)


def resolve_schedules(args: list[str]) -> list[Path]:
    files = []
    for arg in args:
        path = Path(arg)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.glob("*.csv")))
        else:
            files.extend(Path(m) for m in sorted(glob.glob(arg)))
    return list(dict.fromkeys(f.resolve() for f in files))


def run_parasol(model: Path, data: Path | None, schedule: Path | None,
                timeout: int | None, parasol_args: list[str]) -> tuple[float, str | None, str, str, str]:
    cmd = []
    if timeout:
        cmd.extend(["timeout", str(timeout)])
    cmd.append("minizinc")

    cmd.append(str(model))
    if data:
        cmd.append(str(data))
    if schedule:
        cmd.extend(["--static-schedule", str(schedule)])

    cmd.extend(parasol_args)

    print(f"    cmd: {' '.join(cmd)}", flush=True)
    start = time.perf_counter()
    result = subprocess.run(cmd, stdout=subprocess.PIPE)
    elapsed_ms = (time.perf_counter() - start) * 1000

    stdout = result.stdout.decode("utf-8", errors="replace")


    objectives = re.findall(r'_objective\s*=\s*(-?\d+);', stdout)
    objective = objectives[-1] if objectives else None

    if "==========" in stdout:
        status = "Optimal"
    elif "=====UNSATISFIABLE=====" in stdout:
        status = "Unsat"
    elif "----------" in stdout and not objective:
        status = "Optimal"  # SAT problem with solution found
    else:
        status = "Unknown"

    # Parse % NOTE lines to find which solver produced the final solution
    note_matches = re.findall(r'% NOTE: (.+?) found (?:objective|solution)', stdout)
    last_result_from = note_matches[-1] if note_matches else ""

    return elapsed_ms, objective, status, stdout, last_result_from


def run_benchmark(problems: list[tuple[Path, Path | None]], schedules: list[Path | None],
                  timeout: int | None, runs: int, output_dir: Path, cores: int,
                  parasol_args: list[str], ai_label: str = "none"):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "results.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["schedule", "problem", "name", "model", "time_ms", "objective", "optimal", "last_result_from"])

        for schedule in schedules:
            schedule_label = schedule.name if schedule else ai_label
            print(f"\nSchedule: {schedule_label}")

            for model, data in problems:
                problem = model.parent.name
                name = data.stem if data else model.stem
                model_name = model.stem

                print(f"  {name}: ", end="", flush=True)

                for run in range(runs):
                    kill_solvers()
                    time_ms, objective, status, stdout, last_result_from = run_parasol(model, data, schedule, timeout, parasol_args)
                    schedule_stem = schedule.stem if schedule else ai_label

                    # Save full output to .out file
                    out_filename = "-sep-".join([problem, model_name, name, schedule_stem, str(cores), str(run)]) + ".out"
                    (output_dir / out_filename).write_text(stdout)

                    writer.writerow([schedule_stem, problem, name, model_name, f"{time_ms:.0f}", objective or "", status, last_result_from])
                    f.flush()
                    short = "US" if status == "Unsat" else status[0]
                    print(f"{time_ms/1000:.1f}s({short}) ", end="", flush=True)

                print()

    print(f"\nResults written to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Parasol static schedules. Use -- to separate benchmark args from parasol args.",
        epilog="Example: %(prog)s -s schedules/ -r 1 -o results/run1 --discover -- --solver parasol -p 8 --ai none --output-solver"
    )
    parser.add_argument("-s", "--schedules", nargs="*", help="Schedule CSV files or directories")
    parser.add_argument("-t", "--timeout", type=int, default=None, help="Timeout in seconds (applied via the timeout command)")
    parser.add_argument("-r", "--runs", type=int, default=3)
    parser.add_argument("-o", "--output", type=Path, default=Path("results/benchmark_run"))
    parser.add_argument("--problems-path", type=Path, default=Path("/problems"))
    parser.add_argument("--discover", action="store_true", help="Discover problems from --problems-path instead of using hardcoded list")
    parser.add_argument("--start-from-instance", type=str, default=None)

    args, parasol_args = parser.parse_known_args()

    # Strip leading '--' separator if present
    if parasol_args and parasol_args[0] == "--":
        parasol_args = parasol_args[1:]

    # Extract -p/--cores from parasol_args for the .out filename
    cores = 8
    for i, a in enumerate(parasol_args):
        if a in ("-p", "--cores") and i + 1 < len(parasol_args):
            try:
                cores = int(parasol_args[i + 1])
            except ValueError:
                pass

    schedules = resolve_schedules(args.schedules) if args.schedules else [None]
    if args.schedules and not schedules:
        print("No schedule files found", file=sys.stderr)
        sys.exit(1)

    if args.discover:
        problems = discover_problems(args.problems_path, args.start_from_instance)
    else:
        problems = [(args.problems_path / m, args.problems_path / d if d else None) for m, d in PROBLEMS]

    # Derive a label for AI-driven schedules from --ai-config command=./script.py
    ai_label = "none"
    for i, a in enumerate(parasol_args):
        if a == '--ai-config' and i + 1 < len(parasol_args):
            config = parasol_args[i + 1]
            if config.startswith('command='):
                ai_label = Path(config.split('=', 1)[1]).stem

    print(f"Schedules: {len(schedules)}, Problems: {len(problems)}, Runs: {args.runs}")
    print(f"Parasol args: {parasol_args}")
    run_benchmark(problems, schedules, args.timeout, args.runs, args.output, cores, parasol_args, ai_label)


if __name__ == "__main__":
    main()
