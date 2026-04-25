#!/bin/bash
# Run 2022 for k1-8c-8s-v1. The 2021 set is considered complete on disk
# already (95 real rows + at most 1 fake yumi-dynamic row to be cleaned up
# manually) — yumi-dynamic.mzn does not compile under the installed
# minizinc version (multiple `max(empty_set)` sites), so all 5 of its
# instances are unrunnable. Skipping rather than retrying.
set -o pipefail
cd "$(dirname "$0")"

PORTFOLIO="k1-8c-8s-v1"
CORES=8

{
  echo "=== ${PORTFOLIO} 2022 ==="
  python ../../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
      -r 1 -t 1200 \
      -o "../../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-2022" \
      --problems-path "../../../data/mzn-challenge/2022" \
      --discover \
      -- --solver parasol -p ${CORES} --ai none --output-solver \
      --solver-config-mode cache --verbosity error \
      --static-runtime 100000000 || echo "!! 2022 exited non-zero: $?"

  echo "=== done ==="
} 2>&1 | tee "${PORTFOLIO}-resume-out.txt"
