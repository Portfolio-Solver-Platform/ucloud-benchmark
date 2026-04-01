#!/bin/bash
set -eo pipefail

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/static-vs-no-static/static --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai command-line --ai-config command="./ai.py" --output-solver --solver-config-mode cache --verbosity error --pin-solvers org.choco.choco --static-schedule static-portfolio.csv --static-runtime 0 2>&1 | tee static-out.txt
