#!/bin/bash
set -euo pipefail
micromamba create -y -p /opt/nf-envs/sarek-0f94555c069e -f /app/upstream/sarek/modules/local/create_intervals_bed/environment.yml
micromamba env export -p /opt/nf-envs/sarek-0f94555c069e --explicit > /opt/nf-env-locks/sarek-0f94555c069e.txt
micromamba clean --all --yes
