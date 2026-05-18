#!/usr/bin/env python3
"""Emit '<problem>|<mzn>|<dzn>' lines for every instance in a year's features pkl.

The bash runner pipes the output of this script into its job loop, so we
run EXACTLY the instances we have features for - no more, no less.
"""
from __future__ import annotations
import argparse, pickle, sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("year", type=int)
    p.add_argument("--features-dir",
                   default="/home/sofus/speciale/ai/ai-tools/data")
    p.add_argument("--instances-root",
                   default="/home/sofus/speciale/ai/data/mzn-challenge")
    return p.parse_args()


def parse_key(key: str, problem_names: list[str]) -> tuple[str, str, str] | None:
    """Match the longest problem name prefix, then split the remainder into
    (model, name). build_training_data.make_key formats keys as either
    f"{problem}_{model}_{name}" (most cases) or f"{problem}_{model}_" when
    model == name. Both branches end in an underscore boundary after problem."""
    for p in sorted(problem_names, key=len, reverse=True):  # longest match wins
        prefix = p + "_"
        if key.startswith(prefix):
            rest = key[len(prefix):]
            # rest starts with the model; same trick again.
            for m in sorted(problem_names + [p], key=len, reverse=True):
                m_prefix = m + "_"
                if rest.startswith(m_prefix):
                    return p, m, rest[len(m_prefix):]
                if rest == m:
                    return p, m, ""  # model == name case
            # Fallback: split on first '_' inside rest
            i = rest.find("_")
            if i >= 0:
                return p, rest[:i], rest[i + 1:]
            return p, rest, ""
    return None


def main() -> None:
    args = parse_args()
    pkl = Path(args.features_dir) / f"mznc{args.year}_features.pkl"
    with open(pkl, "rb") as f:
        feats = pickle.load(f)
    inst_root = Path(args.instances_root) / str(args.year)

    # Source of truth for problem names: the actual subdirectories on disk.
    problem_names = [d.name for d in inst_root.iterdir() if d.is_dir()]

    for key, vec in sorted(feats.items()):
        if vec is None:
            continue
        parsed = parse_key(key, problem_names)
        if parsed is None:
            print(f"# WARN: cannot parse key {key!r}", file=sys.stderr)
            continue
        problem, model, name = parsed

        problem_dir = inst_root / problem
        if not problem_dir.is_dir():
            print(f"# WARN: missing dir {problem_dir}", file=sys.stderr)
            continue
        mzns = sorted(problem_dir.glob("*.mzn"))
        if not mzns:
            print(f"# WARN: no .mzn in {problem_dir}", file=sys.stderr)
            continue
        mzn = mzns[0].name

        # If name was empty (model == name), the dzn is the model name + .dzn
        # or there is no dzn (model-only instance). Try a couple of patterns.
        candidates: list[Path] = []
        if name:
            candidates.append(problem_dir / f"{name}.dzn")
        else:
            candidates.append(problem_dir / f"{model}.dzn")
        dzn = next((c for c in candidates if c.is_file()), None)
        if dzn is None:
            print(f"# WARN: missing dzn for key {key!r}; tried {candidates}",
                  file=sys.stderr)
            continue
        print(f"{problem}|{mzn}|{dzn.name}")


if __name__ == "__main__":
    main()
