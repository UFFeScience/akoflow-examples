#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
"$root/prepare-inputs.sh"
sudo -n docker build -t akoflow/community-weatherbench2-score-audit:v1 -f "$root/docker/Dockerfile" "$root"
