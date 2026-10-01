#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json, sys
from pathlib import Path
r=Path(sys.argv[1]); m=json.loads((r/'outputs/manifest.json').read_text())
assert m['status']=='success' and m['showcase']=='ai-video-studio'
assert all((r/'outputs'/p).stat().st_size > 0 for p in m['artifacts'])
assert (r/'outputs/final.mp4').stat().st_size > 1000
print('validated ai-video-studio')
PY

