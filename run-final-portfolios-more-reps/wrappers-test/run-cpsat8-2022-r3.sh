#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh
cd /work/benchmark/ucloud-benchmark/run-final-portfolios-more-reps/

PORTFOLIO="cpsat8"
CORES=8
year=2022
rep=3

{
    echo "=== TEST ${PORTFOLIO} ${year} r${rep} ==="
    python ../benchmark_parasol.py -s "../solvers/cpsat8.csv" \
        -r 1 -t 2 \
        -o "../../results/test-orchestrator/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-r${rep}-out.txt
