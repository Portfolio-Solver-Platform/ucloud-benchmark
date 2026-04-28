#!/usr/bin/env python3
"""Combine medium-hard (60-1200s uCloud) replication results with the existing
short (0-20s timeout) replication data, and print stats over the combined set.

Writes <medium_dir>/merged_with_internal.csv with both wall and solver-internal
times, ready for plotting.
"""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path

PARASOL_TIME_RE = re.compile(r"^% time elapsed:\s*([0-9.]+)", re.MULTILINE)


def parse_standalone_internal_ms(text: str) -> float | None:
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
    matches = PARASOL_TIME_RE.findall(text)
    if not matches:
        return None
    return float(matches[-1]) * 1000.0


def out_filename(row: dict, schedule_or_solver: str) -> str:
    return (
        f"{row['problem']}-sep-{row['model']}-sep-{row['name']}"
        f"-sep-{schedule_or_solver}-sep-8-sep-0.out"
    )


def load_pair_set(results_dir: Path, label: str) -> list[dict]:
    """Walk standalone-{year}/ and parasol-{year}/ subdirs, pair by
    (year, problem, model, name), parse internal times, return rows."""
    rows = []
    for d in results_dir.iterdir():
        if not d.is_dir() or "-" not in d.name:
            continue
        mode, _, year = d.name.partition("-")
        if mode != "standalone" or not year.isdigit():
            continue

        s_dir = d
        p_dir = results_dir / f"parasol-{year}"
        s_csv = s_dir / "results.csv"
        p_csv = p_dir / "results.csv"
        if not p_csv.exists() or not s_csv.exists():
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

            s_out = s_dir / out_filename(s, "cp-sat")
            p_out = p_dir / out_filename(p, "cpsat8")
            s_int = parse_standalone_internal_ms(s_out.read_text(errors="replace")) if s_out.exists() else None
            p_int = parse_parasol_internal_ms(p_out.read_text(errors="replace")) if p_out.exists() else None

            rows.append({
                "source": label,
                "year": year,
                "problem": key[0], "model": key[1], "name": key[2],
                "standalone_wall_ms": s_wall,
                "parasol_wall_ms": p_wall,
                "standalone_internal_ms": s_int if s_int is not None else "",
                "parasol_internal_ms": p_int if p_int is not None else "",
                "standalone_status": s.get("status", ""),
                "parasol_status": p.get("optimal", p.get("status", "")),
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("medium_dir", type=Path, help="results dir for medium-hard run")
    ap.add_argument("short_dir", type=Path, help="results dir for short (20s) run", nargs="?")
    args = ap.parse_args()

    rows = load_pair_set(args.medium_dir, "medium")
    if args.short_dir and args.short_dir.exists():
        # Only include short instances that aren't in the medium set
        medium_keys = {(r["year"], r["problem"], r["model"], r["name"]) for r in rows}
        for r in load_pair_set(args.short_dir, "short"):
            key = (r["year"], r["problem"], r["model"], r["name"])
            if key not in medium_keys:
                rows.append(r)

    out_csv = args.medium_dir / "merged_with_internal.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv}  ({len(rows)} matched instances)")
    print(f"  from medium: {sum(1 for r in rows if r['source'] == 'medium')}")
    print(f"  from short:  {sum(1 for r in rows if r['source'] == 'short')}")


if __name__ == "__main__":
    main()
