#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="cpsat8"
CORES=8
year=2023
rep=3

{
    echo "=== TEST ${PORTFOLIO} ${year} r${rep} ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../solvers/cpsat8.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/test-orchestrator/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 2 --cores ${CORES} \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
