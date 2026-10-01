#!/usr/bin/env bash
set -euo pipefail

image=${CALIBRATION_IMAGE:-akoflow/montage-58-interference-calibration:050d}
output_directory=${1:-results/mdifffit-input-validation}
mkdir -p "$output_directory"
output_directory=$(cd "$output_directory" && pwd)

docker run --rm \
  --platform linux/amd64 \
  --cpus=1 \
  --memory=1536m \
  --mount "type=bind,source=$output_directory,target=/akoflow-results" \
  --workdir /akoflow-wfa-shared \
  "$image" sh -c '
    set -eu
    sha256sum -c /akoflow-calibration/projected-inputs.sha256
    started=$(date +%s%N)
    mDiffFit -d -s /akoflow-results/mdifffit.txt \
      pposs2ukstu_blue_001_001.fits \
      pposs2ukstu_blue_001_002.fits \
      /akoflow-results/mdifffit.fits \
      region-oversized.hdr
    finished=$(date +%s%N)
    test -s /akoflow-results/mdifffit.txt
    test -s /akoflow-results/mdifffit.fits
    printf "%s %s\n" "$started" "$finished" > /akoflow-results/timing-ns.txt
    sha256sum /akoflow-results/mdifffit.txt /akoflow-results/mdifffit.fits \
      > /akoflow-results/outputs.sha256
  '

echo "mDiffFit input and isolated execution validated in $output_directory"
