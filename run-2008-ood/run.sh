#!/usr/bin/env bash
# Run cpsat8 / k1-8c-8s-v1 / ek1-8c-8s-v2 portfolios on the exact instance set
# that the AI was trained on (i.e., the instances in the year's features pkl).
#
# This guarantees a 1-to-1 correspondence between portfolio runtimes (here)
# and feature vectors (in mznc<YEAR>_features.pkl), so the OOD comparison
# against svc_k1.py / svc_ek1.py predictions can run row-by-row.
#
# Usage:
#   ./run.sh                        # year=2008, cap=300s, single rep
#   YEAR=2010 ./run.sh
#   CAP_SEC=120 ./run.sh
#   REPS=3 ./run.sh                 # 3 reps to match training
#
# Re-running is safe: rows already in results/<portfolio>.csv are skipped.

set -eo pipefail

YEAR="${YEAR:-2008}"
CAP_SEC="${CAP_SEC:-300}"
REPS="${REPS:-1}"
PARASOL_IMG="${PARASOL_IMG:-parasol:latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
JOBS_HELPER="$SCRIPT_DIR/jobs_from_features.py"
INSTANCES_ROOT="$HOME/speciale/ai/data/mzn-challenge/$YEAR"
SCHED_CPSAT8="$HOME/speciale/ai/ucloud/solvers/cpsat8.csv"
SCHED_K1="$HOME/speciale/ai/ucloud/schedules/k1-8c-8s-v1.csv"
SCHED_EK1="$HOME/speciale/ai/ucloud/schedules-eligible/ek1-8c-8s-v2.csv"
GUROBI_LIC="$HOME/Documents/gurobi.lic"
PYTHON="${PYTHON:-/home/sofus/miniforge3/envs/ai/bin/python}"

for f in "$INSTANCES_ROOT" "$SCHED_CPSAT8" "$SCHED_K1" "$SCHED_EK1" "$GUROBI_LIC" "$JOBS_HELPER" "$PYTHON"; do
    if [ ! -e "$f" ]; then
        echo "ERROR: missing $f" >&2
        exit 1
    fi
done
if [ ! -f "/home/sofus/speciale/ai/ai-tools/data/mznc${YEAR}_features.pkl" ]; then
    echo "ERROR: no features pkl for $YEAR; can't establish instance set" >&2
    exit 1
fi

mkdir -p "$RESULTS_DIR"
echo "Year=$YEAR  cap=${CAP_SEC}s  reps=$REPS  image=$PARASOL_IMG"
echo "Instance set: from mznc${YEAR}_features.pkl (instances we have features for)"
echo

# Get the canonical job list from the features pkl.
mapfile -t JOBS < <("$PYTHON" "$JOBS_HELPER" "$YEAR" 2>/dev/null)
TOTAL_JOBS=${#JOBS[@]}
if [ "$TOTAL_JOBS" -eq 0 ]; then
    echo "ERROR: no jobs emitted from features pkl - check $JOBS_HELPER output" >&2
    exit 1
fi
echo "Discovered $TOTAL_JOBS instances; total runs = $((TOTAL_JOBS * 3 * REPS))"
echo

run_one () {
    local portfolio="$1"
    local portfolio_id="$2"
    local sched="$3"
    local problem="$4"
    local mzn_name="$5"
    local dzn_name="$6"
    local rep="$7"

    local out_csv="$RESULTS_DIR/$portfolio_id.csv"
    local name_no_ext="${dzn_name%.dzn}"

    if [ ! -f "$out_csv" ]; then
        echo "schedule,year,rep,problem,name,model,time_ms,objective,status" > "$out_csv"
    fi

    if awk -F, -v p="$problem" -v n="$name_no_ext" -v r="$rep" \
            'NR>1 && $4==p && $5==n && $3==r {found=1} END{exit !found}' \
            "$out_csv"; then
        printf "  [skip] %-13s %s/%s rep=%d\n" "$portfolio_id" "$problem" "$name_no_ext" "$rep"
        return
    fi

    printf "  [run]  %-13s %s/%s rep=%d ... " "$portfolio_id" "$problem" "$name_no_ext" "$rep"
    local start_ns end_ns wall_ms output objective status model_name
    start_ns=$(date +%s%N)
    output=$(docker run --rm \
        -v "$GUROBI_LIC:/opt/gurobi/gurobi.lic:ro" \
        -v "$sched:/sched.csv:ro" \
        -v "$INSTANCES_ROOT/$problem:/work:ro" \
        "$PARASOL_IMG" \
        minizinc --solver parasol -p 8 \
            --static-schedule /sched.csv --static-runtime "$CAP_SEC" \
            --ai none --solver-config-mode cache \
            --output-solver --output-time \
            -t $((CAP_SEC * 1000)) \
            "/work/$mzn_name" "/work/$dzn_name" 2>&1) || true
    end_ns=$(date +%s%N)
    wall_ms=$(( (end_ns - start_ns) / 1000000 ))

    objective=$(echo "$output" | grep -oE "_objective *= *-?[0-9.]+" | tail -1 \
                | grep -oE -- "-?[0-9.]+$" || true)

    # Status detection priority:
    #   CompileError > Unsat > Optimal > Satisfied > Unknown
    # `----------` (alone on a line) is MiniZinc's solution-found marker.
    # For COPs the last solution before `==========` is the proven optimum.
    # For CSPs (solve satisfy) there's only `----------` and no `_objective =`.
    status="Unknown"
    if echo "$output" | grep -qE "Error: type error"; then
        status="CompileError"
    elif echo "$output" | grep -qE "=====UNSATISFIABLE=====[[:space:]]*$"; then
        status="Unsat"
    elif echo "$output" | grep -qE "==========[[:space:]]*$"; then
        status="Optimal"
    elif echo "$output" | grep -qE "^----------[[:space:]]*$"; then
        status="Satisfied"
    fi
    [ -z "$objective" ] && objective=""
    model_name="${mzn_name%.mzn}"

    echo "${wall_ms}ms obj=${objective:-<none>} status=$status"
    echo "$portfolio_id,$YEAR,$rep,$problem,$name_no_ext,$model_name,$wall_ms,$objective,$status" \
        >> "$out_csv"
}

PORTFOLIOS=(
    "cpsat8|cpsat8|$SCHED_CPSAT8"
    "k1|k1-8c-8s-v1|$SCHED_K1"
    "ek1|ek1-8c-8s-v2|$SCHED_EK1"
)
for rep in $(seq 1 "$REPS"); do
    for entry in "${PORTFOLIOS[@]}"; do
        IFS='|' read -r short_name portfolio_id sched <<< "$entry"
        echo "==== rep=$rep portfolio=$portfolio_id ===="
        for job in "${JOBS[@]}"; do
            IFS='|' read -r problem mzn_name dzn_name <<< "$job"
            run_one "$short_name" "$portfolio_id" "$sched" \
                    "$problem" "$mzn_name" "$dzn_name" "$rep"
        done
        echo
    done
done

echo "Done. Per-portfolio CSVs in $RESULTS_DIR/:"
ls -la "$RESULTS_DIR/"
