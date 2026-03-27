python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/svm/2025 --problems-path ../../data/mznc2025_probs --discover -- --solver parasol -p 8 --ai command-line --ai-config command="./svm.py" --output-solver --solver-config-mode cache --verbosity error 

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/svm/2024 --problems-path ../../data/mznc2024_probs --discover -- --solver parasol -p 8 --ai command-line --ai-config command="./svm.py" --output-solver --solver-config-mode cache --verbosity error 

python ../benchmark_parasol.py -r 1 -t 1200 -o ../../results/svm/2023 --problems-path ../../data/mznc2023_probs --discover -- --solver parasol -p 8 --ai command-line --ai-config command="./svm.py" --output-solver --solver-config-mode cache --verbosity error 

