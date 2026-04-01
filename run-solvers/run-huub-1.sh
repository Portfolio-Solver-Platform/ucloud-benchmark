#!/bin/bash
set -e
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Huub 1-core ${year} ==="
    python benchmark_solvers.py -s solutions.huub -p 1 -r 1 -t 1200 \
        -o "../results/huub/huub1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done
