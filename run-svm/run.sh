#!/bin/bash
set -eo pipefail

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/svm/2023 --problems-path ../../data/mznc2023_probs --discover -- --solver parasol -p 8 --ai command-line --ai-config command="./svm.py" --output-solver --solver-config-mode cache --verbosity error --static-schedule static-portfolio.csv --static-runtime 0 2>&1 | tee svm-out.txt
