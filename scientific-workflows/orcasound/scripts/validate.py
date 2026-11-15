from pathlib import Path
import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET

root = Path('/app')
manifest = json.loads((root / 'data/input-verification.json').read_text())

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

if '--definition' in sys.argv:
    workflow = json.loads((root / 'workflow.json').read_text())
    config = json.loads((root / 'data/input.json').read_text())
    assert len(workflow['spec']['activities']) == 12
    assert len(workflow['spec']['dataDependencies']) == 28
    assert {a['name'] for a in workflow['spec']['activities']} == set(config['stages'])
    assert len(manifest['recordings']) == 12
    assert len(manifest['runtimeFiles']) == 4
    assert manifest['modelLFSObjectSHA256'] == next(r['sha256'] for r in manifest['modelFiles'] if r['filename'] == 'model.safetensors')
    for name, version in [('torch', '2.9.1'), ('torchaudio', '2.9.1'), ('torchvision', '0.24.1'), ('librosa', '0.11.0'), ('safetensors', '0.7.0')]:
        assert importlib.metadata.version(name).startswith(version)
    assert 'ffmpeg version' in subprocess.check_output(['ffmpeg', '-version'], text=True)
    assert not list(root.rglob('*.safetensors')) and not (root / 'runtime/model').exists()
    print('Validated the 12-activity DAG, pinned CPU inference stack, frozen public-input manifest and acquisition-only restricted artifacts; scientific execution is checked separately.')
    raise SystemExit(0)

import numpy as np
from PIL import Image
import soundfile as sf

output = Path('/outputs')
report = json.loads((output / 'orcasound-summary.json').read_text())
assert report['status'] == 'success' and report['recordingCount'] == len(report['samples']) == 12
assert report['strictWeightsLoaded'] and report['loadedTensorCount'] == manifest['modelTensorCount']
assert report['modelSHA256'] == manifest['modelLFSObjectSHA256']
assert report['sourceHashes'] == {r['filename']: r['sha256'] for r in manifest['runtimeFiles']}
assert {s['audio']['source'] for s in report['samples']} == {r['filename'] for r in manifest['recordings']}
assert ET.parse(output / 'orca-confidence.svg').getroot().tag == '{http://www.w3.org/2000/svg}svg'
with Image.open(output / 'hydrophone-spectrograms.png') as image:
    assert image.size == (1600, 1050) and np.asarray(image).std() > 0
with tempfile.TemporaryDirectory() as temporary:
    temporary = Path(temporary)
    with tarfile.open(output / 'orcasound-results.tar.gz') as archive:
        names = {member.name for member in archive.getmembers()}
        assert names == set(report['resultSHA256']) | {'orcasound-summary.json'}
        assert not any('private' in name or 'weights' in name or name.endswith(('.py', '.safetensors', '.pkl')) for name in names)
        for member in archive.getmembers():
            relative = Path(member.name)
            assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as destination:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    destination.write(block)
            if member.name in report['resultSHA256']:
                assert sha(target) == report['resultSHA256'][member.name]
    assert (temporary / 'orcasound-summary.json').read_bytes() == (output / 'orcasound-summary.json').read_bytes()
    for name in ['hydrophone-spectrograms.png', 'orca-confidence.svg']:
        assert sha(output / name) == report['resultSHA256'][name]
    observed_duration = 0.0
    windows = 0
    positives = 0
    files_positive = 0
    for sample in report['samples']:
        audio = sample['audio']
        inference = sample['inference']
        path = temporary / 'audio' / audio['filename']
        data, sr = sf.read(path, dtype='float32', always_2d=True)
        assert sha(path) == audio['wavSHA256']
        assert sr == audio['sampleRate'] and len(data) == audio['frames'] and data.shape[1] == audio['channels']
        assert np.isfinite(data).all() and float(np.sqrt(np.mean(data.astype('float64') ** 2))) > 0
        duration = len(data) / sr
        assert abs(duration - audio['durationSeconds']) < 1e-9
        assert abs(duration - next(r['playlistDurationSeconds'] for r in manifest['recordings'] if r['filename'] == audio['source'])) < 0.1
        observed_duration += duration
        segments = inference['segment_predictions']
        expected_count = math.floor((duration - report['windowSeconds']) / report['hopSeconds']) + 1
        assert len(segments) == expected_count == len(inference['local_predictions']) == len(inference['local_confidences'])
        confidences = []
        for index, segment in enumerate(segments):
            confidence = segment['confidence']
            assert math.isfinite(confidence) and 0 <= confidence <= 1
            assert confidence == inference['local_confidences'][index]
            assert abs(segment['start_time_s'] - index * report['hopSeconds']) < 1e-9
            assert segment['duration_s'] == report['windowSeconds']
            assert inference['local_predictions'][index] == int(confidence > report['localThreshold'])
            confidences.append(confidence)
        global_confidence = sum(sorted(confidences, reverse=True)[:2]) / min(2, len(confidences))
        assert abs(global_confidence - inference['global_confidence']) < 1e-7
        assert inference['global_prediction'] == int(global_confidence >= report['globalThreshold'])
        windows += len(segments)
        positives += sum(inference['local_predictions'])
        files_positive += inference['global_prediction']
        with Image.open(temporary / 'spectrograms' / (Path(audio['filename']).stem + '.png')) as image:
            assert image.width > 500 and image.height > 300 and np.asarray(image).std() > 0
    assert abs(observed_duration - report['decodedSeconds']) < 1e-8
    assert windows == report['inferenceWindowCount'] and positives == report['positiveCandidateWindowCount'] and files_positive == report['positiveFileCount']
print('Validated 12 complete decoded real-audio objects, strict trained-model/source fingerprints, all inference windows and aggregation, WAV/PNG/JSON/archive hashes, scientific figures and exclusion of restricted artifacts from public outputs.')
