#!/bin/bash
set -eo pipefail
cd /work/benchmark/ucloud-benchmark/run-svc-2025/

python3 -m pip install --quiet -r requirements.txt

bash ./run-svc-k1-2025-r1.sh
bash ./run-svc-ek1-2025-r1.sh
