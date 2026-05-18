#!/bin/bash
set -eo pipefail
cd /work/benchmark/ucloud-benchmark/run-svc-2025/

bash ./run-svc-k1-2025-r1.sh
bash ./run-svc-ek1-2025-r1.sh
