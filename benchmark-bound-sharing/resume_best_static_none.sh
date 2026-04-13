#!/bin/bash
set -eo pipefail

# Resume the best-static none run from where it stopped (after tower_070_070_30_100-02).
# The next instance is tower_500_500_50_300-05, covering the remaining 11 instances.

PORTFOLIO="best-static"

python ../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
    -r 1 -t 1200 \
    -o "../../results/${PORTFOLIO}-bound-sharing-2025-none" \
    --problems-path ../../data/mznc2025_probs \
    --discover \
    --start-from-instance tower_500_500_50_300-05 \
    -- --solver parasol -p 8 --ai none --output-solver \
    --solver-config-mode cache --verbosity error \
    --static-runtime 100000000
