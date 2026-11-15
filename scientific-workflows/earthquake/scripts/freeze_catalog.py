import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
catalog = root / 'data/catalog.csv'
provenance = root / 'data/catalog-provenance.json'
if catalog.exists() and provenance.exists():
    if hashlib.sha256(catalog.read_bytes()).hexdigest() != json.loads(provenance.read_text())['sha256']:
        raise SystemExit('Frozen catalog changed; restore it or remove both catalog files to refresh')
    sys.exit(0)
parameters = ['--region', 'california', '--start-date', '2000-01-01', '--end-date', '2025-12-31', '--min-magnitude', '3.0']
subprocess.run([sys.executable, str(root / 'scripts/upstream/fetch_earthquake_data.py'), *parameters, '--output', str(catalog)], check=True)
with catalog.open() as stream:
    rows = list(csv.DictReader(stream))
if len(rows) < 1000 or len(rows) >= 20000:
    catalog.unlink()
    raise SystemExit('Insufficient or potentially truncated USGS catalog')
provenance.write_text(json.dumps({'source': 'https://earthquake.usgs.gov/fdsnws/event/1/query', 'parameters': parameters, 'retrievedAt': datetime.now(timezone.utc).isoformat(), 'events': len(rows), 'sha256': hashlib.sha256(catalog.read_bytes()).hexdigest()}, indent=2) + '\n')
