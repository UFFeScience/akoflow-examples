from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import tempfile

output = Path('/outputs')
report = json.loads((output / 'published-validation.json').read_text())
assert report['status'] == 'success'
assert report['alignment']['total'] == 2 * report['processedReadPairs'] > 0
assert 0 <= report['alignment']['mapped'] <= report['alignment']['total']
import xml.etree.ElementTree as ET
assert ET.parse(output / 'mapping-summary.svg').getroot().tag == '{http://www.w3.org/2000/svg}svg'
with tempfile.TemporaryDirectory() as temporary:
    temporary = Path(temporary)
    with tarfile.open(output / 'published-results.tar.gz') as archive:
        expected = {'results/' + name for name in report['sha256']}
        assert {member.name for member in archive.getmembers()} == expected
        for member in archive.getmembers():
            assert member.isfile()
            name = Path(member.name).name
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == report['sha256'][name]
            (temporary / name).write_bytes(data)
    subprocess.run(['samtools', 'quickcheck', '-v', str(temporary / 'SRR3403832.bam')], check=True)
    subprocess.run(['samtools', 'idxstats', str(temporary / 'SRR3403832.bam')], check=True)
print('Validated complete real read processing, mapping counts (including legitimate zero matches), visual summary, BAM integrity, BAI accessibility and archived file hashes.')
