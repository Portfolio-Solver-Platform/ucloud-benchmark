#!/usr/bin/env python3
import argparse
import atexit
import csv
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from discover import discover_problems

PROBLEMS = [
    # --- Stress tests (specifically designed to stress solvers) ---
    ("search_stress/search_stress.mzn", "search_stress/08_08.dzn"),
    ("slow_convergence/slow_convergence.mzn", "slow_convergence/0300.dzn"),

    # --- Pure SAT puzzles (different constraint structures) ---
    ("hitori/hitori.mzn", "hitori/h11-1.dzn"),
    ("nonogram/non.mzn", "nonogram/non_fast_3.dzn"),
    ("fillomino/fillomino.mzn", "fillomino/6x6_0.dzn"),

    # --- Hard combinatorial problems ---
    ("costas-array/CostasArray.mzn", "costas-array/14.dzn"),
    ("ghoulomb/ghoulomb.mzn", "ghoulomb/3-8-20.dzn"),

    # --- Geometric/packing problems ---
    ("rectangle-packing/rect_packing.mzn", "rectangle-packing/rpp09_false.dzn"),
    ("rectangle-packing/rect_packing.mzn", "rectangle-packing/rpp12_true.dzn"),
    ("pentominoes/pentominoes-int.mzn", "pentominoes/03.dzn"),

    # --- Routing/TSP variants ---
    ("atsp/atsp.mzn", "atsp/instance5_0p15.dzn"),
    ("cvrp/cvrp.mzn", "cvrp/simple2.dzn"),
    ("tsptw/tsptw.mzn", "tsptw/n20w160.001.dzn"),

    # --- Job shop scheduling variants ---
    ("fjsp/fjsp.mzn", "fjsp/easy01.dzn"),
    ("fjsp/fjsp.mzn", "fjsp/med04.dzn"),
    ("openshop/openshop.mzn", "openshop/gp10-4.dzn"),

    # --- Global constraint heavy ---
    ("multi-knapsack/mknapsack.mzn", "multi-knapsack/mknap1-5.dzn"),
    ("black-hole/black-hole.mzn", "black-hole/4.dzn"),

    # --- Classic puzzles ---
    ("mqueens/mqueens2.mzn", "mqueens/n13.dzn"),
]


KNOWN_SOLVERS = ["fzn-cp-sat", "fzn-gecode", "fzn-chuffed", "fzn-huub", "cplex", "choco", "fzn-choco.sh", "picat", "fzn-picat", "java", "minizinc", "parasol"]


def kill_solvers():
    for solver in KNOWN_SOLVERS:
        subprocess.run(["pkill", "-9", solver], capture_output=True)


def signal_handler(sig, frame):
    print("\nInterrupted, killing solvers...")
    kill_solvers()
    sys.exit(1)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(kill_solvers)


def run_solver(model: Path, data: Path | None, solver: str, cores: int,
               timeout: int | None) -> tuple[float, str | None, str, str]:
    cmd = []
    if timeout:
        cmd.extend(["timeout", str(timeout)])
    cmd.extend(["minizinc", "--solver", solver])
    cmd.append(str(model))
    if data:
        cmd.append(str(data))
    cmd.extend(["-p", str(cores), "-i", "--json-stream", "--output-mode", "json",
                "-f", "--output-objective", "--output-time"])

    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True)
    elapsed_ms = (time.perf_counter() - start) * 1000

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if stderr:
        print(f"\n    STDERR: {stderr.strip()}", file=sys.stderr)

    # Parse JSON stream for objective and status
    objective = None
    status = None
    has_solution = False

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        if msg.get("type") == "solution":
            has_solution = True
            obj = msg.get("output", {}).get("json", {}).get("_objective")
            if obj is not None:
                objective = str(obj)

        elif msg.get("type") == "status":
            s = msg.get("status", "")
            if s == "OPTIMAL_SOLUTION":
                status = "Optimal"
            elif s == "UNSATISFIABLE":
                status = "Unsat"
            elif s == "SATISFIED":
                status = "Satisfied"
            elif s == "UNKNOWN":
                status = "Unknown"
            else:
                status = s.capitalize()

    # No status line emitted (solver crashed, timeout killed it, or just didn't print one)
    if status is None:
        status = "Satisfied" if has_solution else "Unknown"

    # Empty output = crash, treat as timeout
    if not stdout.strip() and status == "Unknown":
        elapsed_ms = (timeout * 1000) if timeout else elapsed_ms

    return elapsed_ms, objective, status, stdout


def run_benchmark(problems: list[tuple[Path, Path | None]], solvers: list[str],
                  cores_list: list[int], timeout: int | None, runs: int,
                  output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "results.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["solver", "cores", "problem", "name", "model", "time_ms", "objective", "status"])

        for solver in solvers:
            for cores in cores_list:
                print(f"\nSolver: {solver}, Cores: {cores}")

                for model, data in problems:
                    problem = model.parent.name
                    name = data.stem if data else model.stem
                    model_name = model.stem

                    print(f"  {name}: ", end="", flush=True)

                    for run in range(runs):
                        kill_solvers()
                        time_ms, objective, status, stdout = run_solver(model, data, solver, cores, timeout)

                        # Save full output to .out file
                        out_filename = "-sep-".join([problem, model_name, name, solver, str(cores), str(run)]) + ".out"
                        (output_dir / out_filename).write_text(stdout)

                        writer.writerow([solver, cores, problem, name, model_name, f"{time_ms:.0f}", objective or "", status])
                        f.flush()
                        short = "US" if status == "Unsat" else status[0]
                        print(f"{time_ms/1000:.1f}s({short}) ", end="", flush=True)

                    print()

    print(f"\nResults written to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark individual MiniZinc solvers.",
        epilog="Example: %(prog)s -s cp-sat gecode chuffed -p 1 2 4 -r 1 -t 30 -o results/solvers --discover"
    )
    parser.add_argument("-s", "--solvers", nargs="+", required=True, help="List of solver IDs to benchmark")
    parser.add_argument("-p", "--cores", nargs="+", type=int, default=[1], help="List of core counts to run each solver with (default: 1)")
    parser.add_argument("-t", "--timeout", type=int, default=None, help="Timeout in seconds (applied via the timeout command)")
    parser.add_argument("-r", "--runs", type=int, default=3)
    parser.add_argument("-o", "--output", type=Path, default=Path("results/solver_run"))
    parser.add_argument("--problems-path", type=Path, default=Path("/problems"))
    parser.add_argument("--discover", action="store_true", help="Discover problems from --problems-path instead of using hardcoded list")
    parser.add_argument("--instances", nargs="+", default=None,
                        help="Specific instances as 'model[:data]' pairs, paths relative to --problems-path")
    parser.add_argument("--start-from-instance", type=str, default=None)
    args = parser.parse_args()

    if args.discover:
        problems = discover_problems(args.problems_path, args.start_from_instance)
    elif args.instances:
        problems = []
        for spec in args.instances:
            if ":" in spec:
                m, d = spec.split(":", 1)
                problems.append((args.problems_path / m, args.problems_path / d))
            else:
                problems.append((args.problems_path / spec, None))
    else:
        problems = [(args.problems_path / m, args.problems_path / d if d else None) for m, d in PROBLEMS]

    print(f"Solvers: {args.solvers}, Cores: {args.cores}, Problems: {len(problems)}, Runs: {args.runs}")
    run_benchmark(problems, args.solvers, args.cores, args.timeout, args.runs, args.output)


if __name__ == "__main__":
    main()
