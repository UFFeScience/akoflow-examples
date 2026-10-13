#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'outputs/manifest.json').read_text());q=json.loads((r/'outputs/render-report.json').read_text())
assert m['status']=='success' and q['rendered_frames']==q['expected_frames'] and q['workers']==2
assert all((r/'outputs'/x).stat().st_size>0 for x in m['artifacts']);print('validated blender-render-farm')
PY

