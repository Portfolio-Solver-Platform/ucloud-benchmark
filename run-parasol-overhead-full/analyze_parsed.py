#!/usr/bin/env python3
"""Parse internal solver time from .out files and compare to wall-clock.

Goal: confirm that the wall-clock overhead we measure for parasol is mostly
post-solve shutdown time. We extract the LAST internal-time marker from each
mode's .out file:

  standalone  (JSON stream):  max "time": <ms> across all events
  parasol     (text):         last `% time elapsed: X.XXX` (seconds → ms)

If parasol's wall-vs-internal gap exceeds standalone's, the difference is the
harness shutdown overhead — i.e. the slowdown happens AFTER solving finishes.
"""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path

PARASOL_TIME_RE = re.compile(r"^% time elapsed:\s*([0-9.]+)", re.MULTILINE)


def parse_standalone_internal_ms(text: str) -> float | None:
    """Max 'time' field across all JSON events in stdout (ms)."""
    last = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = msg.get("time")
        if isinstance(t, (int, float)):
            if last is None or t > last:
                last = t
    return float(last) if last is not None else None


def parse_parasol_internal_ms(text: str) -> float | None:
    """Last `% time elapsed: X.XXX` value in seconds → ms."""
    matches = PARASOL_TIME_RE.findall(text)
    if not matches:
        return None
    return float(matches[-1]) * 1000.0


def out_filename(row: dict, schedule_or_solver: str, kind: str) -> str:
    """benchmark_solvers writes <schedule_or_solver>=solver.
    benchmark_parasol writes <schedule_or_solver>=schedule_stem (e.g. cpsat8)."""
    return (
        f"{row['problem']}-sep-{row['model']}-sep-{row['name']}"
        f"-sep-{schedule_or_solver}-sep-8-sep-0.out"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("--schedule", default="cpsat8",
                    help="parasol schedule stem in .out filenames (default: cpsat8)")
    ap.add_argument("--solver", default="cp-sat",
                    help="standalone solver name in .out filenames (default: cp-sat)")
    args = ap.parse_args()

    # Discover years
    years: set[str] = set()
    for d in args.results_dir.iterdir():
        if d.is_dir() and "-" in d.name:
            mode, _, year = d.name.partition("-")
            if mode in ("standalone", "parasol") and year.isdigit():
                years.add(year)

    rows_out: list[dict] = []

    for year in sorted(years):
        s_dir = args.results_dir / f"standalone-{year}"
        p_dir = args.results_dir / f"parasol-{year}"
        s_csv = s_dir / "results.csv"
        p_csv = p_dir / "results.csv"
        if not s_csv.exists() or not p_csv.exists():
            continue

        s_rows = {}
        with open(s_csv) as f:
            for r in csv.DictReader(f):
                s_rows[(r["problem"], r["model"], r["name"])] = r
        p_rows = {}
        with open(p_csv) as f:
            for r in csv.DictReader(f):
                p_rows[(r["problem"], r["model"], r["name"])] = r

        for key in sorted(set(s_rows) & set(p_rows)):
            s, p = s_rows[key], p_rows[key]
            try:
                s_wall = float(s["time_ms"])
                p_wall = float(p["time_ms"])
            except (KeyError, ValueError):
                continue

            s_out = s_dir / out_filename(s, args.solver, "standalone")
            p_out = p_dir / out_filename(p, args.schedule, "parasol")

            s_internal = parse_standalone_internal_ms(s_out.read_text(errors="replace")) if s_out.exists() else None
            p_internal = parse_parasol_internal_ms(p_out.read_text(errors="replace")) if p_out.exists() else None

            rows_out.append({
                "year": year,
                "problem": key[0], "model": key[1], "name": key[2],
                "standalone_wall_ms": s_wall,
                "parasol_wall_ms": p_wall,
                "standalone_internal_ms": s_internal if s_internal is not None else "",
                "parasol_internal_ms": p_internal if p_internal is not None else "",
                "standalone_status": s.get("status", ""),
                "parasol_status": p.get("optimal", p.get("status", "")),
            })

    # Save merged CSV with parsed internal times
    out_csv = args.results_dir / "merged_with_internal.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {out_csv}  ({len(rows_out)} matched instances)\n")

    # Numerify for stats
    def fnum(v):
        try: return float(v)
        except: return None

    # Stats: only on cleanly-finished instances (both wall < timeout)
    # Detect timeout from data
    if rows_out:
        max_wall = max(max(r["standalone_wall_ms"], r["parasol_wall_ms"]) for r in rows_out)
        timeout_threshold = max_wall * 0.95
    else:
        timeout_threshold = 20000

    clean = [r for r in rows_out
             if r["standalone_wall_ms"] < timeout_threshold
             and r["parasol_wall_ms"] < timeout_threshold
             and fnum(r["standalone_internal_ms"]) is not None
             and fnum(r["parasol_internal_ms"]) is not None]
    print(f"clean (no-timeout, internal time available in both): {len(clean)} / {len(rows_out)}\n")

    if not clean:
        return

    wall_deltas = [r["parasol_wall_ms"] - r["standalone_wall_ms"] for r in clean]
    int_deltas = [fnum(r["parasol_internal_ms"]) - fnum(r["standalone_internal_ms"]) for r in clean]
    s_shutdown = [r["standalone_wall_ms"] - fnum(r["standalone_internal_ms"]) for r in clean]
    p_shutdown = [r["parasol_wall_ms"] - fnum(r["parasol_internal_ms"]) for r in clean]

    def show(name, ds):
        ds = sorted(ds)
        n = len(ds)
        print(f"  {name:<26}  n={n:>4}   "
              f"mean={statistics.mean(ds):>+8.0f}ms   "
              f"median={statistics.median(ds):>+8.0f}ms   "
              f"std={statistics.stdev(ds):>7.0f}ms   "
              f"p10={ds[int(n*0.10)]:>+7.0f}   p90={ds[int(n*0.90)]:>+7.0f}")

    print("=== summary (all in ms) ===")
    show("wall delta (P - S)",       wall_deltas)
    show("internal delta (P - S)",   int_deltas)
    show("standalone shutdown",      s_shutdown)
    show("parasol shutdown",         p_shutdown)
    print()

    # Bucket internal_delta by standalone_internal time (constant-cost diagnostic)
    bounds = [(0, 100), (100, 500), (500, 2_000), (2_000, 10_000), (10_000, 60_000)]
    print(f"=== internal-time delta by standalone internal time ===")
    print(f"  {'bucket':<22} {'n':>4}  {'median Δ_int':>13}  {'median Δ_wall':>14}")
    for lo, hi in bounds:
        sub = [r for r in clean if lo <= fnum(r["standalone_internal_ms"]) < hi]
        if not sub:
            continue
        di = sorted(fnum(r["parasol_internal_ms"]) - fnum(r["standalone_internal_ms"]) for r in sub)
        dw = sorted(r["parasol_wall_ms"] - r["standalone_wall_ms"] for r in sub)
        print(f"  [{lo:>5}, {hi:>5})ms       {len(sub):>4}  "
              f"{di[len(di)//2]:>+12.0f}ms  {dw[len(dw)//2]:>+13.0f}ms")


if __name__ == "__main__":
    main()
