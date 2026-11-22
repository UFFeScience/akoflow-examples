#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$root/data"
fetch() {
  object=$1 generation=$2 output=$3 expected=$4
  url="https://storage.googleapis.com/download/storage/v1/b/weatherbench2/o/$object?alt=media&generation=$generation"
  curl --fail --location --retry 4 --retry-all-errors --silent --show-error "$url" -o "$output.tmp"
  actual=$(sha256sum "$output.tmp" | cut -d' ' -f1)
  test "$actual" = "$expected"
  mv "$output.tmp" "$output"
}
fetch 'benchmark_results%2Fgraphcast_vs_era5_240x121_2020.nc' 1772526697962480 "$root/data/graphcast.nc" 2916814398a0d5701d1a0c2c86d3770a36428692b20463423807cec316629b4d
fetch 'benchmark_results%2Fhres_vs_era5_240x121_2020.nc' 1772526680943982 "$root/data/hres.nc" f90bb315a260d3360e756dd2d336dd15ea8d8f4b9a4f6f09bb15678b6caf3b8e
fetch 'datasets%2Fgraphcast%2FLICENSE' 1793858802323776 "$root/data/GRAPHCAST-LICENSE.txt" 73a954bc8bde5ee9812443f9d81c380131ebdeb1ac24a30c536c7a16d3a4014a
fetch 'datasets%2Fhres%2FLICENSE' 1691195899997295 "$root/data/HRES-LICENSE.txt" 12f706522a9d279015c1cccfd3c326b274ac044a73373024713282dd665c8410
fetch 'datasets%2Fera5%2FLICENSE' 1692728948234337 "$root/data/ERA5-LICENSE.txt" ffe05f9653f14ffd23322bf1ebecfd6dd519ba59726280b34593fcf69ccab60e
