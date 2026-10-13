#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd);rm -rf "$root/outputs"
python3 "$root/scripts/pipeline.py" --stage all --output "$root/outputs";"$root/validate.sh"

