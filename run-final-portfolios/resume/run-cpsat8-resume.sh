#!/bin/bash
# Resume cpsat8 shard p4 from where it crashed in 2021 (inside the connect
# problem, at the 3rd connect model), then run 2022.
# No `set -e`: if 2021 crashes again, 2022 should still be attempted.
set -o pipefail
cd "$(dirname "$0")"

PORTFOLIO="cpsat8"
CORES=8

{
  echo "=== ${PORTFOLIO} 2021 (resume from connect__0061) ==="
  python ../../benchmark_parasol.py -s "../../solvers/${PORTFOLIO}.csv" \
      -r 1 -t 1200 \
      -o "../../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-2021" \
      --problems-path "../../../data/mzn-challenge/2021" \
      --discover \
      --start-from-instance "connect__0061" \
      -- --solver parasol -p ${CORES} --ai none --output-solver \
      --solver-config-mode cache --verbosity error \
      --static-runtime 100000000 || echo "!! 2021 exited non-zero: $? — continuing to 2022"

  echo "=== ${PORTFOLIO} 2022 ==="
  python ../../benchmark_parasol.py -s "../../solvers/${PORTFOLIO}.csv" \
      -r 1 -t 1200 \
      -o "../../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-2022" \
      --problems-path "../../../data/mzn-challenge/2022" \
      --discover \
      -- --solver parasol -p ${CORES} --ai none --output-solver \
      --solver-config-mode cache --verbosity error \
      --static-runtime 100000000 || echo "!! 2022 exited non-zero: $?"

  echo "=== done ==="
} 2>&1 | tee "${PORTFOLIO}-resume-out.txt"
