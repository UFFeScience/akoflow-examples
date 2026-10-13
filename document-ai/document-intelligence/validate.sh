#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$root" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'outputs/manifest.json').read_text());q=json.loads((r/'outputs/report.json').read_text())
assert m['status']=='success' and q['documents']==3 and q['invoices']==2 and q['gross_total']==8262.75
assert all((r/'outputs'/x).is_file() for x in m['artifacts']);print('validated document-intelligence')
PY

