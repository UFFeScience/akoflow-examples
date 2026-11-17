import argparse
import json
from pathlib import Path

from PIL import Image

from run_validation import check_archive

parser = argparse.ArgumentParser()
parser.add_argument('--definition', action='store_true')
args = parser.parse_args()
if args.definition:
    from acquisition import digest
    from rpy2.robjects.packages import importr
    import scipy.stats

    app = Path('/app')
    provenance = json.loads((app / 'data/provenance.json').read_text())
    contract = json.loads((app / 'data/input.json').read_text())
    source_manifest = json.loads((app / 'upstream/source-manifest.json').read_text())
    for name, expected in source_manifest['files'].items():
        assert digest(app / 'upstream' / name) == expected
    assert (app / 'requirements.txt').read_bytes() == (app / 'upstream/requirements.txt').read_bytes()
    notebooks = sorted((app / 'upstream/notebooks').glob('*.ipynb'))
    assert len(notebooks) == len(contract['stages']) == 6
    assert provenance['referenceOutputsUsedAsInputs'] is False
    for record in provenance['seedFiles']:
        seed = app / 'data/seeds' / record['filename']
        assert seed.stat().st_size == record['bytes']
        assert digest(seed) == record['sha256']
    for notebook in notebooks:
        for index, cell in enumerate(json.loads(notebook.read_text())['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), str(notebook) + ':' + str(index), 'exec')
    for script in (app / 'scripts').glob('*.py'):
        compile(script.read_text(), str(script), 'exec')
    importr('edgeR')
    assert callable(scipy.stats.false_discovery_control)
    print('Validated six notebook sources, frozen input hashes and Python/R dependencies; scientific execution is separate.')
    raise SystemExit

output = Path('/outputs')
report = json.loads((output / 'scientific-validation.json').read_text())
assert report['status'] == 'passed' and len(report['groups']) == 5
assert report['referenceOutputsUsedAsInputs'] is False
assert report['gdcFileCount'] > 0 and report['mirwalkFileCount'] > 0
with Image.open(output / 'network-summary.png') as image:
    image.verify()
check_archive(output / 'stage-06.tar.gz', report)
print('Validated five newly computed network groups, complete acquisition receipts and retained stage records.')
