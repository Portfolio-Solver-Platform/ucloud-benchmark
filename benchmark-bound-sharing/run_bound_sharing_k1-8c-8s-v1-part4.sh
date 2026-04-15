#!/bin/bash
set -eo pipefail

PORTFOLIO="k1-8c-8s-v1"
INTERVALS=(192 224 256)

{
for interval in "${INTERVALS[@]}"; do
    echo "=== restart-interval=$interval ==="
    python ../benchmark_parasol.py -s "../schedules/${PORTFOLIO}.csv" \
        -r 1 -t 1200 \
        -o "../../results/${PORTFOLIO}/${PORTFOLIO}-bound-sharing-2025-${interval}s" \
        --problems-path "../../data/mznc2025_probs" \
        --discover \
        -- --solver parasol -p 8 --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --restart-interval "$interval" \
        --static-runtime 0
done

echo "=== no bound sharing ==="
python ../benchmark_parasol.py -s "../schedules/${PORTFOLIO}.csv" \
    -r 1 -t 1200 \
    -o "../../results/${PORTFOLIO}/${PORTFOLIO}-bound-sharing-2025-none" \
    --problems-path "../../data/mznc2025_probs" \
    --discover \
    -- --solver parasol -p 8 --ai none --output-solver \
    --solver-config-mode cache --verbosity error \
    --static-runtime 100000000
} 2>&1 | tee bound-sharing-k1-8c-8s-v1-part4-out.txt
