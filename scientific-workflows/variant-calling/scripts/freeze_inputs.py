from pathlib import Path
import json
import urllib.request
import hashlib
import shutil
import concurrent.futures
import time

root = Path(__file__).resolve().parents[1]
data = root / 'data'
records = json.loads((data / 'ena-records.json').read_text())
expected = json.loads((data / 'input-verification.json').read_text())
assert hashlib.sha256((data / 'reference.fasta').read_bytes()).hexdigest() == expected['referenceSHA256']

def md5(path):
    h = hashlib.md5()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def freeze(item):
    location, checksum, size = item
    size = int(size)
    assert location.startswith('ftp.sra.ebi.ac.uk/')
    path = data / Path(location).name
    assert path.name.endswith('.fastq.gz')
    if path.exists() and path.stat().st_size == size and md5(path) == checksum:
        return
    part = path.with_suffix('.partial')
    if path.exists():
        path.replace(part)
    for attempt in range(4):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset > size:
                part.unlink()
                offset = 0
            if offset < size:
                headers = {'User-Agent': 'Akoflow scientific example'}
                if offset:
                    headers['Range'] = 'bytes=' + str(offset) + '-'
                with urllib.request.urlopen(urllib.request.Request('https://' + location, headers=headers), timeout=90) as source:
                    mode = 'ab' if offset and source.status == 206 else 'wb'
                    if mode == 'ab':
                        assert source.headers.get('Content-Range', '').startswith('bytes ' + str(offset) + '-')
                    with part.open(mode) as target:
                        shutil.copyfileobj(source, target, length=1024 * 1024)
            assert part.stat().st_size == size, (path.name, part.stat().st_size, size)
            if md5(part) != checksum:
                part.unlink()
                raise ValueError('download checksum mismatch')
            part.replace(path)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))

items = [(url, checksum, size) for r in records for url, checksum, size in zip(r['fastq_ftp'].split(';'), r['fastq_md5'].split(';'), r['fastq_bytes'].split(';'))]
assert len(items) == 4
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(freeze, items))
print('Verified all four complete FASTQ observations and the original reference against frozen hashes.')
