#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== CPLEX 1-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.cplex -p 1 -r 1 -t 1200 \
        -o "../results/cplex/cplex1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee cplex1-out.txt
