import re
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument('--stage', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
def run(command):
    return subprocess.run(command, cwd=output, check=True, text=True, capture_output=True)
if args.stage == 'index':
    shutil.copyfile(root / 'data/reference.fna', output / 'reference.fna')
    result = run(['bowtie2-build', 'reference.fna', 'reference'])
elif args.stage == 'extract-reads':
    for name in ['SRR3403832_1.fastq', 'SRR3403832_2.fastq']:
        with gzip.open(root / 'data' / (name + '.gz'), 'rb') as source, (output / name).open('wb') as destination:
            shutil.copyfileobj(source, destination)
    result = None
elif args.stage == 'align':
    with (output / 'alignment.sam').open('wb') as destination:
        aligned = subprocess.run(['bowtie2', '-p', '1', '-q', '-x', 'reference', '-1', 'SRR3403832_1.fastq', '-2', 'SRR3403832_2.fastq'], cwd=output, stdout=destination, stderr=subprocess.PIPE, check=True)
    log = aligned.stderr.decode()
    print(log)
    observed = re.search(r'^(\d+) reads;', log, re.MULTILINE)
    assert observed and int(observed.group(1)) > 0, 'Bowtie2 did not report processing any paired observations'
    (output / 'alignment-summary.json').write_text(json.dumps({'processedReadPairs': int(observed.group(1)), 'tool': 'Bowtie2', 'accession': 'SRR3403832'}) + '\n')
    run(['samtools', 'sort', '-@', '1', '-O', 'BAM', '-o', 'SRR3403832.bam', 'alignment.sam'])
    run(['samtools', 'index', 'SRR3403832.bam'])
    (output / 'alignment.sam').unlink()
    (output / 'flagstat.json').write_text(run(['samtools', 'flagstat', '-O', 'json', 'SRR3403832.bam']).stdout)
    (output / 'idxstats.tsv').write_text(run(['samtools', 'idxstats', 'SRR3403832.bam']).stdout)
    result = None
elif args.stage == 'package':
    run(['samtools', 'quickcheck', '-v', 'SRR3403832.bam'])
    stats = json.loads((output / 'flagstat.json').read_text())['QC-passed reads']
    summary = json.loads((output / 'alignment-summary.json').read_text())
    assert stats['total'] == 2 * summary['processedReadPairs'] > 0, (stats, summary)
    assert 0 <= stats['mapped'] <= stats['total'], stats
    files = ['SRR3403832.bam', 'SRR3403832.bam.bai', 'flagstat.json', 'idxstats.tsv', 'alignment-summary.json']
    with tarfile.open(output / 'results.tar.gz', 'w:gz') as archive:
        for name in files:
            archive.add(output / name, arcname='results/' + name)
    report = {'status': 'success', 'accession': 'SRR3403832', 'reference': 'crAssphage', 'alignment': stats, 'processedReadPairs': summary['processedReadPairs'], 'finding': 'reference_matches' if stats['mapped'] else 'no_reference_matches_under_declared_settings', 'sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in files}}
    (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    result = None
elif args.stage == 'visualize':
    report = json.loads((output / 'validation.json').read_text())
    total = report['alignment']['total']
    mapped = report['alignment']['mapped']
    rows = [('Processed mates', total), ('Mapped mates', mapped), ('Unmapped mates', total - mapped)]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430" role="img" aria-labelledby="title desc">', '<title id="title">SRA Search: SRR3403832 mapping results</title>', '<desc id="desc">Measured Bowtie2 alignment against the upstream crAssphage reference. Zero matches is a valid search result.</desc>', '<rect width="1000" height="430" fill="white"/>', '<g font-family="sans-serif" fill="#151515">', '<text x="40" y="48" font-size="25" font-weight="bold">SRA Search · SRR3403832</text>', '<text x="40" y="82" font-size="16">Full public human gut metagenome · Bowtie2 / crAssphage reference</text>']
    for index, (label, count) in enumerate(rows):
        y = 135 + index * 70
        width = 530 * count / total
        parts.extend([f'<text x="40" y="{y + 23}" font-size="17">{label}</text>', f'<rect x="235" y="{y}" width="530" height="32" fill="#eeeeee"/>', f'<rect x="235" y="{y}" width="{width:.3f}" height="32" fill="#333333"/>', f'<text x="790" y="{y + 23}" font-size="17">{count:,}</text>'])
    finding = 'No reference matches under these settings' if mapped == 0 else 'Reference matches detected under these settings'
    parts.extend([f'<text x="40" y="375" font-size="18" font-weight="bold">{finding}</text>', '<text x="40" y="405" font-size="14">Observed alignment output; no simulated counts or substituted reads.</text>', '</g></svg>'])
    (output / 'mapping-summary.svg').write_text(''.join(parts))
    shutil.copyfile(output / 'results.tar.gz', output / 'published-results.tar.gz')
    shutil.copyfile(output / 'validation.json', output / 'published-validation.json')
    result = None
else:
    raise SystemExit('Unknown SRA stage')
if result is not None:
    print(result.stdout)
    print(result.stderr)
(output / ('stage-' + args.stage + '.json')).write_text(json.dumps({'stage': args.stage, 'status': 'success', 'observedAt': datetime.now(timezone.utc).isoformat()}) + '\n')
