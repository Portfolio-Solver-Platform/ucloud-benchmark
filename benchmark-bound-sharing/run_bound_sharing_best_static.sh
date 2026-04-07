#!/bin/bash
set -eo pipefail

PORTFOLIO="best-static"
INTERVALS=(2 4 8 16 32 64 128 256 512)

{
for interval in "${INTERVALS[@]}"; do
    echo "=== Running with restart-interval=$interval ==="
    python ../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
        -r 1 -t 1200 \
        -o "../../results/${PORTFOLIO}-bound-sharing-2025-${interval}s" \
        --problems-path ../../data/mznc2025_probs \
        --discover \
        -- --solver parasol -p 8 --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --restart-interval "$interval" \
        --static-runtime 0
done

echo "=== Running with no bound sharing ==="
python ../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
    -r 1 -t 1200 \
    -o "../../results/${PORTFOLIO}-bound-sharing-2025-none" \
    --problems-path ../../data/mznc2025_probs \
    --discover \
    -- --solver parasol -p 8 --ai none --output-solver \
    --solver-config-mode cache --verbosity error \
    --static-runtime 100000000
} 2>&1 | tee bound-sharing-best-static-out.txt
