#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."

INSTANCES=(
    "work-task-variation/work-task-variation.mzn:work-task-variation/generated-seed-4-length-14-open-12-workers-12-block-15.dzn"
    "EchoSched/JSP0.mzn:EchoSched/13-14-0-2_6.dzn"
    "products-and-shelves/product-and-shelves.mzn:products-and-shelves/ps-50-09.dzn"
    "atsp/atsp.mzn:atsp/instance4_0p15.dzn"
    "hitori/hitori.mzn:hitori/h14-1.dzn"
)

echo "=== local-vs-platform: cp-sat 8c, 3 runs ==="
python benchmark_solvers.py -s cp-sat -p 8 -r 3 -t 1200 \
    -o "../results/local-vs-platform" \
    --problems-path "../data/mznc2025_probs" \
    --instances "${INSTANCES[@]}" 2>&1 | tee run-local-vs-platform/out.txt
