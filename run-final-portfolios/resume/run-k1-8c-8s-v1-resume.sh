#!/bin/bash
# Re-run k1-8c-8s-v1 for 2021 (from scratch — prior partial folder was deleted)
# and 2022.
# No `set -e`: if 2021 crashes, 2022 should still be attempted.
set -o pipefail
cd "$(dirname "$0")"

PORTFOLIO="k1-8c-8s-v1"
CORES=8

{
  echo "=== ${PORTFOLIO} 2021 ==="
  python ../../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
      -r 1 -t 1200 \
      -o "../../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-2021" \
      --problems-path "../../../data/mzn-challenge/2021" \
      --discover \
      -- --solver parasol -p ${CORES} --ai none --output-solver \
      --solver-config-mode cache --verbosity error \
      --static-runtime 100000000 || echo "!! 2021 exited non-zero: $? — continuing to 2022"

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
