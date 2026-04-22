#!/bin/bash
set -eo pipefail

PORTFOLIO="ek1-8c-8s-v2"
INTERVALS=(256)

{
for interval in "${INTERVALS[@]}"; do
    echo "=== restart-interval=$interval ==="
    python ../../benchmark_parasol.py -s "../../schedules-eligible/${PORTFOLIO}.csv" \
        -r 1 -t 1200 \
        -o "../../../results/${PORTFOLIO}/${PORTFOLIO}-bound-sharing-2025-${interval}s" \
        --problems-path "../../../data/mznc2025_probs" \
        --discover \
        -- --solver parasol -p 8 --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --restart-interval "$interval" \
        --static-runtime 0
done
} 2>&1 | tee bound-sharing-ek1-8c-8s-v2-part1-out.txt
