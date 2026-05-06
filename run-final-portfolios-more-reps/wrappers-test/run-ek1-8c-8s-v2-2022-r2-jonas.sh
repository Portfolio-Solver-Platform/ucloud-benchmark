#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi-jonas.lic
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="ek1-8c-8s-v2"
CORES=8
year=2022
rep=2

{
    echo "=== TEST ${PORTFOLIO} ${year} r${rep} (license=jonas) ==="
    python ../benchmark_parasol.py -s "../schedules-eligible/ek1-8c-8s-v2.csv" \
        -r 1 -t 2 \
        -o "../../results/test-orchestrator/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-r${rep}-out.txt
