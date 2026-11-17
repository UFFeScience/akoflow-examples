#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description='Collect the completed native local-daemon results without rerunning any activity.')
parser.add_argument('--container', required=True, help='Name of the local AkôFlow server container')
parser.add_argument('--output', type=Path, help='Empty destination directory; defaults to this bundle outputs/')
args = parser.parse_args()
root = Path(__file__).resolve().parent
record = json.loads((root / 'evidence/daemon-run.json').read_text())
if record['status'] != 'completed' or record.get('completedActivityCount') != 9:
    raise SystemExit('Collect only a fully completed nine-activity native run')
for key in ['runId', 'workflowId']:
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', record[key]):
        raise SystemExit('Invalid native run identity')
output = (args.output or root / 'outputs').resolve()
if output.exists() and any(output.iterdir()):
    raise SystemExit('Destination is not empty; choose a new --output directory to preserve previous results')
output.mkdir(parents=True, exist_ok=True)
source = '/akoflow/workspace/runs/' + record['runId'] + '/' + record['workflowId'] + '-validate/results/.'
subprocess.run(['docker', 'cp', args.container + ':' + source, str(output)], check=True)
report = json.loads((output / 'validation.json').read_text())
if report['status'] != 'success' or min(report['workerOverlapSeconds'].values()) <= 0:
    raise SystemExit('Native validation or actual parallelism is missing')
print('Collected validated native results to ' + str(output))
