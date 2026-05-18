"""
Compare svc_k1.py and svc_ek1.py predictions against the 2008 portfolio
runtimes we just produced (cpsat8 / k1-8c-8s-v1 / ek1-8c-8s-v2 CSVs).

For each instance we compute the pairwise Borda the same way as training:
  pairwise_score(rowA, rowB, kind) ∈ {1, 0.5, 0} for (A wins, tie, A loses)
where rows are dicts with status/objective/time_ms keys. The binary
"true class" for the k1 model is then 1 if k1 outscores cpsat on that
instance and 0 otherwise (and likewise ek1 vs cpsat).

Outputs:
  - per_instance.csv  (one row per (instance, model) with prediction vs truth)
  - prints a summary table (acc, borda totals)
"""
from __future__ import annotations
import csv
import pickle
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
AI_TOOLS = Path("/home/sofus/speciale/ai/ai-tools")
PARASOL_CLI = Path("/home/sofus/speciale/ai/parasol/command-line-ai")

# Make the parasol BagSVCPredictor importable for joblib.
sys.path.insert(0, str(PARASOL_CLI))
from svc_common import BagSVCPredictor, SignedLog1p  # noqa: F401

# Re-use the SAME Borda scoring as build_training_data.py.
sys.path.insert(0, str(AI_TOOLS / "benchmarks" / "scoring"))
from borda import load_problem_types, pairwise_score

# Problem-type lookup (SAT / MIN / MAX) — same source as training.
PROBLEM_TYPES_CSV = AI_TOOLS / "benchmarks/open-category-benchmarks/problem_types.csv"
problem_types = load_problem_types(PROBLEM_TYPES_CSV)

# ---- load the 3 result CSVs ----
def load_results(name: str) -> dict[tuple[str, str], dict]:
    """Returns {(problem, instance_name): {status, objective, time_ms, ...}}."""
    out = {}
    with open(RESULTS / f"{name}.csv") as f:
        for r in csv.DictReader(f):
            out[(r["problem"], r["name"])] = r
    return out

cpsat = load_results("cpsat8")
k1    = load_results("k1-8c-8s-v1")
ek1   = load_results("ek1-8c-8s-v2")

# ---- load the 2008 features pkl and align it to the result CSV keys ----
with open(AI_TOOLS / "data" / "mznc2008_features.pkl", "rb") as f:
    feats = pickle.load(f)

def parse_key(key, problems):
    for p in sorted(problems, key=len, reverse=True):
        if key.startswith(p + "_"):
            rest = key[len(p) + 1:]
            for m in sorted(problems + [p], key=len, reverse=True):
                if rest.startswith(m + "_"):
                    return p, m, rest[len(m) + 1:]
                if rest == m:
                    return p, m, ""
            return p, rest, ""
    return None

problems_on_disk = list({pk[0] for pk in cpsat})  # problem dirs in CSV

instances = []  # list of dicts: {problem, name, X, results_per_portfolio}
for key, vec in sorted(feats.items()):
    if vec is None:
        continue
    parsed = parse_key(key, problems_on_disk)
    if parsed is None:
        continue
    p, m, name = parsed
    rkey = (p, name)
    if rkey not in cpsat or rkey not in k1 or rkey not in ek1:
        continue
    instances.append({
        "problem": p, "name": name,
        "X": np.asarray(vec, dtype=np.float64).reshape(1, -1),
        "cpsat": cpsat[rkey],
        "k1":    k1[rkey],
        "ek1":   ek1[rkey],
    })
print(f"Aligned {len(instances)} instances with features + results.")

# ---- compute pairwise Borda per instance (cpsat vs k1, cpsat vs ek1) ----
def row_for_borda(r):
    """Map the result CSV row into the dict shape pairwise_score expects."""
    obj = r.get("objective") or ""
    return {
        "status":    r["status"],
        "objective": obj,
        "time_ms":   r["time_ms"],
    }

def borda_pair(a, b, kind):
    """Returns (a_score, b_score) — each in {1, 0.5, 0}."""
    ra, rb = row_for_borda(a), row_for_borda(b)
    s = pairwise_score(ra, rb, kind)
    return s, 1 - s

# ---- run the SVC models on each instance ----
mk1  = joblib.load(PARASOL_CLI / "data" / "svc_k1_model.joblib")
mek1 = joblib.load(PARASOL_CLI / "data" / "svc_ek1_model.joblib")

