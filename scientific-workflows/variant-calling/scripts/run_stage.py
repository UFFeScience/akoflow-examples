import argparse
from pathlib import Path
import subprocess
import shutil
import gzip
import json
import hashlib
import tarfile
import datetime
import html

parser = argparse.ArgumentParser()
parser.add_argument('--stage', required=True)
parser.add_argument('--sample')
parser.add_argument('--output', default='.')
args = parser.parse_args()
root = Path('/app')
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=True)
reference = 'reference.fasta'
samples = ['SRR2584866', 'SRR2589044']
if args.sample is not None:
    assert args.sample in samples

def run(command, destination=None):
    if destination is None:
        r = subprocess.run(command, cwd=str(out), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if r.stdout:
            print(r.stdout)
        if r.stderr:
            print(r.stderr)
        return r.stdout
    with (out / destination).open('wb') as stream:
        r = subprocess.run(command, cwd=str(out), check=True, stdout=stream, stderr=subprocess.PIPE)
    print(r.stderr.decode('utf-8', errors='replace'))

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read_vcf(path):
    rows = []
    with path.open() as stream:
        for line in stream:
            if line.startswith('#'):
                continue
            fields = line.rstrip('\n').split('\t')
            assert len(fields) >= 8, line
            ref, alleles = fields[3], fields[4].split(',')
            kind = 'SNP' if len(ref) == 1 and all(len(a) == 1 for a in alleles) else 'INDEL' if any(len(a) != len(ref) for a in alleles) else 'MNP'
            rows.append({'chromosome': fields[0], 'position': int(fields[1]), 'reference': ref, 'alternate': fields[4], 'quality': None if fields[5] == '.' else float(fields[5]), 'type': kind})
    return rows

sample = args.sample
if args.stage == 'index':
    shutil.copyfile(str(root / 'data/reference.fasta'), str(out / reference))
    run(['bwa', 'index', reference])
    run(['samtools', 'faidx', reference])
elif args.stage == 'extract':
    counts = []
    for mate in [1, 2]:
        name = sample + '_' + str(mate) + '.fastq'
        with gzip.open(str(root / 'data' / (name + '.gz')), 'rb') as source, (out / name).open('wb') as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        lines = int(run(['wc', '-l', name]).split()[0])
        assert lines > 0 and lines % 4 == 0
        counts.append(lines // 4)
    assert counts[0] == counts[1]
    record = next(r for r in json.loads((root / 'data/ena-records.json').read_text()) if r['run_accession'] == sample)
    assert counts[0] == int(record['read_count']), (sample, counts, record['read_count'])
    (out / (sample + '.read-counts.json')).write_text(json.dumps({'sample': sample, 'readPairs': counts[0], 'mates': sum(counts)}, indent=2) + '\n')
elif args.stage == 'align':
    run(['bwa', 'mem', '-t', '6', reference, sample + '_1.fastq', sample + '_2.fastq'], sample + '.aligned.sam')
elif args.stage == 'bam':
    run(['samtools', 'view', '-S', '-b', sample + '.aligned.sam'], sample + '.aligned.bam')
    run(['samtools', 'sort', '-o', sample + '.aligned.sorted.bam', sample + '.aligned.bam'])
    run(['samtools', 'index', sample + '.aligned.sorted.bam'])
    run(['samtools', 'quickcheck', '-v', sample + '.aligned.sorted.bam'])
    stats = json.loads(run(['samtools', 'flagstat', '-O', 'json', sample + '.aligned.sorted.bam']))
    counts = json.loads((out / (sample + '.read-counts.json')).read_text())
    passed = stats['QC-passed reads']
    passed['primary'] = passed.get('primary', passed['total'] - passed['secondary'] - passed['supplementary'])
    assert passed['primary'] == counts['mates'] and passed['mapped'] > 0, (sample, passed, counts)
    (out / (sample + '.flagstat.json')).write_text(json.dumps(stats, indent=2) + '\n')
elif args.stage == 'pileup':
    run(['bcftools', 'mpileup', '-O', 'b', '-o', sample + '.raw.bcf', '-f', reference, sample + '.aligned.sorted.bam'])
    stats = run(['bcftools', 'stats', sample + '.raw.bcf'])
    lines = [line.split('\t') for line in stats.splitlines() if line.startswith('SN\t')]
    sites = next(int(f[3]) for f in lines if f[2] == 'number of records:')
    assert sites > 0, sample
    (out / (sample + '.coverage.json')).write_text(json.dumps({'sample': sample, 'pileupSites': sites}, indent=2) + '\n')
elif args.stage == 'call':
    run(['bcftools', 'call', '--ploidy', '1', '-m', '-v', '-o', sample + '.variants.vcf', sample + '.raw.bcf'])
elif args.stage == 'filter':
    run(['vcfutils.pl', 'varFilter', sample + '.variants.vcf'], sample + '.final.vcf')
    (out / (sample + '.filtered-stats.txt')).write_text(run(['bcftools', 'stats', sample + '.final.vcf']))
elif args.stage == 'summary':
    length = sum(len(line.strip()) for line in (out / reference).read_text().splitlines() if not line.startswith('>'))
    results = []
    files = []
    for current in samples:
        rows = read_vcf(out / (current + '.final.vcf'))
        assert all(1 <= row['position'] <= length for row in rows)
        stats = json.loads((out / (current + '.flagstat.json')).read_text())['QC-passed reads']
        stats['primary'] = stats.get('primary', stats['total'] - stats['secondary'] - stats['supplementary'])
        counts = json.loads((out / (current + '.read-counts.json')).read_text())
        coverage = json.loads((out / (current + '.coverage.json')).read_text())
        assert coverage['pileupSites'] > 0 and stats['mapped'] > 0 and stats['primary'] == counts['mates']
        result = {'sample': current, 'readPairs': counts['readPairs'], 'primaryMates': stats['primary'], 'mappedRecords': stats['mapped'], 'pileupSites': coverage['pileupSites'], 'filteredVariantCount': len(rows), 'types': {kind: sum(row['type'] == kind for row in rows) for kind in ['SNP', 'INDEL', 'MNP']}, 'variants': rows}
        results.append(result)
        files.extend(current + suffix for suffix in ['.aligned.sorted.bam', '.aligned.sorted.bam.bai', '.final.vcf', '.variants.vcf', '.flagstat.json', '.read-counts.json', '.coverage.json', '.filtered-stats.txt'])
    report = {'status': 'success', 'reference': 'E. coli REL606', 'referenceLength': length, 'samples': results, 'toolchain': {'bwa': '0.7.17-r1188', 'samtools': '1.15.1', 'bcftools': '1.15.1', 'ploidy': 1}, 'sha256': {name: digest(out / name) for name in files}}
    (out / 'variant-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    with (out / 'variant-positions.tsv').open('w') as target:
        target.write('sample\tchromosome\tposition\treference\talternate\ttype\tquality\n')
        for r in results:
            for row in r['variants']:
                target.write('\t'.join([r['sample'], row['chromosome'], str(row['position']), row['reference'], row['alternate'], row['type'], '.' if row['quality'] is None else str(row['quality'])]) + '\n')
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="880" viewBox="0 0 1200 880" role="img" aria-labelledby="title desc">', '<title id="title">E. coli Variant Calling: observed filtered variants</title>', '<desc id="desc">Actual variant counts and genomic positions for two full public sequencing samples against the REL606 reference.</desc>', '<rect width="1200" height="880" fill="white"/>', '<g font-family="sans-serif" fill="#151515">', '<text x="45" y="47" font-size="27" font-weight="bold">Variant Calling - E. coli REL606</text>', '<text x="45" y="80" font-size="17">Full public reads; original BWA / samtools / bcftools toolchain; haploid calls</text>']
    for index, r in enumerate(results):
        top = 115 + index * 355
        svg.append('<text x="45" y="{}" font-size="23" font-weight="bold">{}: {} filtered variants</text>'.format(top + 20, html.escape(r['sample']), r['filteredVariantCount']))
        svg.append('<text x="45" y="{}" font-size="16">{:,} pairs | {:,} mapped records | {:,} pileup sites</text>'.format(top + 48, r['readPairs'], r['mappedRecords'], r['pileupSites']))
        svg.append('<text x="45" y="{}" font-size="16">SNP: {} | INDEL: {} | MNP: {}</text>'.format(top + 74, r['types']['SNP'], r['types']['INDEL'], r['types']['MNP']))
        left, baseline, width, height = 115, top + 275, 1010, 160
        points = [row for row in r['variants'] if row['quality'] is not None]
        maxq = max([1.0] + [row['quality'] for row in points])
        svg.append('<path d="M{},{} V{} H{}" fill="none" stroke="#666"/>'.format(left, baseline-height, baseline, left+width))
        for tick in range(5):
            x = left + width * tick / 4
            svg.append('<text x="{}" y="{}" text-anchor="middle" font-size="13">{:.2f}</text>'.format(x, baseline + 23, length * tick / 4 / 1000000))
        svg.append('<text x="{}" y="{}" font-size="14" text-anchor="middle">Genomic position (Mb)</text>'.format(left + width / 2, baseline + 48))
        svg.append('<text x="45" y="{}" font-size="13">QUAL</text>'.format(baseline - height / 2))
        svg.append('<text x="{}" y="{}" text-anchor="end" font-size="12">{:.0f}</text>'.format(left - 6, baseline-height+5, maxq))
        svg.append('<text x="{}" y="{}" text-anchor="end" font-size="12">0</text>'.format(left - 6, baseline,))
        for row in points:
            x = left + width * row['position'] / length
            y = baseline - height * row['quality'] / maxq
            svg.append('<circle cx="{:.2f}" cy="{:.2f}" r="3.5" fill="{}" opacity="0.7"/>'.format(x, y, '#222222' if row['type'] == 'SNP' else '#888888'))
    svg.extend(['<text x="45" y="860" font-size="13">Observed filtered VCF records. Point height is reported Phred QUAL; axes use each sample\'s observed maximum.</text>', '</g></svg>'])
    (out / 'variant-summary.svg').write_text(''.join(svg), encoding='utf-8')
    with tarfile.open(str(out / 'variant-results.tar.gz'), 'w:gz') as archive:
        for name in files + ['variant-summary.json', 'variant-positions.tsv', 'variant-summary.svg']:
            archive.add(str(out / name), arcname='results/' + name)
else:
    raise SystemExit('Unknown stage')
marker = 'stage-' + args.stage + ('-' + sample.lower() if sample else '') + '.json'
(out / marker).write_text(json.dumps({'stage': args.stage, 'sample': sample, 'status': 'success', 'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
