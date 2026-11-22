#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dir=${WELL_INPUT_SOURCE:-/home/ovvesley/Workspace/.cache/the-well-radiative/test}
destination=$root/inputs
mkdir -p "$destination"

verify_copy() {
  value=$1
  expected=$2
  name=turbulent_radiative_layer_tcool_${value}.hdf5
  source=$source_dir/$name
  test -f "$source" || { echo "Missing pinned input: $source" >&2; exit 2; }
  actual=$(sha256sum "$source" | cut -d ' ' -f 1)
  test "$actual" = "$expected" || { echo "Checksum mismatch: $name" >&2; exit 3; }
  cp "$source" "$destination/$name"
}

verify_copy 0.03 7cfc3b5be027792100b20cc4c1ab2f2835f983b00f6f86c3833bb52484c5a68e
verify_copy 0.06 7274a1ee2daf404e392cafac0a7de08668a834d78c5af48ed1c3eb844822be99
verify_copy 0.10 4a8d39a19bea829b01de8c25a78fa7d089de82f14c676fca3a94365e6e994ebe
verify_copy 0.18 30a0218124429556c889dfbb94b3f20acee1946d35d74c7ed5179b717f57dc21
verify_copy 0.32 06cbd36c1dbea84e70906a363d20143b228765ee37850ec65351e247cf7df747
verify_copy 0.56 d69d6f41c950d69e2a21688c65e303fd5cd415c37ec686df055db7da73a838fe
verify_copy 1.00 97f5d10132c6f4b100d1c77d94e91fa2acdc4954cc359733087b9ae5fc983838
verify_copy 1.78 f53524c481e095be20d607dd3f9a2738dd1a2dd8c0a675c0794f000822c79c2b
verify_copy 3.16 02a7d46a9ac1f36a479d32396a07818e26832015d083dee63845d64b92b39cf3
sha256sum "$destination"/*.hdf5 > "$destination/SHA256SUMS"
echo "Prepared nine pinned test inputs in $destination"
