#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
grep -qx 'akoflow-local-to-gcp' "$root/outputs/handoff.txt"
grep -qx 'cloud consumed: akoflow-local-to-gcp' "$root/outputs/receipt.txt"
test -s "$root/outputs/stage-produce.json"
test -s "$root/outputs/stage-consume.json"
printf 'Validated original transfer fixture and receipt\n'
