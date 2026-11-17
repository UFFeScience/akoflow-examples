import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import importlib.metadata
import subprocess
import sys
import tarfile
import time

from acquisition import digest

STAGES = ['metadata-access', 'metadata-filtering', 'expression-aggregation', 'expression-filtering', 'interaction-inference', 'network-construction']
parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=STAGES, required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
project = output / 'project'
index = STAGES.index(args.stage) + 1
started = time.time()
provenance = json.loads(Path('/app/data/provenance.json').read_text())


def unpack(path):
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise RuntimeError('Unsafe stage snapshot entry')
            destination = output / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open('wb') as stream:
                shutil.copyfileobj(source, stream)


def execute_notebook():
    notebooks = sorted(Path('/app/upstream/notebooks').glob('*.ipynb'))
    notebook = json.loads(notebooks[index - 1].read_text())
    (project / 'notebooks').mkdir(parents=True, exist_ok=True)
    environment = {'__name__': '__main__'}
    os.chdir(project / 'notebooks')
    sys.path.insert(0, str(project))
    for cell_index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] != 'code':
            continue
        if index == 5 and cell_index == 10:
            print('Acquisition cell already completed through the verified public CSV transport.', flush=True)
            continue
        code = ''.join(cell['source'])
        print('Executing upstream notebook', notebooks[index - 1].name, 'cell', cell_index, flush=True)
        exec(compile(code, str(notebooks[index - 1]) + ':cell-' + str(cell_index), 'exec'), environment)
        if index == 3 and cell_index == 5:
            from acquisition import download_gdc
            environment['gdc_api_file_download'] = download_gdc
        if index == 5 and cell_index == 9:
            from acquisition import download_all_mirwalk
            download_all_mirwalk(environment['expressed_mirs'])



if index > 1:
    unpack(output / f'stage-{index - 1:02d}.tar.gz')
else:
    (project / 'notebooks').mkdir(parents=True, exist_ok=True)
    shutil.copyfile('/app/upstream/config.py', project / 'config.py')
    shutil.copyfile('/app/upstream/source-manifest.json', project / 'scientific-source-manifest.json')
    runtime = {'python': sys.version, 'packages': {name: importlib.metadata.version(name) for name in ['pandas', 'numpy', 'scipy', 'rpy2', 'joblib']}, 'edgeR': subprocess.check_output(['Rscript', '-e', 'cat(as.character(packageVersion("edgeR")))'], text=True).strip()}
    (project / 'runtime-toolchain.json').write_text(json.dumps(runtime, indent=2) + '\n')
    raw = project / 'data/raw/tcga-brca'
    raw.mkdir(parents=True, exist_ok=True)
    for entry in provenance['seedFiles']:
        source = Path('/app/data/seeds') / entry['filename']
        if digest(source) != entry['sha256']:
            raise RuntimeError('Frozen raw metadata checksum mismatch')
        shutil.copyfile(source, raw / entry['filename'])
    (project / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Staged the four frozen raw metadata/supplementary inputs from upstream v0.1.0.', flush=True)

if index > 1:
    execute_notebook()

if index == 3:
    for parent in ['raw', 'processed']:
        for group in ['basal-like', 'her2-enriched', 'luminal-a', 'luminal-b', 'normal']:
            folder = project / 'data' / parent / 'tcga-brca' / group
            for path in folder.glob('*'):
                if path.is_file() and not path.name.startswith('aggregated-'):
                    path.unlink()

if index == 5:
    for path in (project / 'data/processed/mirwalk').glob('MIMAT*.csv'):
        path.unlink()

record = {'stage': args.stage, 'status': 'completed', 'startedAt': datetime.fromtimestamp(started, timezone.utc).isoformat(), 'finishedAt': datetime.now(timezone.utc).isoformat(), 'wallSeconds': time.time() - started, 'upstreamVersion': provenance['version']}
(project / 'stage-records').mkdir(exist_ok=True)
(project / 'stage-records' / (args.stage + '.json')).write_text(json.dumps(record, indent=2) + '\n')

if index == 6:
    from scientific_check import validate_project
    report = validate_project(project, output)
    (output / 'scientific-validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

os.chdir(output)
with tarfile.open(output / f'stage-{index:02d}.tar.gz', 'w:gz', compresslevel=1) as archive:
    for path in sorted(project.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            archive.add(path, arcname=str(path.relative_to(output)), recursive=False)
shutil.rmtree(project)
(output / ('stage-' + args.stage + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print('Completed stage', args.stage, 'in', round(time.time() - started, 3), 'seconds', flush=True)
