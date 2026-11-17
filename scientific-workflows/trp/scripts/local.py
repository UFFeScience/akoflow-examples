import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL_IMAGE = 'akoflow-local/trp:workload'
NETWORK_STAGES = {'expression-aggregation', 'interaction-inference'}


def invoke(arguments):
    subprocess.run(arguments, check=True)


def context_digest():
    paths = []
    for folder in ['upstream', 'scripts', 'data']:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(ROOT / name for name in ['requirements.txt', 'docker/Dockerfile', '.dockerignore'])
    result = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(ROOT))):
        result.update((str(path.relative_to(ROOT)) + '\n').encode())
        result.update(path.read_bytes())
    return result.hexdigest()


def docker(image, command, output=None, network='none'):
    arguments = ['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', network,
                 '--user', str(os.getuid()) + ':' + str(os.getgid()), '--env', 'HOME=/tmp']
    if output is not None:
        arguments += ['--mount', 'type=bind,src=' + str(output) + ',dst=/outputs', '--workdir', '/outputs']
    invoke(arguments + [image] + command)


def main():
    parser = argparse.ArgumentParser(description='Build or pull and execute all six TRP stages with Docker. Requires Python 3 and Docker only.')
    parser.add_argument('action', choices=['prepare', 'run', 'validate'])
    parser.add_argument('--pull', action='store_true', help='Use the public digest-pinned image instead of building locally')
    parser.add_argument('--definition', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    digest = context_digest()
    image = os.environ.get('TRP_IMAGE', LOCAL_IMAGE)
    if args.action == 'prepare':
        if args.pull:
            lock = json.loads((ROOT / 'image.lock.json').read_text())
            reference = lock.get('digest', lock['image'])
            invoke(['docker', 'pull', '--platform', lock['platform'], reference])
            invoke(['docker', 'tag', reference, LOCAL_IMAGE])
        else:
            invoke(['docker', 'build', '--platform', 'linux/amd64', '--label', 'io.akoflow.source-sha256=' + digest,
                    '-f', str(ROOT / 'docker/Dockerfile'), '-t', LOCAL_IMAGE, str(ROOT)])
        receipt = {'image': LOCAL_IMAGE, 'imageId': subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', LOCAL_IMAGE], text=True).strip(),
                   'contextSHA256': digest, 'mode': 'pull' if args.pull else 'build'}
        (ROOT / '.prepared-image.json').write_text(json.dumps(receipt, indent=2) + '\n')
        docker(LOCAL_IMAGE, ['python', '/app/scripts/validate.py', '--definition'])
        return
    if image == LOCAL_IMAGE and not os.environ.get('TRP_IMAGE'):
        receipt_path = ROOT / '.prepared-image.json'
        if not receipt_path.is_file():
            raise SystemExit('Run ./prepare.sh or ./prepare.sh --pull first.')
        prepared = json.loads(receipt_path.read_text())
        observed = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], text=True).strip()
        if prepared['contextSHA256'] != digest or prepared['imageId'] != observed:
            raise SystemExit('Source or prepared image changed. Run ./prepare.sh again.')
    output = args.output.resolve()
    if args.action == 'run':
        output.mkdir(parents=True, exist_ok=True)
        existing = list(output.iterdir())
        if existing:
            raise SystemExit('Output directory contains previous results. Select a fresh --output directory; existing files are preserved.')
        contract = json.loads((ROOT / 'data/input.json').read_text())
        for stage in contract['stages']:
            docker(image, ['python', '/app/scripts/run_stage.py', '--stage', stage, '--output', '/outputs'],
                   output, 'bridge' if stage in NETWORK_STAGES else 'none')
        docker(image, ['python', '/app/scripts/validate.py'], output)
    else:
        docker(image, ['python', '/app/scripts/validate.py'] + (['--definition'] if args.definition else []),
               None if args.definition else output)


if __name__ == '__main__':
    main()
