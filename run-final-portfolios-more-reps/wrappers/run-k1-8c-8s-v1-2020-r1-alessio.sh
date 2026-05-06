#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi-alessio.lic
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="k1-8c-8s-v1"
CORES=8
year=2020
rep=1

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=alessio) ==="
    python ../benchmark_parasol.py -s "../schedules/k1-8c-8s-v1.csv" \
        -r 1 -t 1200 \
        -o "../../results/final-many-reps/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-r${rep}-out.txt
