#!/bin/bash
# Resume k1-8c-8s-v1 shard p4 from where it crashed in 2021
# (last row written was the final wmsmc-int instance; missing problem is yumi-dynamic),
# then run 2022.
# No `set -e`: if 2021 crashes again, 2022 should still be attempted.
set -o pipefail
cd "$(dirname "$0")"

PORTFOLIO="k1-8c-8s-v1"
CORES=8

{
  echo "=== ${PORTFOLIO} 2021 (resume from first yumi-dynamic file) ==="
  python ../../benchmark_parasol.py -s "../../schedules/${PORTFOLIO}.csv" \
      -r 1 -t 1200 \
      -o "../../../results/portfolios-final/${PORTFOLIO}/${PORTFOLIO}-2021" \
      --problems-path "../../../data/mzn-challenge/2021" \
      --discover \
      --start-from-instance "p_10_SSSSSS_SSSS_yumi_grid_setup_3_3_zones" \
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
