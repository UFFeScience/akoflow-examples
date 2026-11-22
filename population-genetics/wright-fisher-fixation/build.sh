#!/bin/sh
set -eu
sudo -n docker build -t akoflow/community-wright-fisher-fixation:v1 -f docker/Dockerfile .
