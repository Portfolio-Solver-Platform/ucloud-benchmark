#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

for year in 2023 2024 2025; do
    echo "=== Picat 8-core ${year} ==="
    python benchmark_solvers.py -s org.picat-lang.picat -p 8 -r 1 -t 1200 \
        -o "../results/picat/picat8-${year}" \
        --problems-path "../data/mznc${year}_probs" --discover
done 2>&1 | tee picat8-out.txt
