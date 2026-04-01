#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Scip 1-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.scip -p 1 -r 1 -t 1200 \
        -o "../results/scip/scip1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee scip1-out.txt
