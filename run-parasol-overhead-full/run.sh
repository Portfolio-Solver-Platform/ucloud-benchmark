#!/bin/bash
# Full sweep: every 2023-2025 instance run twice (standalone cp-sat,8 and
# parasol cp-sat,8), with a short 20s timeout. Designed to detect parasol's
# constant per-invocation overhead on a clean machine without spending hours
# on hard instances.
#
# Usage:
#   ./run.sh                     # default 20s timeout, 1 rep each
#   TIMEOUT_S=30 ./run.sh        # different timeout
#   ./run.sh 2024                # restrict to one year
set -eo pipefail
cd "$(dirname "$0")"

TIMEOUT_S="${TIMEOUT_S:-20}"
N_RUNS="${N_RUNS:-1}"
YEARS=("${@:-2023 2024 2025}")

BENCHMARK_DIR="$(cd .. && pwd)"          # /home/sofus/speciale/ai/ucloud
DATA_BASE="$(cd ../../data && pwd)"
RESULTS_DIR="$(cd ../.. && pwd)/results/parasol-overhead-full"
mkdir -p "${RESULTS_DIR}"

echo "=== parasol-overhead full sweep ==="
echo "  TIMEOUT_S = ${TIMEOUT_S}"
echo "  N_RUNS    = ${N_RUNS}"
echo "  YEARS     = ${YEARS[*]}"
echo "  output    = ${RESULTS_DIR}"
echo ""

run_year_mode() {
    local year="$1" mode="$2"
    local data_dir="${DATA_BASE}/mznc${year}_probs"

    if [ ! -d "$data_dir" ]; then
        echo "!! missing $data_dir; skipping $year"
        return
    fi

    if [ "$mode" = "standalone" ]; then
        echo "=== [${year} / standalone] ==="
        docker run --rm \
            -v "${BENCHMARK_DIR}:/benchmark" \
            -v "${data_dir}:/problems" \
            -v "${RESULTS_DIR}:/results" \
            -w /benchmark \
            parasol \
            python3.13 benchmark_solvers.py \
                -s cp-sat -p 8 -r "${N_RUNS}" -t "${TIMEOUT_S}" \
                -o "/results/standalone-${year}" \
                --problems-path /problems \
                --discover
    elif [ "$mode" = "parasol" ]; then
        echo "=== [${year} / parasol] ==="
        docker run --rm \
            -v "${BENCHMARK_DIR}:/benchmark" \
            -v "${data_dir}:/problems" \
            -v "${RESULTS_DIR}:/results" \
            -w /benchmark \
            parasol \
            python3.13 benchmark_parasol.py \
                -s solvers/cpsat8.csv -r "${N_RUNS}" -t "${TIMEOUT_S}" \
                -o "/results/parasol-${year}" \
                --problems-path /problems \
                --discover \
                -- --solver parasol -p 8 --ai none --output-solver \
                   --solver-config-mode cache --verbosity error \
                   --static-runtime 100000000
    fi
}

for year in ${YEARS[@]}; do
    run_year_mode "$year" "standalone" 2>&1 | tee "out-standalone-${year}.txt"
    run_year_mode "$year" "parasol"    2>&1 | tee "out-parasol-${year}.txt"
done

echo ""
echo "=== summary ==="
python3 analyze.py "${RESULTS_DIR}"
