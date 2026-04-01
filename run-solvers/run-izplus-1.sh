#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Izplus 1-core ${year} ==="
    python benchmark_solvers.py -s izplus -p 1 -r 1 -t 1200 \
        -o "../results/izplus/izplus1-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee izplus1-out.txt
