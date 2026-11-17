import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
plt.rcParams.update({'figure.dpi': 150, 'axes.spines.top': False, 'axes.spines.right': False})

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def inputs():
    receipt = json.loads((DATA / 'acquisition.json').read_text())
    for item in receipt['files']:
        p = DATA / 'inputs' / item['path']
        if digest(p) != item['sha256']:
            raise RuntimeError('Input checksum mismatch: ' + str(p))
    return receipt

def finish(output, artifacts, findings):
    provenance = json.loads((DATA / 'provenance.json').read_text())
    write(output / 'scientific-validation.json', {'status': 'passed', 'findings': findings, 'provenance': provenance, 'acquisition': inputs()})
    artifacts = artifacts + ['scientific-validation.json']
    for name in artifacts:
        if not (output / name).is_file() or (output / name).stat().st_size == 0:
            raise RuntimeError('Missing artifact: ' + name)
    write(output / 'manifest.json', {'showcase': provenance['slug'], 'status': 'success', 'artifacts': artifacts, 'sha256': {n: digest(output / n) for n in artifacts}})

def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--output', required=True)
    a = parser.parse_args()
    out = Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return a.stage, out
