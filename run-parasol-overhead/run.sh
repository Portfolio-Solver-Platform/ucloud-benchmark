#!/bin/bash
# Replicate the parasol-vs-standalone overhead measurement on two specific instances:
#   hitori/h14-1            (SAT puzzle, ~250s standalone)
#   EchoSched/14-10-0-2_3   (job-shop variant, ~120s standalone)
#
# Both modes use cp-sat with 8 cores. Difference:
#   - standalone:  minizinc --solver cp-sat -p 8
#   - parasol   :  minizinc --solver parasol --static-schedule cpsat8.csv -p 8
#
# Usage:
#   ./run.sh             # default 6 reps per (instance, mode)
#   ./run.sh 3           # 3 reps
#   N_RUNS=10 ./run.sh   # 10 reps via env
set -eo pipefail
cd "$(dirname "$0")"

N_RUNS="${1:-${N_RUNS:-6}}"
TIMEOUT_S="${TIMEOUT_S:-1200}"

BENCHMARK_DIR="$(cd .. && pwd)"          # /home/sofus/speciale/ai/ucloud
DATA_DIR="$(cd ../../data/mznc2025_probs && pwd)"
RESULTS_DIR="$(cd ../.. && pwd)/results/parasol-overhead-replication"
SCHEDULE_HOST="${BENCHMARK_DIR}/solvers/cpsat8.csv"
mkdir -p "${RESULTS_DIR}"

INSTANCES=(
    "hitori/hitori.mzn:hitori/h14-1.dzn"
    "EchoSched/JSP0.mzn:EchoSched/14-10-0-2_3.dzn"
)

echo "=== parasol-overhead replication ==="
echo "  N_RUNS    = ${N_RUNS}"
echo "  timeout   = ${TIMEOUT_S}s"
echo "  instances = ${INSTANCES[*]}"
echo "  output    = ${RESULTS_DIR}"
echo ""

# --- mode 1: standalone cp-sat,8 ---
echo "=== [1/2] standalone (minizinc --solver cp-sat -p 8) ==="
docker run --rm \
    -v "${BENCHMARK_DIR}:/benchmark" \
    -v "${DATA_DIR}:/problems" \
    -v "${RESULTS_DIR}:/results" \
    -w /benchmark \
    parasol \
    python3.13 benchmark_solvers.py \
        -s cp-sat -p 8 -r "${N_RUNS}" -t "${TIMEOUT_S}" \
        -o /results/standalone \
        --problems-path /problems \
        --instances "${INSTANCES[@]}" 2>&1 | tee out-standalone.txt

echo ""
echo "=== [2/2] parasol (--solver parasol --static-schedule cpsat8.csv -p 8) ==="
docker run --rm \
    -v "${BENCHMARK_DIR}:/benchmark" \
    -v "${DATA_DIR}:/problems" \
    -v "${RESULTS_DIR}:/results" \
    -w /benchmark \
    parasol \
    python3.13 benchmark_parasol.py \
        -s solvers/cpsat8.csv -r "${N_RUNS}" -t "${TIMEOUT_S}" \
        -o /results/parasol \
        --problems-path /problems \
        --instances "${INSTANCES[@]}" \
        -- --solver parasol -p 8 --ai none --output-solver \
           --solver-config-mode cache --verbosity error \
           --static-runtime 100000000 2>&1 | tee out-parasol.txt

echo ""
echo "=== summary ==="
python3 analyze.py "${RESULTS_DIR}"
