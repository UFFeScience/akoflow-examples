#!/bin/sh
set -eu
if [ "${1:-}" = "-definition" ]; then
 docker run --rm --network none ghcr.io/uffescience/openoil-ensemble@sha256:9939dcaa4c26b62ce5496f46f3946d26f0ad1168fbfe1c5acd13b3385fd25b6e python -c 'from opendrift.models.openoil import OpenOil; from roaring_landmask import RoaringLandmask; print("OpenOil and coastline dependencies available")'
else
 docker run --rm --network none -v "$PWD/outputs:/work" ghcr.io/uffescience/openoil-ensemble@sha256:9939dcaa4c26b62ce5496f46f3946d26f0ad1168fbfe1c5acd13b3385fd25b6e python /opt/openoil/workflow.py --stage validate
fi
