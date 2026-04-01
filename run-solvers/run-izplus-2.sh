#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Izplus 2-core ${year} ==="
    python benchmark_solvers.py -s izplus -p 2 -r 1 -t 1200 \
        -o "../results/izplus/izplus2-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee izplus2-out.txt
