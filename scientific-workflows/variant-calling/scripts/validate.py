from pathlib import Path
import json
import hashlib
import tarfile
import tempfile
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path('/app')

def run(command):
    return subprocess.check_output(command, universal_newlines=True)

if '--definition' in sys.argv:
    config = json.loads((root / 'data/input.json').read_text())
    workflow = json.loads((root / 'workflow.json').read_text())
    names = [a['name'] for a in workflow['spec']['activities']]
    assert len(names) == 14 and set(names) == set(config['stages'])
    assert workflow['spec']['image'] == 'ghcr.io/uffescience/akoflow-examples/variant-calling:v1'
    bwa = subprocess.run(['bwa'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout
    assert '0.7.17-r1188' in bwa
    assert run(['samtools', '--version']).startswith('samtools 1.15.1')
    assert run(['bcftools', '--version']).startswith('bcftools 1.15.1')
    expected = json.loads((root / 'data/input-verification.json').read_text())
    assert hashlib.sha256((root / 'data/reference.fasta').read_bytes()).hexdigest() == expected['referenceSHA256']
    assert (root / 'scripts/upstream/LICENSE').is_file()
    print('Validated the pinned original toolchain, reference, complete 14-activity definition and upstream license. Scientific execution is validated separately by the real daemon run.')
    raise SystemExit(0)

out = Path('/outputs')
report = json.loads((out / 'variant-summary.json').read_text())
assert report['status'] == 'success' and len(report['samples']) == 2
assert {r['sample'] for r in report['samples']} == {'SRR2584866', 'SRR2589044'}
assert ET.parse(str(out / 'variant-summary.svg')).getroot().tag == '{http://www.w3.org/2000/svg}svg'
sequence = ''.join(line.strip() for line in (root / 'data/reference.fasta').read_text().splitlines() if not line.startswith('>'))
with tempfile.TemporaryDirectory() as temporary:
    temporary = Path(temporary)
    with tarfile.open(str(out / 'variant-results.tar.gz')) as archive:
        expected = {'results/' + name for name in report['sha256']} | {'results/variant-summary.json', 'results/variant-positions.tsv', 'results/variant-summary.svg'}
        assert {m.name for m in archive.getmembers()} == expected
        for m in archive.getmembers():
            assert m.isfile() and m.name.startswith('results/') and '..' not in m.name
            name = Path(m.name).name
            h = hashlib.sha256()
            with archive.extractfile(m) as source, (temporary / name).open('wb') as target:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    h.update(block)
                    target.write(block)
            if name in report['sha256']:
                assert h.hexdigest() == report['sha256'][name], name
    assert (temporary / 'variant-summary.json').read_bytes() == (out / 'variant-summary.json').read_bytes()
    for r in report['samples']:
        assert r['readPairs'] > 0 and r['primaryMates'] == 2 * r['readPairs'] and r['mappedRecords'] > 0 and r['pileupSites'] > 0
        sample = r['sample']
        subprocess.check_call(['samtools', 'quickcheck', '-v', str(temporary / (sample + '.aligned.sorted.bam'))])
        subprocess.check_call(['samtools', 'idxstats', str(temporary / (sample + '.aligned.sorted.bam'))], stdout=subprocess.DEVNULL)
        text = run(['bcftools', 'view', '-H', str(temporary / (sample + '.final.vcf'))])
        rows = [line.split('\t') for line in text.splitlines() if line]
        assert len(rows) == r['filteredVariantCount']
        for row in rows:
            position = int(row[1])
            assert sequence[position - 1:position - 1 + len(row[3])] == row[3], (sample, position, row[3])
        assert sum(r['types'].values()) == len(rows)
print('Validated full-sample processing, positive mapped coverage, actual VCF records/reference alleles, BAM/BAI integrity, archive hashes and the scientific SVG.')
