#!/bin/bash
set -eo pipefail

PORTFOLIO="ek1-8c-8s-v2"

{


echo "=== no bound sharing ==="
python ../../benchmark_parasol.py -s "../../schedules-eligible/${PORTFOLIO}.csv" \
    -r 1 -t 1200 \
    -o "../../../results/${PORTFOLIO}/${PORTFOLIO}-bound-sharing-2025-none-v2" \
    --problems-path "../../../data/mznc2025_probs" \
    --discover \
    -- --solver parasol -p 8 --ai none --output-solver \
    --solver-config-mode cache --verbosity error \
    --static-runtime 100000000
} 2>&1 | tee bound-sharing-ek1-8c-8s-v2-none-out.txt
