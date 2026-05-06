#!/bin/bash
set -eo pipefail

# Token must be in env. For interactive use:
#   export UCLOUD_TOKEN='...'
#   ./run-orchestrator-test.sh
# For batch use, source a private file before this runs, e.g.:
#   . /work/.ucloud-token   # file containing: export UCLOUD_TOKEN='...' (chmod 600)
: "${UCLOUD_TOKEN:?UCLOUD_TOKEN must be set in the environment}"

# Install CA certs so urllib can verify HTTPS (UCloud containers often miss them).
apt-get update -qq
apt-get install -y -qq ca-certificates
update-ca-certificates

cd /work/benchmark/ucloud-benchmark/orchestrator
python3 -u orchestrator.py --test
