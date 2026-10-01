#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'outputs/manifest.json').read_text());e=json.loads((r/'outputs/evaluation.json').read_text())
assert m['status']=='success' and e=={'questions':3,'grounded_accuracy':1.0};assert all((r/'outputs'/x).is_file() for x in m['artifacts']);print('validated local-rag-factory')
PY

