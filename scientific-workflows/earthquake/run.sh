#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/showcase/main.go" -root "$root" -container -parallel 2
if ! "$root/validate.sh"; then
  rm -f "$root/outputs/manifest.json"
  exit 1
fi
