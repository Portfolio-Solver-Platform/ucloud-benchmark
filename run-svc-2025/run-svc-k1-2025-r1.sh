#!/bin/bash
set -eo pipefail
source /work/minizinc/scripts/setup-env.sh --gurobi-license /work/minizinc/solvers/gurobi/gurobi.lic
cd /work/benchmark/ucloud-benchmark/run-svc-2025/

echo "--- installing Python deps ---"
python3 -m pip install --quiet -r requirements.txt

echo "--- AI smoke-test: ./svc-k1/svc_k1_2011_2024.py on a zero vector ---"
ZERO="$(printf '0%.0s' {1..95} | sed 's/0/0,/g; s/,$//')"
SMOKE_OUT="$(./svc-k1/svc_k1_2011_2024.py "$ZERO" -p 8 2>&1)" || {
    echo "AI script failed -- output below"
    echo "$SMOKE_OUT"
    exit 1
}
echo "smoke-test output:"
echo "$SMOKE_OUT"

PORTFOLIO="svc-k1"
CORES=8
year=2025
rep=1

{
    echo "=== ${PORTFOLIO} ${year} r${rep} (license=default) ==="
    python3 -u ../per_problem_runner.py \
        --portfolio "${PORTFOLIO}" --year ${year} --rep ${rep} \
        --schedule "../schedules/k1-8c-8s-v1.csv" \
        --problems-path "../../data/mzn-challenge/${year}" \
        --output-dir "../../results/svc-2025/${PORTFOLIO}/${PORTFOLIO}-${year}-r${rep}" \
        --timeout 1200 --cores ${CORES} \
        -- --solver parasol -p ${CORES} \
        --ai command-line --ai-config command="./svc-k1/svc_k1_2011_2024.py" \
        --output-solver --solver-config-mode cache --verbosity error \
        --static-runtime 0
} 2>&1 | tee -a ${PORTFOLIO}-${year}-r${rep}-out.txt
