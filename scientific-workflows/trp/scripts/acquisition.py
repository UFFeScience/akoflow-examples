import concurrent.futures
import hashlib
import json
from pathlib import Path
import time

import pandas as pd
import requests


def request(session, method, url, **kwargs):
    for attempt in range(4):
        try:
            response = session.request(method, url, timeout=(20, 180), **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def digest(path, algorithm='sha256'):
    value = hashlib.new(algorithm)
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def download_gdc(df_files, group, retries=5, delay=5):
    import config
    selected = df_files.query('group == @group').drop_duplicates('file_id').to_dict('records')
    expected = {}
    with requests.Session() as session:
        for offset in range(0, len(selected), 100):
            ids = [row['file_id'] for row in selected[offset:offset + 100]]
            filters = {'op': 'in', 'content': {'field': 'file_id', 'value': ids}}
            response = request(session, 'GET', config.GDC_API_ENDPOINTS['files'], params={
                'filters': json.dumps(filters), 'fields': 'file_id,md5sum,file_size', 'size': len(ids),
            })
            for row in response.json()['data']['hits']:
                expected[row['file_id']] = row
    if len(expected) != len(selected):
        raise RuntimeError(f'GDC did not return all requested UUIDs for {group}')
    folder = Path(config.TCGA_DATA_DIRS['raw'][group.lower().replace(' ', '-')])
    receipts = Path(config.ROOT_DIR) / 'receipts/gdc'
    receipts.mkdir(parents=True, exist_ok=True)

    def acquire(row):
        identifier = row['file_id']
        metadata = expected[identifier]
        name = row['experimental_strategy'].lower() + '_' + identifier + '.' + row['data_format'].lower()
        target = folder / name
        url = config.GDC_API_ENDPOINTS['data'] + '/' + identifier
        for attempt in range(4):
            temporary = target.with_suffix(target.suffix + '.partial')
            try:
                if not target.exists():
                    with requests.Session() as session, request(session, 'GET', url, stream=True) as response, temporary.open('wb') as destination:
                        for block in response.iter_content(1024 * 1024):
                            destination.write(block)
                    if temporary.stat().st_size != metadata['file_size'] or digest(temporary, 'md5') != metadata['md5sum']:
                        raise RuntimeError('GDC input length or MD5 mismatch: ' + identifier)
                    temporary.replace(target)
                if target.stat().st_size != metadata['file_size'] or digest(target, 'md5') != metadata['md5sum']:
                    raise RuntimeError('Cached GDC input failed verification: ' + identifier)
                record = {'file_id': identifier, 'url': url, 'bytes': target.stat().st_size, 'md5': metadata['md5sum'], 'sha256': digest(target), 'group': group}
                (receipts / (identifier + '.json')).write_text(json.dumps(record, indent=2) + '\n')
                print('Verified GDC input', group, identifier, record['bytes'], flush=True)
                return
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(acquire, selected))


def download_mirwalk(accession):
    import config
    target = Path(config.MIRWALK_DATA_DIRS['external']) / (accession + '.csv')
    receipt_dir = Path(config.ROOT_DIR) / 'receipts/mirwalk'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / (accession + '.json')
    no_hit = Path(config.ROOT_DIR) / 'receipts/mirwalk-no-hits' / (accession + '.json')
    if no_hit.exists():
        record = json.loads(no_hit.read_text())
        page = Path(config.ROOT_DIR) / record['responsePath']
        if digest(page) == record['sha256'] and '<h2>No ID matched your search criteria.</h2>' in page.read_text():
            return
    if target.exists() and receipt.exists():
        record = json.loads(receipt.read_text())
        if digest(target) == record['sha256']:
            return
    for attempt in range(4):
        temporary = target.with_suffix('.partial')
        try:
            with requests.Session() as session:
                result = request(session, 'GET', config.MIRWALK_BASE_URL + '/search/', params={'species': 'human', 'gene': '', 'mirna': accession})
                if '<h2>No ID matched your search criteria.</h2>' in result.text:
                    page = Path(config.ROOT_DIR) / 'receipts/mirwalk-no-hits' / (accession + '.html')
                    page.parent.mkdir(parents=True, exist_ok=True)
                    page.write_bytes(result.content)
                    no_hit.write_text(json.dumps({'accession': accession, 'status': 'no-match', 'queryUrl': result.url, 'responsePath': str(page.relative_to(config.ROOT_DIR)), 'bytes': page.stat().st_size, 'sha256': digest(page)}, indent=2) + '\n')
                    print('Verified miRWalk no-match response', accession, flush=True)
                    return
                if 'Export CSV' not in result.text:
                    raise RuntimeError('miRWalk did not expose a CSV export for ' + accession)
                with request(session, 'GET', config.MIRWALK_BASE_URL + '/export/csv/', stream=True) as response, temporary.open('wb') as destination:
                    for block in response.iter_content(1024 * 1024):
                        destination.write(block)
            header = pd.read_csv(temporary, nrows=1)
            if header.empty or not {'mirnaid', 'genesymbol', 'bindingp', 'position', 'TargetScan'}.issubset(header.columns):
                raise RuntimeError('Invalid or empty miRWalk CSV: ' + accession)
            temporary.replace(target)
            receipt.write_text(json.dumps({'accession': accession, 'queryUrl': result.url, 'exportUrl': config.MIRWALK_BASE_URL + '/export/csv/', 'bytes': target.stat().st_size, 'sha256': digest(target)}, indent=2) + '\n')
            print('Verified miRWalk input', accession, target.stat().st_size, flush=True)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def download_all_mirwalk(accessions):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download_mirwalk, accessions))
