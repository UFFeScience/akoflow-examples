#!/bin/sh
set -eu
if [ "${1:-}" = "-definition" ]; then
 docker run --rm --network none ghcr.io/uffescience/openoil-ensemble:v1 python -c 'from opendrift.models.openoil import OpenOil; from roaring_landmask import RoaringLandmask; print("OpenOil and coastline dependencies available")'
else
 docker run --rm --network none -v "$PWD/outputs:/work" ghcr.io/uffescience/openoil-ensemble:v1 python /opt/openoil/workflow.py --stage validate
fi
