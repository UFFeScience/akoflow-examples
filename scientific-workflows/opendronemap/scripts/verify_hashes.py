import hashlib
import json
from pathlib import Path
import sys

output = Path(sys.argv[1])
report = json.loads((output / 'validation.json').read_text())
if report['status'] != 'success':
    raise SystemExit('Native validation was not successful')
for name, expected in report['sha256'].items():
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit('Invalid artifact path in native report')
    actual = hashlib.sha256((output / relative).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('Artifact differs from its native execution: ' + name)
print('All six scientific and visual products match native SHA-256 digests')
