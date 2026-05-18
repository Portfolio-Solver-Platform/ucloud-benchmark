#!/usr/bin/env python3
"""Parasol scheduler (cpsat8 vs k1-no-yuck) for LOYO evaluation.

The held-out year is read from the HELD_OUT_YEAR env var; the matching
data/svc_k1_no$YEAR.joblib model is loaded. Per-call decisions are
appended to ai_choices.csv next to this script.
"""

import argparse
import os
import time

import joblib
import numpy as np

from svc_common import BagSVCPredictor, SignedLog1p  # noqa: F401

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHOICE_LOG = os.path.join(SCRIPT_DIR, "ai_choices.csv")

CP_SAT_ID = "cp-sat"
CHUFFED_ID = "org.chuffed.chuffed"
GECODE_ID = "org.gecode.gecode"
GUROBI_ID = "org.minizinc.mip.gurobi"
PICAT_ID = "org.picat-lang.picat"
YUCK_ID = "yuck"


def parse_comma_separated_floats(input_str):
    return np.array([float(x) for x in input_str.split(",")])


def schedule(features, total_cores):
    year = os.environ.get("HELD_OUT_YEAR")
    if not year:
        raise RuntimeError("HELD_OUT_YEAR env var must be set")
    model_path = os.path.join(SCRIPT_DIR, "data", f"svc_k1_no{year}.joblib")
    model = joblib.load(model_path)

    pred = int(model.predict(features.reshape(1, -1))[0])
    if pred == 0:
        return [(CP_SAT_ID, 8)]
    return [
        (CP_SAT_ID, 1),
        (CHUFFED_ID, 1),
        (GECODE_ID, 2),
        (GUROBI_ID, 2),
        (PICAT_ID, 1),
        (YUCK_ID, 1),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("features", type=parse_comma_separated_floats)
    parser.add_argument("-p", required=True, type=int, dest="cores")
    args = parser.parse_args()
    sched = schedule(args.features, args.cores)

    portfolio = "cpsat" if len(sched) == 1 else "k1-no-yuck"
    sched_str = ";".join(f"{s}:{c}" for s, c in sched)
    new = not os.path.exists(CHOICE_LOG)
    with open(CHOICE_LOG, "a") as f:
        if new:
            f.write("timestamp,year,predicted,schedule\n")
        f.write(f"{time.time():.3f},{os.environ.get('HELD_OUT_YEAR','')},"
                f"{portfolio},{sched_str}\n")

    for solver, cores in sched:
        print(f"{solver},{cores}")


if __name__ == "__main__":
    main()
