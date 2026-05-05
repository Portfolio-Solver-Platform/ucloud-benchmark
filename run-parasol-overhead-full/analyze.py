#!/usr/bin/env python3
"""Analyze the parasol-overhead full sweep.

Walks <results-dir>/standalone-*/results.csv and parasol-*/results.csv,
joins by (year, problem, model, name), and produces:
  - merged.csv: one row per matched instance with both times
  - stdout summary: overall and per-year delta stats; constant-cost vs
    multiplicative-cost diagnostic.
"""
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> dict[tuple, dict]:
    """Return {(problem, model, name) -> row}."""
    out = {}
    if not path.exists():
        return out
    with open(path) as f:
        for r in csv.DictReader(f):
            out[(r["problem"], r["model"], r["name"])] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path)
    args = ap.parse_args()

    # Discover year shards
    years: set[str] = set()
    for d in args.results_dir.iterdir():
        if d.is_dir() and "-" in d.name:
            mode, _, year = d.name.partition("-")
            if mode in ("standalone", "parasol") and year.isdigit():
                years.add(year)

    rows_out: list[dict] = []
    deltas_by_year: dict[str, list[float]] = defaultdict(list)
    deltas_overall: list[float] = []
    pairs_by_year: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for year in sorted(years):
        s_rows = load(args.results_dir / f"standalone-{year}" / "results.csv")
        p_rows = load(args.results_dir / f"parasol-{year}" / "results.csv")

        for key in sorted(set(s_rows) & set(p_rows)):
            s, p = s_rows[key], p_rows[key]
            try:
                s_t = float(s["time_ms"])
                p_t = float(p["time_ms"])
            except (KeyError, ValueError):
                continue
            row = {
                "year": year,
                "problem": key[0], "model": key[1], "name": key[2],
                "standalone_ms": s_t,
                "parasol_ms": p_t,
                "delta_ms": p_t - s_t,
                "standalone_status": s.get("status", ""),
                "parasol_status": p.get("optimal", p.get("status", "")),
                "standalone_obj": s.get("objective", ""),
                "parasol_obj": p.get("objective", ""),
            }
            rows_out.append(row)
            deltas_by_year[year].append(p_t - s_t)
            deltas_overall.append(p_t - s_t)
            pairs_by_year[year].append((s_t, p_t))

    if not rows_out:
        print(f"no matched instances under {args.results_dir}")
        return

    # Write merged.csv
    merged_path = args.results_dir / "merged.csv"
    with open(merged_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {merged_path}  ({len(rows_out)} matched instances)\n")

    def stats(name: str, ds: list[float]) -> None:
        if not ds:
            print(f"  {name}: empty")
            return
        ds = sorted(ds)
        n = len(ds)
        mean = sum(ds) / n
        median = ds[n // 2]
        std = statistics.stdev(ds) if n > 1 else 0.0
        p10 = ds[int(n * 0.10)]
        p90 = ds[int(n * 0.90)]
        n_neg = sum(1 for d in ds if d < -50)
        n_pos_small = sum(1 for d in ds if -50 <= d <= 200)
        n_pos = sum(1 for d in ds if d > 200)
        print(f"  {name:<10}  n={n:>4}   "
              f"mean={mean:>+8.0f}ms  median={median:>+7.0f}ms  std={std:>7.0f}ms  "
              f"p10={p10:>+7.0f}ms  p90={p90:>+8.0f}ms")
        print(f"             |  faster (-50ms<): {n_neg:>3}   "
              f"~equal (-50..200ms): {n_pos_small:>3}   "
              f"slower (>200ms): {n_pos:>3}")

    print(f"=== Overall delta (parasol - standalone), ms ===")
    stats("overall", deltas_overall)
    print()

    print(f"=== Per-year delta ===")
    for year in sorted(deltas_by_year):
        stats(year, deltas_by_year[year])
    print()

    # Constant vs multiplicative diagnostic.
    # If overhead is constant K, then delta should be ~K regardless of standalone time.
    # If overhead is multiplicative (delta = (k-1) * standalone), delta grows with x.
    # Restrict to cases where both finished cleanly (well under timeout).
    print(f"=== Constant vs multiplicative diagnostic (instances < 0.8 * timeout in both modes) ===")
    all_pairs = [pp for ps in pairs_by_year.values() for pp in ps]
    timeout_floor = max((max(s, p) for s, p in all_pairs), default=20000)
    safe_threshold = timeout_floor * 0.8
    sb = [(s, p) for ps in pairs_by_year.values() for s, p in ps
          if s < safe_threshold and p < safe_threshold]
    if len(sb) >= 10:
        deltas = [p - s for s, p in sb]
        print(f"  n cleanly-finished pairs: {len(sb)}")
        print(f"  median delta (good estimate of constant overhead): {statistics.median(deltas):.0f} ms")
        print(f"  mean delta:                                          {statistics.mean(deltas):.0f} ms")
        # Bin by standalone time (log buckets)
        print()
        print(f"  delta grouped by standalone time (constant overhead → flat across rows):")
        print(f"    {'standalone bucket':<22} {'n':>4} {'median Δ':>10} {'mean Δ':>10} {'as % of std':>13}")
        bounds = [(0, 100), (100, 500), (500, 2_000), (2_000, 10_000), (10_000, 60_000)]
        for lo, hi in bounds:
            sub = [(s, p) for s, p in sb if lo <= s < hi]
            if not sub:
                continue
            ds = [p - s for s, p in sub]
            ss = [s for s, _ in sub]
            mp = statistics.median(ds) / max(statistics.median(ss), 1e-9)
            print(f"    [{lo:>5}, {hi:>5})ms       {len(sub):>4}  "
                  f"{statistics.median(ds):>+9.0f}  {statistics.mean(ds):>+9.0f}  "
                  f"{mp:>+12.1%}")
    else:
        print(f"  not enough data ({len(sb)} pairs)")


if __name__ == "__main__":
    main()
