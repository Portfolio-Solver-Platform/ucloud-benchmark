#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="k1-8c-8s-v1"
CORES=8

for year in 2023 2024 2025; do
    echo "=== ${PORTFOLIO} ${year} ==="
    python ../benchmark_parasol.py -s "../schedules/k1-8c-8s-v1.csv" \
        -r 1 -t 1200 \
        -o "../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-${year}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
done 2>&1 | tee ${PORTFOLIO}-p5-out.txt
