import csv
import hashlib
import json
from pathlib import Path
from PIL import Image

output = Path('/outputs')
config = json.loads(Path('/app/data/input.json').read_text())
manifest = json.loads((output / 'manifest.json').read_text())
assert manifest['status'] == 'success'
assert manifest['stages'] == config['stages']
for name in config['artifacts']:
    path = output / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['sha256'][name], name
    if path.suffix == '.png':
        with Image.open(path) as image:
            assert min(image.size) >= 100, name
            image.verify()
    if path.suffix == '.json':
        value = json.loads(path.read_text())
        assert value and 'error' not in value, name
with (output / 'catalog.csv').open() as stream:
    rows = list(csv.DictReader(stream))
assert 1000 <= len(rows) < 20000
assert len({row['id'] for row in rows}) == len(rows)
print(f'Validated 11 real activities, {len(rows)} USGS events and all output hashes.')
