#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi-felix.lic
cd /work/benchmark/ucloud-benchmark/run-svc-2020-2022/

python3 -m pip install --quiet -r requirements.txt

PORTFOLIO="svc-k1"
CORES=8
year=2022
rep=2
export HELD_OUT_YEAR=2022

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=felix) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../initial-schedules/k1-initial.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/svc-2020-2022/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} \
        --ai command-line --ai-config command="./svc-k1/svc_k1.py" \
        --output-solver --solver-config-mode cache --verbosity error \
        --static-runtime 0
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
