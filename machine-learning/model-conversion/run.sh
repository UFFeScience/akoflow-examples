#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/showcase/main.go" -root "$root"
"$root/validate.sh"
