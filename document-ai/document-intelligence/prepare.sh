#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null
command -v python3 >/dev/null
go -C "$root/../.." mod download
printf 'Local prerequisites are ready. Run ./run.sh.\n'
