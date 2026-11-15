#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/showcase/main.go" -root "$root" -container -parallel 2
"$root/validate.sh"
