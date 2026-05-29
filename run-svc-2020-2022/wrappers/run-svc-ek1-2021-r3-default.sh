#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi.lic
cd /work/benchmark/ucloud-benchmark/run-svc-2020-2022/


PORTFOLIO="svc-ek1"
CORES=8
year=2021
rep=3

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=default) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../initial-schedules/ek1-initial.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/svc-2020-2022/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} \
        --ai svc-ek1 --ai-config held-out-year=${year} \
        --output-solver --solver-config-mode cache --verbosity error \
        --static-runtime 0 --restart-interval 10000000000
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
