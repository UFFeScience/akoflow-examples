import argparse
from dataclasses import asdict
import datetime
import hashlib
import importlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--stage', required=True)
parser.add_argument('--part', type=int)
parser.add_argument('--output', default='.')
args = parser.parse_args()
root = Path('/app')
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / 'data/input-verification.json').read_text())

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def save(name, data):
    (output / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')

def pack(name, files):
    with tarfile.open(output / name, 'w:gz') as archive:
        for path, relative in files:
            archive.add(path, arcname=relative)

def unpack(path, destination):
    with tarfile.open(path) as archive:
        for item in archive.getmembers():
            relative = Path(item.name)
            assert item.isfile() and not relative.is_absolute() and '..' not in relative.parts
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(item) as source, target.open('wb') as stream:
                shutil.copyfileobj(source, stream)

def download(record, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(record['url'], timeout=90) as source, target.open('wb') as stream:
                shutil.copyfileobj(source, stream, length=1024 * 1024)
            assert target.stat().st_size == record['bytes'], record['filename']
            assert sha(target) == record['sha256'], record['filename']
            print('Official input acquired and hash verified:', record['filename'], record['bytes'], flush=True)
            return
        except (urllib.error.URLError, TimeoutError, OSError, AssertionError):
            if attempt == 3:
                raise
            target.unlink(missing_ok=True)
            time.sleep(2 * (attempt + 1))

def selected(part):
    assert part in [0, 1, 2]
    return manifest['recordings'][part * 4:(part + 1) * 4]

if args.stage == 'acquire':
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        raw_files = []
        private_files = []
        for record in manifest['recordings']:
            path = temporary / 'raw' / record['filename']
            download(record, path)
            raw_files.append((path, record['filename']))
        for record in manifest['modelFiles'] + manifest['runtimeFiles']:
            relative = ('weights/' if record in manifest['modelFiles'] else 'model/') + record['filename']
            path = temporary / 'runtime' / relative
            download(record, path)
            private_files.append((path, relative))
        pack('recordings.tar.gz', raw_files)
        pack('private-inference-inputs.tar.gz', private_files)
    save('acquisition.json', {'status': 'success', 'source': manifest, 'recordingsSHA256': sha(output / 'recordings.tar.gz'), 'privatePayloadSHA256': sha(output / 'private-inference-inputs.tar.gz'), 'redistribution': 'Private inference payload contains unmodified upstream RAIL artifacts. It is not included in public source/image/result archives.'})
elif args.stage == 'convert':
    import numpy as np
    import soundfile as sf
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(output / 'recordings.tar.gz', temporary / 'raw')
        files = []
        reports = []
        for record in selected(args.part):
            source = temporary / 'raw' / record['filename']
            assert sha(source) == record['sha256']
            target = temporary / (Path(record['filename']).stem + '.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-y', str(target)], check=True)
            data, sr = sf.read(target, dtype='float32', always_2d=True)
            assert data.shape[0] > 0 and np.isfinite(data).all()
            rms = float(np.sqrt(np.mean(data.astype('float64') ** 2)))
            assert rms > 0
            reports.append({'filename': target.name, 'source': record['filename'], 'sampleRate': sr, 'frames': len(data), 'channels': data.shape[1], 'durationSeconds': len(data) / sr, 'rms': rms, 'wavSHA256': sha(target)})
            files.append((target, target.name))
        pack('waveforms-' + str(args.part) + '.tar.gz', files)
        save('waveform-qc-' + str(args.part) + '.json', reports)
elif args.stage == 'spectrogram':
    import matplotlib.pyplot as plt
    from scipy.io import wavfile
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(output / ('waveforms-' + str(args.part) + '.tar.gz'), temporary)
        files = []
        for path in sorted(temporary.glob('*.wav')):
            sr, data = wavfile.read(path)
            channels = 1 if data.ndim == 1 else data.shape[1]
            fig, axes = plt.subplots(channels, 1, figsize=(7.2, 4.2), squeeze=False)
            for index in range(channels):
                axis = axes[index, 0]
                signal = data if channels == 1 else data[:, index]
                _, _, _, artist = axis.specgram(signal, Fs=sr, NFFT=256, noverlap=128)
                axis.set_ylabel('Frequency (Hz)')
                axis.set_xlabel('Decoded time (s)')
                fig.colorbar(artist, ax=axis, label='Power (dB)')
            fig.suptitle(path.name + ' — real hydrophone audio')
            fig.tight_layout()
            target = temporary / (path.stem + '.png')
            fig.savefig(target, dpi=140)
            plt.close(fig)
            files.append((target, target.name))
        assert len(files) == 4
        pack('spectrograms-' + str(args.part) + '.tar.gz', files)
elif args.stage == 'predict':
    import torch
    from safetensors.torch import load_file
    torch.set_num_threads(2)
    acquired = json.loads((output / 'acquisition.json').read_text())
    assert sha(output / 'private-inference-inputs.tar.gz') == acquired['privatePayloadSHA256']
    qc = json.loads((output / ('waveform-qc-' + str(args.part) + '.json')).read_text())
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(output / 'private-inference-inputs.tar.gz', temporary / 'runtime')
        unpack(output / ('waveforms-' + str(args.part) + '.tar.gz'), temporary / 'audio')
        for record in manifest['modelFiles'] + manifest['runtimeFiles']:
            relative = ('weights/' if record in manifest['modelFiles'] else 'model/') + record['filename']
            assert sha(temporary / 'runtime' / relative) == record['sha256']
        sys.path.insert(0, str(temporary / 'runtime'))
        model_module = importlib.import_module('model')
        config = json.loads((temporary / 'runtime/weights/config.json').read_text())
        config['model']['device'] = 'cpu'
        config['model']['precision'] = 'float32'
        model = model_module.OrcaHelloSRKWDetectorV1(config)
        weights = load_file(temporary / 'runtime/weights/model.safetensors', device='cpu')
        loaded = model.load_state_dict(weights, strict=True)
        assert not loaded.missing_keys and not loaded.unexpected_keys
        model.eval()
        results = []
        for item in qc:
            path = temporary / 'audio' / item['filename']
            assert sha(path) == item['wavSHA256']
            result = asdict(model.detect_srkw_from_file(str(path)))
            segments = result['segment_predictions']
            assert segments and len(segments) == len(result['local_confidences']) == len(result['local_predictions'])
            assert all(math.isfinite(s['confidence']) and 0 <= s['confidence'] <= 1 for s in segments)
            assert result['local_predictions'] == [int(s['confidence'] > config['global_prediction']['pred_local_threshold']) for s in segments]
            result['metadata']['wav_file_path'] = item['filename']
            results.append({'audio': item, 'inference': result})
        save('predictions-' + str(args.part) + '.json', {'status': 'success', 'part': args.part, 'strictWeightsLoaded': True, 'loadedTensorCount': len(weights), 'modelSHA256': next(r['sha256'] for r in manifest['modelFiles'] if r['filename'] == 'model.safetensors'), 'sourceHashes': {r['filename']: r['sha256'] for r in manifest['runtimeFiles']}, 'windowSeconds': config['inference']['window_s'], 'hopSeconds': config['inference']['window_hop_s'], 'localThreshold': config['global_prediction']['pred_local_threshold'], 'globalThreshold': config['global_prediction']['pred_global_threshold'], 'samples': results})
elif args.stage == 'merge':
    reports = [json.loads((output / ('predictions-' + str(part) + '.json')).read_text()) for part in range(3)]
    assert all(r['status'] == 'success' and r['strictWeightsLoaded'] for r in reports)
    assert len({r['modelSHA256'] for r in reports}) == 1
    samples = sorted([sample for report in reports for sample in report['samples']], key=lambda s: s['audio']['filename'])
    assert len(samples) == 12 and len({s['audio']['filename'] for s in samples}) == 12
    save('merged-predictions.json', {'status': 'success', 'sensor': manifest['sensor'], 'sourceSessionTimestamp': manifest['sourceSessionTimestamp'], 'modelRevision': manifest['modelRevision'], 'modelSHA256': reports[0]['modelSHA256'], 'sourceHashes': reports[0]['sourceHashes'], 'strictWeightsLoaded': True, 'loadedTensorCount': reports[0]['loadedTensorCount'], 'windowSeconds': reports[0]['windowSeconds'], 'hopSeconds': reports[0]['hopSeconds'], 'localThreshold': reports[0]['localThreshold'], 'globalThreshold': reports[0]['globalThreshold'], 'samples': samples})
elif args.stage == 'summary':
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw
    report = json.loads((output / 'merged-predictions.json').read_text())
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for part in range(3):
            unpack(output / ('waveforms-' + str(part) + '.tar.gz'), temporary / 'audio')
            unpack(output / ('spectrograms-' + str(part) + '.tar.gz'), temporary / 'spectrograms')
        assert len(list((temporary / 'audio').glob('*.wav'))) == 12
        pictures = sorted((temporary / 'spectrograms').glob('*.png'))
        assert len(pictures) == 12
        contact = Image.new('RGB', (1600, 1050), 'white')
        draw = ImageDraw.Draw(contact)
        draw.text((18, 10), 'Orcasound: twelve real hydrophone segments - observed spectrograms', fill='black', font_size=23)
        for index, path in enumerate(pictures):
            with Image.open(path) as image:
                image.thumbnail((400, 320))
                contact.paste(image, ((index % 4) * 400, 45 + (index // 4) * 330))
        contact.save(output / 'hydrophone-spectrograms.png')
        fig, axis = plt.subplots(figsize=(12, 5))
        offset = 0.0
        positive = 0
        windows = 0
        for sample in report['samples']:
            audio, inference = sample['audio'], sample['inference']
            segments = inference['segment_predictions']
            axis.plot([offset + s['start_time_s'] for s in segments], [s['confidence'] for s in segments], '.-', linewidth=1, markersize=4, color='#222222')
            axis.axvline(offset, linewidth=0.5, color='#aaaaaa')
            offset += audio['durationSeconds']
            positive += sum(inference['local_predictions'])
            windows += len(segments)
        axis.axhline(report['localThreshold'], color='#666666', linestyle='--', label='Configured local candidate threshold')
        axis.set(xlabel='Concatenated decoded segment time (s); boundaries shown', ylabel='Trained model candidate confidence', ylim=(-0.02, 1.02), title='Orcasound — observed per-window model scores')
        axis.legend(loc='upper right')
        fig.text(0.5, 0.01, 'Model candidates require expert confirmation. Real consecutive HLS objects are decoded separately; this is not a ground-truth whale annotation.', ha='center', fontsize=9)
        fig.tight_layout(rect=(0, 0.035, 1, 1))
        fig.savefig(output / 'orca-confidence.svg')
        plt.close(fig)
        report.update(recordingCount=12, decodedSeconds=offset, inferenceWindowCount=windows, positiveCandidateWindowCount=positive, positiveFileCount=sum(s['inference']['global_prediction'] for s in report['samples']), finding='Scores are trained-model candidates from public real hydrophone audio, not confirmed species observations.', distribution='Public outputs exclude the private upstream model/source payload.')
        files = [(path, 'audio/' + path.name) for path in sorted((temporary / 'audio').glob('*.wav'))] + [(path, 'spectrograms/' + path.name) for path in pictures]
        for name in ['hydrophone-spectrograms.png', 'orca-confidence.svg', 'merged-predictions.json']:
            files.append((output / name, name))
        report['resultSHA256'] = {relative: sha(path) for path, relative in files}
        save('orcasound-summary.json', report)
        files.append((output / 'orcasound-summary.json', 'orcasound-summary.json'))
        pack('orcasound-results.tar.gz', files)
else:
    raise SystemExit('Unknown stage')
save('stage-' + args.stage + ('-' + str(args.part) if args.part is not None else '') + '.json', {'status': 'success', 'stage': args.stage, 'part': args.part, 'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()})
