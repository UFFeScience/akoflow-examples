#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rm -rf "$root/outputs"
mkdir -p "$root/outputs"
python3 "$root/scripts/run_showcase.py" --output "$root/outputs"
"$root/validate.sh"
