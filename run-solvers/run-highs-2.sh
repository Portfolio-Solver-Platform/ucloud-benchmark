#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Highs 2-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.highs -p 2 -r 1 -t 1200 \
        -o "../results/highs/highs2-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee highs2-out.txt
