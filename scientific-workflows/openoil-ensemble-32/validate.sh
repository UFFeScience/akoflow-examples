#!/bin/sh
set -eu
if [ "${1:-}" = "-definition" ]; then
 docker run --rm --network none ghcr.io/uffescience/openoil-ensemble@sha256:267348059d11049d42458ab2e3a30cedb4efa143b619f60686d44525f1bba19a python -c 'from opendrift.models.openoil import OpenOil; from roaring_landmask import RoaringLandmask; print("OpenOil and coastline dependencies available")'
else
 docker run --rm --network none -v "$PWD/outputs:/work" ghcr.io/uffescience/openoil-ensemble@sha256:267348059d11049d42458ab2e3a30cedb4efa143b619f60686d44525f1bba19a python /opt/openoil/workflow.py --stage validate
fi
