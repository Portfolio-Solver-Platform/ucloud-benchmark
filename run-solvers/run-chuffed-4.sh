#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Chuffed 4-core ${year} ==="
    python benchmark_solvers.py -s org.chuffed.chuffed -p 4 -r 1 -t 1200 \
        -o "../results/chuffed/chuffed4-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee chuffed4-out.txt
