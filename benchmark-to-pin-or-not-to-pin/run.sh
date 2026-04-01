#!/bin/bash
set -eo pipefail

{
python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/pin-or-not/choco-cpsat-pin --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai none --output-solver --solver-config-mode cache --verbosity error --pin-solvers org.choco.choco --static-schedule choco-cpsat.csv --static-runtime 0

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/pin-or-not/choco-cpsat-not-pin --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai none --output-solver --solver-config-mode cache --verbosity error --static-schedule choco-cpsat.csv --static-runtime 0

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/pin-or-not/choco-highs-pin --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai none --output-solver --solver-config-mode cache --verbosity error --pin-solvers org.choco.choco --static-schedule choco-highs.csv --static-runtime 0

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/pin-or-not/choco-highs-not-pin --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai none --output-solver --solver-config-mode cache --verbosity error --static-schedule choco-highs.csv --static-runtime 0
} 2>&1 | tee pin-or-not-out.txt
