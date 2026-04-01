#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Yuck 2-core ${year} ==="
    python benchmark_solvers.py -s yuck -p 2 -r 1 -t 1200 \
        -o "../results/yuck/yuck2-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee yuck2-out.txt
