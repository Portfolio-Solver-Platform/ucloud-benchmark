#!/bin/bash
set -e
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Choco 2-core ${year} ==="
    python benchmark_solvers.py -s org.choco.choco -p 2 -r 1 -t 1200 \
        -o "../results/choco/choco2-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done
