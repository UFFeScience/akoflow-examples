from pathlib import Path
import hashlib
import json
import urllib.request

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
for location, expected, size in zip(data['fastq_ftp'].split(';'), data['fastq_md5'].split(';'), data['fastq_bytes'].split(';')):
    target = root / 'data' / Path(location).name
    if not target.exists():
        temporary = target.with_suffix('.partial')
        urllib.request.urlretrieve('https://' + location, temporary)
        temporary.replace(target)
    assert target.stat().st_size == int(size), target
    digest = hashlib.md5()
    with target.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    assert digest.hexdigest() == expected, target
record.write_text(json.dumps(records, indent=2) + '\n')
print('Verified complete SRR3403832 paired FASTQ observations against ENA byte counts and MD5 digests.')
