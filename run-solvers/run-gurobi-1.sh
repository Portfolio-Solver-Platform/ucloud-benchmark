#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Gurobi 1-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.gurobi -p 1 -r 1 -t 1200 \
        -o "../results/gurobi/gurobi1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee gurobi1-out.txt
