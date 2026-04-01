#!/bin/bash
set -e
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Choco 4-core ${year} ==="
    python benchmark_solvers.py -s org.choco.choco -p 4 -r 1 -t 1200 \
        -o "../results/choco/choco4-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done
