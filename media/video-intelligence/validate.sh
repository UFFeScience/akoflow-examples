#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'outputs/manifest.json').read_text());t=json.loads((r/'outputs/timeline.json').read_text());p=json.loads((r/'outputs/probe.json').read_text())
assert m['status']=='success' and 5.5<float(p['format']['duration'])<6.5 and len(t['scenes'])>=3
assert all((r/'outputs'/x).stat().st_size>0 for x in m['artifacts']);print('validated video-intelligence')
PY

