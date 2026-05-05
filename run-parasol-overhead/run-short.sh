#!/bin/bash
# Parasol-vs-standalone replication on SHORT instances (1-5 s standalone), where
# cp-sat run-to-run variance is small enough that any constant per-invocation
# overhead from parasol should be cleanly detectable.
#
# Default 10 reps each (override with first arg or N_RUNS env).
#
# Companion to run.sh which uses medium-range (~40-80 s) instances.
set -eo pipefail
cd "$(dirname "$0")"

N_RUNS="${1:-${N_RUNS:-10}}"
TIMEOUT_S="${TIMEOUT_S:-60}"

BENCHMARK_DIR="$(cd .. && pwd)"
DATA_DIR="$(cd ../../data/mznc2025_probs && pwd)"
RESULTS_DIR="$(cd ../.. && pwd)/results/parasol-overhead-replication-short"
mkdir -p "${RESULTS_DIR}"

INSTANCES=(
    "atsp/atsp.mzn:atsp/instance11_0p25.dzn"          # ~1.2s standalone
    "hitori/hitori.mzn:hitori/h11-1.dzn"              # ~2.8s standalone
    "tower/tower.mzn:tower/tower_050_050_10_050-03.dzn"  # ~4.2s standalone
)

echo "=== parasol-overhead replication (SHORT instances) ==="
echo "  N_RUNS    = ${N_RUNS}"
echo "  timeout   = ${TIMEOUT_S}s"
echo "  instances = ${INSTANCES[*]}"
echo "  output    = ${RESULTS_DIR}"
echo ""

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
        --instances "${INSTANCES[@]}" 2>&1 | tee out-standalone-short.txt

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
           --static-runtime 100000000 2>&1 | tee out-parasol-short.txt

echo ""
echo "=== summary ==="
python3 analyze.py "${RESULTS_DIR}"
