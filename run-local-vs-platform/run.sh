#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

# Resolve to absolute paths (docker -v requires them)
BENCHMARK_DIR="$(cd .. && pwd)"
DATA_DIR="$(cd ../../data/mznc2025_probs && pwd)"
RESULTS_DIR="$(cd ../.. && pwd)/results"
mkdir -p "$RESULTS_DIR/local-vs-platform"

INSTANCES=(
    "EchoSched/JSP0.mzn:EchoSched/14-10-0-2_3.dzn"
    "fbd1/FBD1.mzn:fbd1/FBDk07.dzn"
    "atsp/atsp.mzn:atsp/instance4_0p15.dzn"
    "hitori/hitori.mzn:hitori/h14-1.dzn"
    "ihtc-2024-kletzander/model4_opt.mzn:ihtc-2024-kletzander/test03.dzn"
)

echo "=== local-vs-platform (docker): cp-sat 8c, 3 runs ==="
docker run --rm \
    -v "${BENCHMARK_DIR}:/benchmark" \
    -v "${DATA_DIR}:/problems" \
    -v "${RESULTS_DIR}:/results" \
    -w /benchmark \
    parasol \
    python3.13 benchmark_solvers.py \
        -s cp-sat -p 8 -r 3 -t 1200 \
        -o /results/local-vs-platform \
        --problems-path /problems \
        --instances "${INSTANCES[@]}" 2>&1 | tee out.txt
