import hashlib
import json
from pathlib import Path
import urllib.request
import time

root = Path(__file__).resolve().parents[1]
data = root / 'data'
config = json.loads((data / 'sources.json').read_text())
previous = {}
if (data / 'acquisition.json').exists():
    previous = {f['path']: f for f in json.loads((data / 'acquisition.json').read_text())['files']}
receipts = []
for item in config['files']:
    target = data / 'inputs' / item['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    old = previous.get(item['path'], {})
    pinned = item.get('sha256') or (old.get('sha256') if old.get('url') == item['url'] else None)
    if target.exists() and old.get('url') == item['url']:
        expected = item.get('sha256', old.get('sha256'))
        observed = hashlib.sha256(target.read_bytes()).hexdigest()
        if expected == observed:
            receipts.append(dict(item, sha256=observed, bytes=target.stat().st_size))
            continue
    temp = target.with_suffix(target.suffix + '.partial')
    for attempt in range(4):
        try:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'Akoflow-scientific-reproduction/1.0'})
            with urllib.request.urlopen(request, timeout=120) as src, temp.open('wb') as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            observed = hashlib.sha256(temp.read_bytes()).hexdigest()
            if pinned and pinned != observed:
                raise RuntimeError('Pinned SHA256 mismatch: ' + item['path'])
            if item.get('md5') and hashlib.md5(temp.read_bytes()).hexdigest() != item['md5']:
                raise RuntimeError('Vendor MD5 mismatch: ' + item['path'])
            if item.get('bytes') and temp.stat().st_size != item['bytes']:
                raise RuntimeError('Length mismatch: ' + item['path'])
            temp.replace(target)
            break
        except Exception:
            temp.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    receipts.append(dict(item, sha256=observed, bytes=target.stat().st_size))
    print('Verified', item['path'], target.stat().st_size, flush=True)
(data / 'acquisition.json').write_text(json.dumps({'files': receipts}, indent=2) + '\n')
