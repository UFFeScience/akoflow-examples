#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null
command -v docker >/dev/null
go -C "$root/../.." mod download
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
