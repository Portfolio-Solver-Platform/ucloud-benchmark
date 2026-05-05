#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="ek1-8c-8s-v2"
CORES=8
year=2020

{
    echo "=== ${PORTFOLIO} ${year} ==="
    python ../benchmark_parasol.py -s "../schedules-eligible/${PORTFOLIO}.csv" \
        -r 3 -t 1200 \
        -o "../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-${year}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-out.txt
