#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi-astrid.lic
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="ek1-8c-8s-v2"
CORES=8
year=2025
rep=3

{
    echo "=== TEST ${PORTFOLIO} ${year} r${rep} (license=astrid) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../schedules-eligible/ek1-8c-8s-v2.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/test-orchestrator/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 2 --cores ${CORES} \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
