#!/bin/bash
# Runs the medium-hard instances (60-1200s on uCloud cp-sat,8) on the local
# machine, in both standalone-cp-sat-8 and parasol modes, with a 600s timeout.
# Local is roughly 3x faster than uCloud, so 600s comfortably fits anything
# that finished within 1200s on uCloud.
#
# Usage:
#   ./run.sh             # default 600s timeout, 1 rep
#   TIMEOUT_S=900 ./run.sh
set -eo pipefail
cd "$(dirname "$0")"

TIMEOUT_S="${TIMEOUT_S:-600}"
N_RUNS="${N_RUNS:-1}"

BENCHMARK_DIR="$(cd .. && pwd)"
DATA_BASE="$(cd ../../data && pwd)"
RESULTS_DIR="$(cd ../.. && pwd)/results/parasol-overhead-medium"
mkdir -p "${RESULTS_DIR}"

# Source the per-year instance arrays
source "$(dirname "$0")/instances.sh"

echo "=== parasol-overhead medium-hard sweep ==="
echo "  TIMEOUT_S = ${TIMEOUT_S}"
echo "  N_RUNS    = ${N_RUNS}"
echo "  output    = ${RESULTS_DIR}"
echo ""

run_year_mode() {
    local year="$1" mode="$2"
    local data_dir="${DATA_BASE}/mznc${year}_probs"
    local arr_name="INSTANCES_${year}[@]"
    local instances=("${!arr_name}")

    if [ ${#instances[@]} -eq 0 ]; then
        echo "  no instances for $year, skipping $mode"
        return
    fi

    if [ "$mode" = "standalone" ]; then
        echo "=== [${year} / standalone] (${#instances[@]} instances) ==="
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
                --instances "${instances[@]}"
    elif [ "$mode" = "parasol" ]; then
        echo "=== [${year} / parasol] (${#instances[@]} instances) ==="
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
                --instances "${instances[@]}" \
                -- --solver parasol -p 8 --ai none --output-solver \
                   --solver-config-mode cache --verbosity error \
                   --static-runtime 100000000
    fi
}

for year in 2025; do
    run_year_mode "$year" "standalone" 2>&1 | tee "out-standalone-${year}.txt"
    run_year_mode "$year" "parasol"    2>&1 | tee "out-parasol-${year}.txt"
done

echo ""
echo "=== combined analysis (medium + existing 0-20s short data) ==="
python3 analyze.py "${RESULTS_DIR}" /home/sofus/speciale/ai/results/parasol-overhead-full
