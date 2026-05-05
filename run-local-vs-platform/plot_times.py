#!/usr/bin/env python3
"""Generate a Typst/Lilaq grouped bar plot comparing local vs platform
cp-sat 8-core solve times across 4 instances (3 repetitions each).

Reads:
  - ../../results/local-vs-platform/results.csv   (docker local run)
  - ../../results/platform-local-vs-platform/results.csv   (psp platform run)

Writes:
  - plot_times.typ   (grouped bar chart with min/max error bars)
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
LOCAL_CSV = HERE / "local-vs-platform" / "results.csv"
PLATFORM_CSV = HERE / "platform_raw.csv"
OUTPUT_FILE = HERE / "plot_times.typ"

SKIP_PROBLEMS = {"atsp"}  # solve time is too variable to compare meaningfully
ORDER = ["EchoSched", "fbd1", "hitori", "ihtc-2024-kletzander"]
LABEL_FOR = {"ihtc-2024-kletzander": "ihtc"}
FULL_INSTANCE = {
    "EchoSched": "EchoSched/14-10-0-2_3",
    "fbd1": "fbd1/FBDk07",
    "hitori": "hitori/h14-1",
    "ihtc-2024-kletzander": "ihtc-2024-kletzander/test03",
}


def load(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        sys.exit(f"Missing {path}")
    d: dict[str, list[float]] = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["problem"] in SKIP_PROBLEMS:
                continue
            d[row["problem"]].append(int(row["time_ms"]) / 1000.0)
    return d


def summarize(values: list[float]) -> tuple[float, float]:
    """Return (mean, symmetric half-range) so error bars reach both min and max."""
    m = mean(values)
    return m, max(m - min(values), max(values) - m)


def tup(xs, fmt=".1f") -> str:
    return "(" + ", ".join(f"{x:{fmt}}" for x in xs) + ")"


def main():
    local = load(LOCAL_CSV)
    platform = load(PLATFORM_CSV)

    present = [p for p in ORDER if p in local and p in platform]
    if not present:
        sys.exit("No shared problems between local and platform CSVs.")

    labels = [LABEL_FOR.get(p, p) for p in present]
    local_means, local_errs = zip(*(summarize(local[p]) for p in present))
    plat_means, plat_errs = zip(*(summarize(platform[p]) for p in present))

    print("Summary (seconds, mean ± half-range covering min/max):")
    for p, lm, le, pm, pe in zip(present, local_means, local_errs, plat_means, plat_errs):
        print(f"  {p:<25s}  local: {lm:6.1f} ± {le:5.1f}   platform: {pm:6.1f} ± {pe:5.1f}")

    labels_typ = "(" + ", ".join(f'"{l}"' for l in labels) + ")"
    instance_lines = "; ".join(
        f"{LABEL_FOR.get(p, p)} = {FULL_INSTANCE[p]}" for p in present
    )

    typst = f"""\
#import "@preview/lilaq:0.6.0" as lq

#set page(width: auto, height: auto, margin: 1em)

#let labels = {labels_typ}
#let local-times = {tup(local_means)}
#let local-errs  = {tup(local_errs)}
#let platform-times = {tup(plat_means)}
#let platform-errs  = {tup(plat_errs)}

#figure(
  lq.diagram(
    width: 10cm,
    height: 6cm,
    title: [Solve Time: Local vs.\\ Platform (cp-sat, 8 cores, 3 reps)],
    ylabel: [Solve time (s)],
    xlabel: [Problem],
    legend: (position: (100% + .5em, 0%)),
    xaxis: (
      ticks: labels.enumerate(),
      subticks: none,
    ),

    lq.bar(
      range(labels.len()), local-times,
      offset: -0.2, width: 0.4,
      fill: blue.lighten(30%),
      label: [local],
    ),
    lq.bar(
      range(labels.len()), platform-times,
      offset: 0.2, width: 0.4,
      fill: orange.lighten(30%),
      label: [platform],
    ),
    lq.plot(
      range(labels.len()).map(x => x - 0.2), local-times,
      yerr: local-errs,
      color: black, stroke: none,
    ),
    lq.plot(
      range(labels.len()).map(x => x + 0.2), platform-times,
      yerr: platform-errs,
      color: black, stroke: none,
    ),
  ),
  caption: [
    Mean solve time (cp-sat, 8 cores, 3 repetitions) for the same instances run
    locally in Docker versus on the PSP platform. Error bars span min/max across
    the three repetitions. Instances: {instance_lines}.
  ],
)
"""
    OUTPUT_FILE.write_text(typst)
    print(f"\nWrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
