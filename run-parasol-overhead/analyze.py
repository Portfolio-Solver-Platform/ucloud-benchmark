#!/usr/bin/env python3
"""Aggregate replication results from run.sh into a per-instance comparison.

Reads:
  <results-dir>/standalone/results.csv   (from benchmark_solvers.py)
  <results-dir>/parasol/results.csv      (from benchmark_parasol.py)

Prints, for each instance:
  - N runs per mode
  - mean / median / stdev / min / max time_ms per mode
  - delta (parasol - standalone) on each statistic
"""
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path,
                    help="Directory containing standalone/ and parasol/ subdirs")
    args = ap.parse_args()

    standalone = load_csv(args.results_dir / "standalone" / "results.csv")
    parasol = load_csv(args.results_dir / "parasol" / "results.csv")

    if not standalone or not parasol:
        print(f"missing CSVs under {args.results_dir}", flush=True)
        return

    # Group by instance key
    def by_instance(rows: list[dict]) -> dict[tuple, list[float]]:
        out: dict[tuple, list[float]] = defaultdict(list)
        for r in rows:
            key = (r["problem"], r["name"])
            out[key].append(float(r["time_ms"]))
        return out

    s_by = by_instance(standalone)
    p_by = by_instance(parasol)

    keys = sorted(set(s_by) | set(p_by))
    rows_print = []
    for key in keys:
        s_t = s_by.get(key, [])
        p_t = p_by.get(key, [])
        if not s_t or not p_t:
            continue

        def stats(xs):
            return {
                "n": len(xs),
                "mean": statistics.mean(xs),
                "median": statistics.median(xs),
                "stdev": statistics.stdev(xs) if len(xs) > 1 else 0.0,
                "min": min(xs),
                "max": max(xs),
            }

        s = stats(s_t)
        p = stats(p_t)
        rows_print.append((key, s, p))

    if not rows_print:
        print("no overlapping instances")
        return

    for key, s, p in rows_print:
        print(f"\n--- {key[0]}/{key[1]} ---")
        print(f"{'metric':<10} {'standalone (ms)':>20} {'parasol (ms)':>20} {'delta (ms)':>14} {'delta (%)':>10}")
        for k in ["mean", "median", "stdev", "min", "max"]:
            sv, pv = s[k], p[k]
            d = pv - sv
            pct = (d / sv * 100) if sv else float("nan")
            print(f"{k:<10} {sv:>20,.0f} {pv:>20,.0f} {d:>+14,.0f} {pct:>+9.1f}%")
        print(f"{'n':<10} {s['n']:>20d} {p['n']:>20d}")

    # Cross-instance summary: median delta across the (instance-mean) values
    if len(rows_print) >= 2:
        print()
        deltas = [p["mean"] - s["mean"] for _, s, p in rows_print]
        ratios = [p["mean"] / s["mean"] for _, s, p in rows_print if s["mean"] > 0]
        print(f"=== aggregate over {len(rows_print)} instances ===")
        print(f"  mean of (parasol_mean - standalone_mean): {statistics.mean(deltas):>10,.0f} ms")
        print(f"  mean of (parasol_mean / standalone_mean): {statistics.mean(ratios):>10.2f}x")


if __name__ == "__main__":
    main()
