#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Coin-bc 8-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.coin-bc -p 8 -r 1 -t 1200 \
        -o "../results/coin-bc/coin-bc8-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee coin-bc8-out.txt
