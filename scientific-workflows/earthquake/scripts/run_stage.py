import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--stage', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
stage = next(s for s in json.loads((root / 'data/stages.json').read_text()) if s[0] == args.stage)
name, script, artifact, source = stage
if name == 'fetch':
    catalog = root / 'data/catalog.csv'
    provenance = json.loads((root / 'data/catalog-provenance.json').read_text())
    if hashlib.sha256(catalog.read_bytes()).hexdigest() != provenance['sha256']:
        raise SystemExit('USGS catalog checksum mismatch')
    shutil.copyfile(catalog, output / artifact)
else:
    command = [sys.executable, str(root / 'scripts/upstream' / (script + '.py')), '--input', source, '--output', artifact]
    if name.endswith('-map'):
        command += ['--catalog', 'catalog.csv']
    if name == 'hazard':
        command += ['--grid-resolution', '2.0']
    subprocess.run(command, cwd=output, check=True)
path = output / artifact
if not path.is_file() or path.stat().st_size == 0:
    raise SystemExit('Missing computed artifact: ' + artifact)
if path.suffix == '.json':
    result = json.loads(path.read_text())
    if not result or 'error' in result:
        raise SystemExit('Scientific stage returned an empty or error result: ' + artifact)
