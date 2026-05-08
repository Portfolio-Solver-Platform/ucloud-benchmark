#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="cpsat8"
CORES=8
year=2012
rep=3

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=default,cpsat-no-gurobi) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../solvers/cpsat8.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/final-many-reps/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
