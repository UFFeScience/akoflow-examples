import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'data/source.json').read_text())
images = root / 'data/images'
images.mkdir(parents=True, exist_ok=True)

def acquire(item):
    path = images / item['name']
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']:
        return
    request = urllib.request.Request(item['url'], headers={'User-Agent': 'Akoflow-OpenDroneMap'})
    with urllib.request.urlopen(request, timeout=120) as response:
        content = response.read()
    if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
        raise ValueError('Source photograph failed integrity check: ' + item['name'])
    temporary = path.with_suffix('.part')
    temporary.write_bytes(content)
    temporary.replace(path)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(acquire, manifest['files']))
print(f"Verified {len(manifest['files'])} original CC0 photographs at {manifest['commit']}")
