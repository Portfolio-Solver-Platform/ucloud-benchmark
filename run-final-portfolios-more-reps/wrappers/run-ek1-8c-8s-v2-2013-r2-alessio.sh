#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi-alessio.lic
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="ek1-8c-8s-v2"
CORES=8
year=2013
rep=2

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=alessio) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../schedules-eligible/ek1-8c-8s-v2.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/final-many-reps/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
