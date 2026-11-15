import argparse, hashlib, importlib, json, pickle, sys, tarfile, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from osgeo import gdal
from PIL import Image
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

parser = argparse.ArgumentParser()
parser.add_argument('--definition', action='store_true')
parser.add_argument('--output', default='/outputs')
args = parser.parse_args()
app = Path('/app')
sys.path.insert(0, str(app / 'scripts/upstream'))
manifest = json.loads((app / 'data/input-verification.json').read_text())
workflow = json.loads((app / 'workflow.json').read_text())
assert len(workflow['spec']['activities']) == 12
assert len(manifest['files']) == 35 and sum(r['bytes'] for r in manifest['files']) == 60606972
assert len({r['sha256'] for r in manifest['files']}) == 35
for name in ['knn', 'rf']:
    expected = json.loads((app / 'data/upstream.json').read_text())['sha256'][name + '.py']
    assert hashlib.sha256((app / 'scripts/upstream' / (name + '.py')).read_bytes()).hexdigest() == expected
if args.definition:
    print(json.dumps({'status': 'success', 'definitionOnly': True, 'activities': 12, 'realSourceObjects': 35}))
    raise SystemExit
out = Path(args.output)
report = json.loads((out / 'somospie-summary.json').read_text())
assert report['status'] == 'success' and report['predictionRowsPerModel'] == 40000
assert report['monthlyQC']['dailyFiles'] == 31
assert report['monthlyQC']['validMonthlyCells'] == 64
assert report['monthlyQC']['validDailyCellValues'] == 722
assert report['originalRawFilesExcludedFromPublicResults'] is True
with tempfile.TemporaryDirectory() as temporary:
    target = Path(temporary)
    with tarfile.open(out / 'somospie-results.tar.gz') as archive:
        names = archive.getnames()
        assert len(names) == len(set(names)) == 25
        assert set(names) == set(report['resultSHA256']) | {'derived-summary.json'}
        for member in archive.getmembers():
            assert member.isfile() and Path(member.name).name == member.name
            assert not member.name.endswith('.nc') and 'Copernicus_DSM' not in member.name
            (target / member.name).write_bytes(archive.extractfile(member).read())
    assert json.loads((target / 'derived-summary.json').read_text()) == report
    for name, expected in report['resultSHA256'].items():
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == expected
    train, evaluation = [pd.read_csv(target / name) for name in ['train.csv', 'eval.csv']]
    assert train.shape == (64, 7) and evaluation.shape == (40000, 6)
    assert list(train.columns) == ['x', 'y', 'z', 'aspect', 'elevation', 'hillshading', 'slope']
    assert np.isfinite(train.to_numpy()).all() and np.isfinite(evaluation.to_numpy()).all()
    for name, shape, resolution in [('monthly-moisture.tif', (8, 8), .25), ('valid-days.tif', (8, 8), .25), ('knn-predictions.tif', (200, 200), .01), ('rf-predictions.tif', (200, 200), .01)]:
        ds = gdal.Open(str(target / name))
        assert (ds.RasterYSize, ds.RasterXSize) == shape
        assert np.allclose(ds.GetGeoTransform(), (-99, resolution, 0, 37, 0, -resolution))
        assert ds.GetSpatialRef().GetAuthorityCode(None) == '4326'
        assert np.isfinite(ds.ReadAsArray()).all()
    observed = gdal.Open(str(target / 'monthly-moisture.tif')).ReadAsArray().ravel()
    assert np.allclose(observed, train.z)
    counts = gdal.Open(str(target / 'valid-days.tif')).ReadAsArray()
    assert counts.sum() == 722 and counts.min() >= 1 and counts.max() <= 31
    np.random.seed(3)
    train_indices, heldout_indices = train_test_split(np.arange(64), test_size=.1)
    for name, candidates in [('knn', 50), ('rf', 10)]:
        importlib.import_module(name)
        info = json.loads((target / (name + '-training.json')).read_text())
        assert info['trainIndices'] == list(train_indices) and info['heldoutIndices'] == list(heldout_indices)
        assert len(set(train_indices) & set(heldout_indices)) == 0
        assert info['trainingRows'] == 57 and info['heldoutRows'] == 7 and info['cvCandidates'] == candidates and info['cvFolds'] == 10
        cv = pd.read_csv(target / (name + '-cv.csv'))
        assert len(cv) == candidates and all('split' + str(i) + '_test_score' in cv for i in range(10))
        assert np.isfinite(cv['mean_test_score']).all()
        with (target / (name + '-model.pkl')).open('rb') as stream: model = pickle.load(stream)
        with (target / (name + '-scaler.pkl')).open('rb') as stream: scaler = pickle.load(stream)
        x = train.drop(columns='z')
        assert np.allclose(scaler.mean_, x.iloc[train_indices].mean())
        heldout = pd.read_csv(target / (name + '-heldout.csv'))
        predicted = model.predict(scaler.transform(x.iloc[heldout_indices]))
        assert np.allclose(predicted, heldout.prediction) and np.allclose(heldout.z, train.z.iloc[heldout_indices])
        assert abs(mean_squared_error(heldout.z, predicted) ** .5 - info['heldoutRMSE']) < 1e-12
        assert abs(r2_score(heldout.z, predicted) - info['heldoutR2']) < 1e-12
        predictions = pd.read_csv(target / (name + '-predictions.csv'), header=None)
        recomputed = model.predict(scaler.transform(evaluation))
        assert len(predictions) == 40000 and np.allclose(predictions.iloc[:, :2], evaluation.iloc[:, :2])
        assert np.allclose(recomputed, predictions.iloc[:, 2])
        raster = gdal.Open(str(target / (name + '-predictions.tif'))).ReadAsArray()
        assert np.allclose(recomputed.reshape(200, 200), raster)
        assert (recomputed >= 0).all() and (recomputed <= 1).all()
    for original, published in [('soil-moisture-maps.png', 'published-soil-moisture-maps.png'), ('heldout-diagnostics.png', 'published-heldout-diagnostics.png')]:
        assert (target / original).read_bytes() == (out / published).read_bytes()
        with Image.open(out / published) as image:
            assert image.width >= 1500 and image.height >= 700
            image.verify()
print(json.dumps({'status': 'success', 'realSourceObjects': 35, 'monthlyCells': 64, 'dailyValidValues': 722, 'fullCVCandidates': [50, 10], 'predictionsPerModel': 40000, 'figures': 2, 'originalRawDataRedistributed': False}))
