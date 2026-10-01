#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rm -rf "$root/outputs" "$root/screenshots"
mkdir -p "$root/outputs" "$root/screenshots"
python3 "$root/scripts/run_showcase.py" --output "$root/outputs"
node "$root/scripts/capture_screenshots.mjs"
"$root/validate.sh"
