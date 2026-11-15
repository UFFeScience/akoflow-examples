#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker build -f docker/Dockerfile -t gawa:homeserver-tiles-v1 -t gawa:local-f68f0939d5255163 .