per_inst = []
for inst in instances:
    p, n, X = inst["problem"], inst["name"], inst["X"]
    # Find kind (SAT/MIN/MAX). The (problem, model) key uses the model name.
    # All 2008 models we have features for happen to be problem==model, but
    # build_training_data.make_key uses (problem, model) verbatim, so look
    # both up.
    kind = problem_types.get((p, p)) or problem_types.get((p, inst["cpsat"]["model"]))
    if kind is None:
        # If unknown, treat as SAT.
        kind = "SAT"
    a_cpsat_k1, a_k1 = borda_pair(inst["cpsat"], inst["k1"], kind)
    a_cpsat_ek1, a_ek1 = borda_pair(inst["cpsat"], inst["ek1"], kind)

    # Binary "true class": 1 if non-cpsat wins (strictly), 0 if cpsat wins,
    # 0.5 (tie) treated as no-loss for either choice. Borda still records
    # the actual a-vs-b scores so the *picked-portfolio Borda* is meaningful
    # even on ties.
    truth_k1  = 1 if a_k1 > 0.5 else (0 if a_k1 < 0.5 else -1)
    truth_ek1 = 1 if a_ek1 > 0.5 else (0 if a_ek1 < 0.5 else -1)

    pred_k1  = int(mk1.predict(X)[0])
    pred_ek1 = int(mek1.predict(X)[0])

    per_inst.append({
        "problem": p, "name": n, "kind": kind,
        "cpsat_time": inst["cpsat"]["time_ms"],
        "k1_time":    inst["k1"]["time_ms"],
        "ek1_time":   inst["ek1"]["time_ms"],
        "borda_cpsat_in_k1_pair":  a_cpsat_k1,
        "borda_k1_in_k1_pair":     a_k1,
        "borda_cpsat_in_ek1_pair": a_cpsat_ek1,
        "borda_ek1_in_ek1_pair":   a_ek1,
        "truth_k1":  truth_k1,
        "pred_k1":   pred_k1,
        "truth_ek1": truth_ek1,
        "pred_ek1":  pred_ek1,
    })

# ---- print summary table ----
def summarize(rows, key_truth, key_pred, pair_label):
    n = len(rows)
    n_ties = sum(r[key_truth] == -1 for r in rows)
    n_nontie = n - n_ties
    if n_nontie == 0:
        acc = float("nan")
    else:
        correct = sum(r[key_truth] == r[key_pred]
                      for r in rows if r[key_truth] != -1)
        acc = correct / n_nontie

    # Borda actually achieved by following the model's pick.
    a = "borda_cpsat_in_" + pair_label
    b = "borda_" + ("k1" if "k1_pair" == pair_label else "ek1") + "_in_" + pair_label
    achieved = sum(r[a] if r[key_pred] == 0 else r[b] for r in rows)
    always_cpsat = sum(r[a] for r in rows)
    always_other = sum(r[b] for r in rows)
    oracle = sum(max(r[a], r[b]) for r in rows)

    print(f"\n--- {pair_label} ---")
    print(f"  n_total = {n}, n_ties = {n_ties}, n_non_tie = {n_nontie}")
    if n_nontie:
        print(f"  accuracy on non-tie instances: {acc*100:.1f}%")
    print(f"  Borda achieved by model:       {achieved:.2f}")
    print(f"  Borda from always-cpsat:       {always_cpsat:.2f}")
    other = "k1" if "k1_pair" == pair_label else "ek1"
    print(f"  Borda from always-{other}:        {always_other:.2f}")
    print(f"  Oracle (per-instance max):     {oracle:.2f}")
    n_pred_other = sum(r[key_pred] == 1 for r in rows)
    print(f"  Model picked '{other}' in {n_pred_other}/{n} instances")

print("=" * 60)
print(f"2008 OOD test — 20 instances, single rep, 300s cap")
print("=" * 60)
summarize(per_inst, "truth_k1",  "pred_k1",  "k1_pair")
summarize(per_inst, "truth_ek1", "pred_ek1", "ek1_pair")

# ---- write per-instance CSV for the report ----
out_csv = ROOT / "per_instance.csv"
with open(out_csv, "w", newline="") as f:
    fields = ["problem", "name", "kind",
              "cpsat_time", "k1_time", "ek1_time",
              "borda_cpsat_in_k1_pair", "borda_k1_in_k1_pair",
              "borda_cpsat_in_ek1_pair", "borda_ek1_in_ek1_pair",
              "truth_k1", "pred_k1", "truth_ek1", "pred_ek1"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in per_inst:
        w.writerow(r)
print(f"\nWrote {out_csv}")
