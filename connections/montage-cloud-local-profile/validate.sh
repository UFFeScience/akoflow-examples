#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/montage-check/main.go" -root "$root" "$@"
