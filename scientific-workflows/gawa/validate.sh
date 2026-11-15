#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/gawa-check/main.go" -root "$root" "$@"
