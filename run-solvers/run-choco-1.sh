#!/bin/bash
set -e
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Choco 1-core ${year} ==="
    python benchmark_solvers.py -s org.choco.choco -p 1 -r 1 -t 1200 \
        -o "../results/choco/choco1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee choco1-out.txt
