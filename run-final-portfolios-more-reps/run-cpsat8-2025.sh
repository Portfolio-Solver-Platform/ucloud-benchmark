#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="cpsat8"
CORES=8
year=2025

{
    echo "=== ${PORTFOLIO} ${year} ==="
    python ../benchmark_parasol.py -s "../solvers/cpsat8.csv" \
        -r 3 -t 1200 \
        -o "../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-${year}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-out.txt
