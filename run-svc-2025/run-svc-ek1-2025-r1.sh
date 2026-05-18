#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi.lic
cd /work/benchmark/ucloud-benchmark/run-svc-2025/

PORTFOLIO="svc-ek1"
CORES=8
year=2025
rep=1

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=default) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../schedules-eligible/ek1-8c-8s-v2.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/svc-2025/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} \
        --ai command-line --ai-config command="./svc-ek1/svc_ek1_2011_2024.py" \
        --output-solver --solver-config-mode cache --verbosity error \
        --static-runtime 0
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
