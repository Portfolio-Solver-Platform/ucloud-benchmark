from tqdm import tqdm
import os
import subprocess
import argparse

SOLVERS = {
    "dexter": [1, 2, 4, 8],
    "org.minizinc.mip.xpress": [1, 2, 4, 8],
    "nl.tudelft.algorithmics.pumpkin": [1],
    "yuck": [1, 2, 4, 8],
    "org.minizinc.mip.scip": [1],
    "org.minizinc.mip.highs": [1],
    "org.minizinc.mip.coin-bc": [1, 2, 4, 8],
}

KILL_SOLVERS = ["minizinc", "java", "pumpkin-solver", "fzn-dexter"]

def get_base_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def kill_solvers():
    for solver in KILL_SOLVERS:
        subprocess.run(["pkill", "-9", solver], capture_output=True)


def run_minizinc(model, instance, core, solver, output_dir):
    cmd = [
        "minizinc",
        model,
    ]
    if instance is not None:
        cmd.append(instance)
    cmd.extend([
        "-i",
        "--output-time",
        "--output-objective",
        "-p", str(core),
        "--free-search",
        "--json-stream",
        "--time-limit", "1200000",
        "--output-mode", "json",
        "--solver", solver,
    ])

    model_name = get_base_name(model)
    instance_name = get_base_name(instance) if instance else ""
    output_file = os.path.join(output_dir, f"{model_name}_{instance_name}-sep-{solver}-sep-{core}.out")

    with open(output_file, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL)


def do_all_runs(model, instance, solver, cores, output_dir):
    for core in cores:
        kill_solvers()
        run_minizinc(model, instance, core, solver, output_dir)


def start(solver, cores, problems_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for sub_folder in sorted(os.listdir(problems_path)):
        if not os.path.isdir(os.path.join(problems_path, sub_folder)):
            continue
        files: list[str] = os.listdir(os.path.join(problems_path, sub_folder))
        models: list[str] = [file for file in files if file.endswith('.mzn')]
        instances: list[str] = [file for file in files if file.endswith('.dzn') or file.endswith('.json')]
        sub_folder_path = os.path.join(problems_path, sub_folder)

        if len(instances) == 0:
            for model in models:
                model_path = os.path.join(sub_folder_path, model)
                do_all_runs(model_path, None, solver, cores, output_dir)
        else:
            for model in models:
                for instance in instances:
                    model_path = os.path.join(sub_folder_path, model)
                    instance_path = os.path.join(sub_folder_path, instance)
                    do_all_runs(model_path, instance_path, solver, cores, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MiniZinc benchmarks")
    parser.add_argument("--problems", required=True, help="Path to problems directory")
    parser.add_argument("--output", required=True, help="Output directory for result files")
    args = parser.parse_args()

    for solver, cores in tqdm(SOLVERS.items(), desc="Solvers"):
        start(solver, cores, args.problems, args.output)