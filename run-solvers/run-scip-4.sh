#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Scip 4-core ${year} ==="
    python benchmark_solvers.py -s org.minizinc.mip.scip -p 4 -r 1 -t 1200 \
        -o "../results/scip/scip4-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee scip4-out.txt
