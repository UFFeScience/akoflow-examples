import hashlib
import json
from pathlib import Path
import tarfile


def stream_digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def check_archive(path, report):
    names = set()
    snapshot_hashes = {}
    receipts = []
    no_hits = []
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert member.name not in names
            names.add(member.name)
            if member.name.startswith('project/data/external/mirwalk/') and member.name.endswith('.csv'):
                snapshot_hashes[member.name] = stream_digest(archive.extractfile(member))
            elif member.name.startswith('project/receipts/mirwalk/') and member.name.endswith('.json'):
                receipts.append(json.load(archive.extractfile(member)))
            elif member.name.startswith('project/receipts/mirwalk-no-hits/'):
                if member.name.endswith('.html'):
                    content = archive.extractfile(member).read()
                    assert b'<h2>No ID matched your search criteria.</h2>' in content
                    snapshot_hashes[member.name] = hashlib.sha256(content).hexdigest()
                elif member.name.endswith('.json'):
                    no_hits.append(json.load(archive.extractfile(member)))
    assert len([name for name in names if name.startswith('project/stage-records/') and name.endswith('.json')]) == 6
    for group in report['groups']:
        for name in ['interaction-network-edges.csv', 'interaction-network-nodes.csv', 'association-network-edges.csv', 'association-network-nodes.csv']:
            assert 'project/data/processed/networks/' + group['group'] + '/' + name in names
    assert len(receipts) == report['mirwalkFileCount']
    assert len(no_hits) == report.get('mirwalkNoMatchCount', 0)
    assert not {r['accession'] for r in receipts} & {r['accession'] for r in no_hits}
    for record in receipts:
        assert snapshot_hashes['project/data/external/mirwalk/' + record['accession'] + '.csv'] == record['sha256']
    for record in no_hits:
        assert record['status'] == 'no-match'
        assert snapshot_hashes['project/' + record['responsePath']] == record['sha256']
