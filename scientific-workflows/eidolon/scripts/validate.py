import json
from pathlib import Path
from common import digest
root = Path(__file__).resolve().parents[1]
out = root / 'outputs'
m = json.loads((out / 'manifest.json').read_text())
v = json.loads((out / 'scientific-validation.json').read_text())
assert m['status'] == 'success' and v['status'] == 'passed'
for name in m['artifacts']:
    assert digest(out / name) == m['sha256'][name], name
print(json.dumps(v['findings'], ensure_ascii=False))
