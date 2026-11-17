import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description='Publish a completed scientific run using the daemon\'s existing Hub connection.')
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--api-url', default='http://127.0.0.1:8080/akoflow-api')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    token = os.environ.get('AKOFLOW_API_TOKEN', '')
    if not token and args.env_file:
        for line in args.env_file.read_text().splitlines():
            if line.startswith('AKOFLOW_API_TOKEN='):
                token = line.split('=', 1)[1].strip().strip('\"\x27')
    if not token:
        raise SystemExit('AKOFLOW_API_TOKEN or --env-file is required')

    def call(path, value=None):
        request = urllib.request.Request(
            args.api_url.rstrip('/') + '/' + path.lstrip('/'),
            data=json.dumps(value).encode() if value is not None else None,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f'Daemon request failed: {error.code} {path}') from None

    bundle = args.bundle.resolve()
    evidence = bundle / 'evidence'
    run = json.loads((evidence / 'daemon-run.json').read_text())
    projection = call('execution-runs/' + run['runId'] + '/')
    observed = projection['run']
    count = run['activityCount']
    if observed['status'] != 'completed' or observed['completedActivityCount'] != count:
        raise SystemExit('The requested run has not completed all activities')
    connection = call('hub/status/')
    if not connection.get('connected'):
        raise SystemExit('Sign in using the existing Hub integration before publishing')
    previous = evidence / 'hub-publication.json'
    if previous.exists():
        receipt = json.loads(previous.read_text())
        if receipt.get('runId') == run['runId'] and receipt.get('hubOrigin') == connection['hubUrl']:
            print(json.dumps(receipt, indent=2))
            return
    config = json.loads((bundle / 'data/input.json').read_text())
    slug = 'scientific-workflows-' + bundle.name
    publications = call('hub/publications/')
    publication = next((item for item in publications if item['slug'] == slug), None)
    title = config.get('title', bundle.name.replace('-', ' ').title())
    readme = (bundle / 'README.md').read_text().split('\n<!-- connected-hub-publication -->')[0]
    if publication is None:
        publication = call('hub/publications/', {
            'title': title,
            'slug': slug,
            'description': f'Real scientific computation through the AkôFlow daemon: {count} completed activities.',
            'readme': readme,
            'visibility': 'public',
        })
    preview = call('hub/publications/preview/', {
        'runId': run['runId'],
        'publicationId': publication['id'],
        'message': f'Measured real daemon run: {count}/{count} completed activities.',
    })
    review = preview['review']
    if review['experiment']['executionCount'] != 1 or review['experiment']['activityCount'] != count:
        raise SystemExit('Publication preview does not match the requested run')
    if any(row['summary']['status'] != 'completed' for row in review['results']):
        raise SystemExit('Publication preview contains an incomplete execution')
    (evidence / 'hub-preview.json').write_text(json.dumps(preview, indent=2) + '\n')
    receipt = call('hub/publications/confirm/', {'previewId': preview['id'], 'acknowledgePublic': True})
    owner_kind = 'o' if publication.get('kind') == 'organization' else 'u'
    receipt.update({
        'url': connection['hubUrl'].rstrip('/') + '/' + owner_kind + '/' + preview['publication']['owner'] + '/' + slug,
        'publicationId': publication['id'],
        'runId': run['runId'],
        'hubOrigin': connection['hubUrl'],
        'uri': 'akoflow://hub/publications/' + publication['id'] + '/versions/' + str(receipt['version']),
        'image': run['image'],
        'imageDistribution': 'Build from the source Dockerfile; public registry availability is not inferred.',
    })
    previous.write_text(json.dumps(receipt, indent=2) + '\n')
    section = '\n<!-- connected-hub-publication -->\n\n## Measured daemon execution and Hub version\n\n'
    section += f"[Open the published workflow and measured results]({receipt['url']}). "
    section += f"Run `{run['runId']}` completed **{count}/{count} activities** in **{observed['makespanSeconds']:.3f} seconds**. "
    section += 'These are observed Docker computations. The imported manual plan contains placeholder predicted timings and is not a benchmark.\n\n'
    section += f"Configured Hub origin: `{connection['hubUrl']}`. This receipt applies to that instance. "
    section += 'The OCI image must be built from this bundle on the execution host; public registry availability is not claimed.\n\n'
    section += f"Import URI for this configured Hub:\n\n```text\n{receipt['uri']}\n```\n"
    (bundle / 'README.md').write_text(readme.rstrip() + '\n' + section)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
