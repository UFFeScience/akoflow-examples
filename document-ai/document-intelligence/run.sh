#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); rm -rf "$root/outputs"
python3 "$root/scripts/pipeline.py" --output "$root/outputs" --stage all
"$root/validate.sh"

