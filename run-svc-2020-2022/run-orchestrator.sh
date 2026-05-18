#!/bin/bash
set -eo pipefail

# Token must be in env. For interactive use:
#   export UCLOUD_TOKEN='...'
#   ./run-orchestrator-test.sh
# For batch use, source a private file before this runs, e.g.:
#   . /work/.ucloud-token   # file containing: export UCLOUD_TOKEN='...' (chmod 600)
: "${UCLOUD_TOKEN:?UCLOUD_TOKEN must be set in the environment}"

# Install CA certs so urllib can verify HTTPS (UCloud containers often miss them).


cd /work/benchmark/ucloud-benchmark/run-svc-2020-2022
python3 -u orchestrator.py
