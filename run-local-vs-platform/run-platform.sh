#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"

python run_platform.py 2>&1 | tee out-platform.txt
