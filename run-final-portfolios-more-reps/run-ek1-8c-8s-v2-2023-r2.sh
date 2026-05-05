#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

PORTFOLIO="ek1-8c-8s-v2"
CORES=8
year=2023
rep=2

{
    echo "=== ${PORTFOLIO} ${year} r${rep} ==="
    python ../benchmark_parasol.py -s "../schedules-eligible/ek1-8c-8s-v2.csv" \
        -r 1 -t 1200 \
        -o "../../results/final-many-reps/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --discover \
        -- --solver parasol -p ${CORES} --ai none --output-solver \
        --solver-config-mode cache --verbosity error \
        --static-runtime 100000000
} 2>&1 | tee ${PORTFOLIO}-${year}-r${rep}-out.txt
