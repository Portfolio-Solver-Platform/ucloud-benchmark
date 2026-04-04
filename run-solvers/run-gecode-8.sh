#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Gecode 8-core ${year} ==="
    python benchmark_solvers.py -s org.gecode.gecode -p 8 -r 1 -t 1200 \
        -o "../results/gecode/gecode8-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee gecode8-out.txt
