#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Gurobi 8-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.gurobi -p 8 -r 1 -t 1200 \
        -o "../results/gurobi/gurobi8-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee gurobi8-out.txt
