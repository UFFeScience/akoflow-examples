from pathlib import Path
import hashlib
import http.client
import json
import shutil
import time
import urllib.request


def verified(path, expected, size):
    if not path.exists() or path.stat().st_size != size:
        return False
    digest = hashlib.md5()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest() == expected


def download(url, target, expected, size, attempts=5, timeout=60):
    if verified(target, expected, size):
        return
    temporary = target.with_suffix('.partial')
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                with temporary.open('wb') as stream:
                    shutil.copyfileobj(response, stream)
            if not verified(temporary, expected, size):
                raise ValueError(f'Input byte count or MD5 mismatch: {target.name}')
            temporary.replace(target)
            return
        except (OSError, http.client.HTTPException, ValueError) as error:
            temporary.unlink(missing_ok=True)
            if attempt + 1 == attempts:
                raise
            delay = 2 ** (attempt + 1)
            print(f'{target.name}: download attempt {attempt + 1} failed ({error}); retrying in {delay}s', flush=True)
            time.sleep(delay)


def main():
    root = Path(__file__).resolve().parents[1]
    query = 'https://www.ebi.ac.uk/ena/portal/api/filereport?accession=SRR3403832&result=read_run&fields=run_accession,fastq_ftp,fastq_md5,fastq_bytes,read_count,base_count&format=json'
    record = root / 'data/read-provenance.json'
    if record.exists():
        records = json.loads(record.read_text())
    else:
        with urllib.request.urlopen(query, timeout=60) as response:
            records = json.load(response)
    assert len(records) == 1 and records[0]['run_accession'] == 'SRR3403832'
    data = records[0]
    for location, expected, size in zip(data['fastq_ftp'].split(';'), data['fastq_md5'].split(';'), data['fastq_bytes'].split(';'), strict=True):
        target = root / 'data' / Path(location).name
        download('https://' + location, target, expected, int(size))
    record.write_text(json.dumps(records, indent=2) + '\n')
    print('Verified complete SRR3403832 paired FASTQ observations against ENA byte counts and MD5 digests.')


if __name__ == '__main__':
    main()
