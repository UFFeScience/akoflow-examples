#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json, sys
from pathlib import Path
r=Path(sys.argv[1]); m=json.loads((r/'outputs/manifest.json').read_text())
assert m['status']=='success' and m['showcase']=='ai-video-studio'
assert all((r/'outputs'/p).stat().st_size > 0 for p in m['artifacts'])
assert any((r/'outputs'/name).stat().st_size > 1000 for name in ('final.mp4','final.y4m') if (r/'outputs'/name).exists())
print('validated ai-video-studio')
PY
