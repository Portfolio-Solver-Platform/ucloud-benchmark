#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="cpsat8"
CORES=8

for year in 2017 2018 2019; do
    echo "=== ${PORTFOLIO} ${year} ==="
    python ../benchmark_parasol.py -s "../solvers/cpsat8.csv" \
        -r 1 -t 1200 \
        -o "../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-${year}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
done 2>&1 | tee ${PORTFOLIO}-p3-out.txt
