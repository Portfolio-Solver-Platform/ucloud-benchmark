#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="k3-8c-8s-v2-p2"
CORES=8

for year in 2025 2024 2023; do
    echo "=== ${PORTFOLIO} ${year} ==="
    python ../benchmark_parasol.py -s "../schedules/${PORTFOLIO}.csv" \
        -r 1 -t 1200 \
        -o "../../results/portfolios/${PORTFOLIO}/${PORTFOLIO}-${year}" \
        --problems-path "../../data/mznc${year}_probs" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
done 2>&1 | tee ${PORTFOLIO}-out.txt
