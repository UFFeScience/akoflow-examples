import argparse
from pathlib import Path
import hashlib
import importlib
import json
import pickle
import shutil
import tarfile
import tempfile
import time
import urllib.request

import numpy as np
import pandas as pd
from osgeo import gdal, osr

gdal.UseExceptions()
parser = argparse.ArgumentParser()
parser.add_argument('--stage', required=True)
parser.add_argument('--model', choices=['knn', 'rf'])
parser.add_argument('--output', default='.')
args = parser.parse_args()
root = Path('/app')
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / 'data/input-verification.json').read_text())
bounds = manifest['boundsWestSouthEastNorth']
features = ['aspect', 'elevation', 'hillshading', 'slope']
sys_path = str(root / 'scripts/upstream')
import sys
sys.path.insert(0, sys_path)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if callable(value):
        return value.__module__ + '.' + value.__name__
    return value

def save(name, value):
    (out / name).write_text(json.dumps(clean(value), indent=2, allow_nan=False) + '\n')

def pack(path, files):
    with tarfile.open(path, 'w:gz') as archive:
        for source, name in files:
            archive.add(source, arcname=name)

def unpack(path, destination):
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            relative = Path(member.name)
            assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as stream:
                shutil.copyfileobj(source, stream)

def raster(path, array, resolution):
    ds = gdal.GetDriverByName('GTiff').Create(str(path), array.shape[1], array.shape[0], 1, gdal.GDT_Float32, ['COMPRESS=LZW', 'TILED=YES'])
    ds.SetGeoTransform((bounds[0], resolution, 0, bounds[3], 0, -resolution))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(float('nan'))
    band.WriteArray(array)
    band.FlushCache()
    ds = None

def read_raster(path):
    ds = gdal.Open(str(path))
    return ds.ReadAsArray(), ds.GetGeoTransform()

if args.stage == 'acquire':
    files = []
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for record in manifest['files']:
            target = temporary / record['filename']
            target.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(record['url'], timeout=90) as source, target.open('wb') as stream:
                        shutil.copyfileobj(source, stream, 1024 * 1024)
                    assert target.stat().st_size == record['bytes'] and digest(target) == record['sha256']
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(2 * (attempt + 1))
            files.append((target, record['filename']))
            print('Verified official raw observation:', record['filename'], flush=True)
        pack(out / 'raw-observations.tar.gz', files)
    save('acquisition.json', {'status': 'success', 'files': manifest['files'], 'rawArchiveSHA256': digest(out / 'raw-observations.tar.gz'), 'distribution': 'Original ESA files are local inputs only; public artifacts contain derived scientific results.'})
elif args.stage == 'moisture':
    import netCDF4
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(out / 'raw-observations.tar.gz', temporary)
        daily = []
        for path in sorted((temporary / 'soil-moisture').glob('*.nc')):
            record = next(r for r in manifest['files'] if Path(r['filename']).name == path.name)
            assert digest(path) == record['sha256']
            with netCDF4.Dataset(path) as source:
                assert source.variables['sm'].units == 'm3 m-3'
                lat, lon = source.variables['lat'][:], source.variables['lon'][:]
                iy = np.where((lat >= bounds[1]) & (lat < bounds[3]))[0]
                ix = np.where((lon >= bounds[0]) & (lon < bounds[2]))[0]
                values = source.variables['sm'][0, :, :][np.ix_(iy, ix)]
                values = values[np.argsort(lat[iy])[::-1], :][:, np.argsort(lon[ix])]
                daily.append(values)
        assert len(daily) == 31
        stack = np.ma.stack(daily)
        monthly = stack.mean(axis=0)
        counts = stack.count(axis=0)
        assert monthly.shape == (8, 8) and monthly.count() > 30
        assert np.all((monthly.compressed() >= 0) & (monthly.compressed() <= 1))
        raster(out / 'monthly-moisture.tif', monthly.filled(np.nan), 0.25)
        raster(out / 'valid-days.tif', counts, 0.25)
        save('monthly-qc.json', {'status': 'success', 'dailyFiles': 31, 'shape': [8, 8], 'validMonthlyCells': int(monthly.count()), 'validDailyCellValues': int(stack.count()), 'units': 'm3 m-3', 'bounds': bounds, 'minimum': float(monthly.min()), 'maximum': float(monthly.max()), 'missingRule': 'Mean of available nonmissing daily soil-moisture observations; same missing-value aggregation purpose as upstream. Additional product quality flags are not silently reinterpreted.'})
elif args.stage == 'mosaic':
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(out / 'raw-observations.tar.gz', temporary)
        paths = sorted((temporary / 'surface-elevation').glob('*.tif'))
        assert len(paths) == 4
        for path in paths:
            assert digest(path) == next(r['sha256'] for r in manifest['files'] if Path(r['filename']).name == path.name)
        vrt = gdal.BuildVRT(str(temporary / 'mosaic.vrt'), [str(p) for p in paths])
        s, d = osr.SpatialReference(), osr.SpatialReference()
        s.ImportFromEPSG(4326)
        d.ImportFromEPSG(32614)
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        d.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(s, d)
        corners = [transform.TransformPoint(x, y) for x in [bounds[0], bounds[2]] for y in [bounds[1], bounds[3]]]
        extent = [min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners)]
        result = gdal.Warp(str(out / 'metric-surface.tif'), vrt, dstSRS='EPSG:32614', outputBounds=extent, xRes=90, yRes=90, resampleAlg='bilinear', dstNodata=-9999, creationOptions=['COMPRESS=LZW', 'TILED=YES'])
        assert result is not None
        result = None
elif args.stage == 'terrain':
    files = []
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        shutil.copyfile(out / 'metric-surface.tif', temporary / 'elevation.tif')
        for mode, name in [('aspect', 'aspect'), ('hillshade', 'hillshading'), ('slope', 'slope')]:
            options = {'computeEdges': True, 'creationOptions': ['COMPRESS=LZW', 'TILED=YES']}
            if mode == 'aspect':
                options['zeroForFlat'] = True
            result = gdal.DEMProcessing(str(temporary / (name + '.tif')), str(out / 'metric-surface.tif'), mode, **options)
            assert result is not None
            result = None
        for name in features:
            files.append((temporary / (name + '.tif'), name + '.tif'))
        pack(out / 'terrain-features.tar.gz', files)
    save('terrain-qc.json', {'status': 'success', 'source': 'Copernicus GLO-90 2021 digital surface model', 'metricEPSG': 32614, 'metricResolutionMetres': 90, 'slopeAspectMethod': 'GDAL default Horn on metric height/planimetric coordinates', 'aspectFlatPolicy': 'zeroForFlat', 'features': features, 'heightInterpretation': 'Surface including vegetation/infrastructure, not bare-earth terrain; used as static 2021 covariate for 2010 soil moisture.'})
elif args.stage in ['train-table', 'eval-table']:
    coarse = args.stage == 'train-table'
    resolution = 0.25 if coarse else 0.01
    width = int(round((bounds[2] - bounds[0]) / resolution))
    height = int(round((bounds[3] - bounds[1]) / resolution))
    xs = bounds[0] + (np.arange(width) + 0.5) * resolution
    ys = bounds[3] - (np.arange(height) + 0.5) * resolution
    x, y = np.meshgrid(xs, ys)
    values = {'x': x.ravel(), 'y': y.ravel()}
    if coarse:
        moisture, _ = read_raster(out / 'monthly-moisture.tif')
        values['z'] = moisture.ravel()
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        unpack(out / 'terrain-features.tar.gz', temporary)
        for name in features:
            ds = gdal.Warp('', str(temporary / (name + '.tif')), format='MEM', dstSRS='EPSG:4326', outputBounds=bounds, width=width, height=height, resampleAlg='average', dstNodata=float('nan'))
            array = ds.ReadAsArray()
            ds = None
            values[name] = array.ravel()
    frame = pd.DataFrame(values).replace([np.inf, -np.inf], np.nan).dropna()
    assert len(frame) == width * height
    frame.to_csv(out / ('train.csv' if coarse else 'eval.csv'), index=False)
    save(('train' if coarse else 'eval') + '-table-qc.json', {'status': 'success', 'rows': len(frame), 'columns': list(frame.columns), 'shape': [height, width], 'EPSG': 4326, 'resolutionDegrees': resolution, 'covariateResampling': 'area average from metric DSM-derived covariates', 'droppedRows': width * height - len(frame)})
elif args.stage == 'train':
    from functools import partial
    from sklearn.model_selection import RandomizedSearchCV
    from sklearn.metrics import mean_squared_error, r2_score
    module = importlib.import_module(args.model)
    np.random.seed(3)
    class RecordedSearch(RandomizedSearchCV):
        def fit(self, *values, **kwargs):
            fitted = super().fit(*values, **kwargs)
            result = pd.DataFrame(self.cv_results_)
            for column in result.columns:
                if column.startswith('param_'):
                    result[column] = result[column].map(clean)
            result.to_csv(out / (args.model + '-cv.csv'), index=False)
            return fitted
    module.RandomizedSearchCV = RecordedSearch
    if args.model == 'rf':
        module.RandomForestRegressor = partial(module.RandomForestRegressor, random_state=3)
    training = pd.read_csv(out / 'train.csv')
    x_train, y_train, x_test, y_test, scaler = module.split_and_preprocess_trainingdata(training)
    if args.model == 'knn':
        model = module.train_knn(x_train, y_train, 20, 3, scaler)
    else:
        model = module.train_rf(x_train, y_train, 2000, 3)
    predicted = model.predict(x_test)
    heldout = training.loc[y_test.index, ['x', 'y', 'z']].copy()
    heldout['prediction'] = predicted
    heldout.to_csv(out / (args.model + '-heldout.csv'), index=False)
    with (out / (args.model + '-model.pkl')).open('wb') as stream:
        pickle.dump(model, stream)
    with (out / (args.model + '-scaler.pkl')).open('wb') as stream:
        pickle.dump(scaler, stream)
    cv = pd.read_csv(out / (args.model + '-cv.csv'))
    save(args.model + '-training.json', {'status': 'success', 'model': args.model, 'trainingRows': len(x_train), 'heldoutRows': len(x_test), 'trainIndices': list(y_train.index), 'heldoutIndices': list(y_test.index), 'seed': 3, 'cvFolds': 10, 'cvCandidates': len(cv), 'maxK': 20 if args.model == 'knn' else None, 'maxTrees': 2000 if args.model == 'rf' else None, 'selectedParameters': model.get_params(), 'heldoutRMSE': float(np.sqrt(mean_squared_error(y_test, predicted))), 'heldoutR2': float(r2_score(y_test, predicted)), 'upstreamSourceSHA256': digest(root / 'scripts/upstream' / (args.model + '.py')), 'adaptation': 'Original model/search functions. Explicit NumPy split seed and RF estimator seed 3; full original candidate spaces and cross-validation retained. Search instrumentation records actual CV results.'})
elif args.stage == 'predict':
    module = importlib.import_module(args.model)
    with (out / (args.model + '-model.pkl')).open('rb') as stream:
        model = pickle.load(stream)
    with (out / (args.model + '-scaler.pkl')).open('rb') as stream:
        scaler = pickle.load(stream)
    frame = pd.read_csv(out / 'eval.csv')
    normalized = module.preprocess_evaluationdata(frame, scaler)
    target = out / (args.model + '-predictions.csv')
    getattr(module, 'predict_' + args.model)(normalized, frame, str(target), model)
    predictions = pd.read_csv(target, header=None, names=['x', 'y', 'sm'])
    assert len(predictions) == len(frame) == 40000 and np.isfinite(predictions.to_numpy()).all()
    raster(out / (args.model + '-predictions.tif'), predictions['sm'].to_numpy().reshape(200, 200), 0.01)
elif args.stage == 'diagnostics':
    import matplotlib.pyplot as plt
    from sklearn.metrics import mean_squared_error, r2_score
    observed, _ = read_raster(out / 'monthly-moisture.tif')
    counts, _ = read_raster(out / 'valid-days.tif')
    predictions = {name: read_raster(out / (name + '-predictions.tif'))[0] for name in ['knn', 'rf']}
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    panels = [('Observed January 2010 monthly moisture', observed), ('Valid daily observations per monthly cell', counts), ('Original SOMOSPIE KNN spatial inference', predictions['knn']), ('Original SOMOSPIE RF spatial inference', predictions['rf'])]
    for index, (title, values) in enumerate(panels):
        axis = axes.flat[index]
        coverage = index == 1
        artist = axis.imshow(values, extent=extent, origin='upper', vmin=0 if coverage else float(np.nanmin(observed)), vmax=31 if coverage else float(np.nanmax(observed)), cmap='Greys' if coverage else 'viridis')
        axis.set(title=title, xlabel='Longitude', ylabel='Latitude')
        fig.colorbar(artist, ax=axis, label='Valid days' if coverage else 'Volumetric soil moisture (m3/m3)')
    fig.suptitle('SOMOSPIE - real ESA observations and DSM-informed predictions')
    fig.tight_layout()
    fig.savefig(out / 'soil-moisture-maps.png', dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    reports = {}
    for axis, name in zip(axes, ['knn', 'rf']):
        heldout = pd.read_csv(out / (name + '-heldout.csv'))
        training = json.loads((out / (name + '-training.json')).read_text())
        rmse = float(np.sqrt(mean_squared_error(heldout['z'], heldout['prediction'])))
        r2 = float(r2_score(heldout['z'], heldout['prediction']))
        assert abs(rmse - training['heldoutRMSE']) < 1e-12
        axis.scatter(heldout['z'], heldout['prediction'], color='#222222')
        low, high = float(np.nanmin(observed)), float(np.nanmax(observed))
        axis.plot([low, high], [low, high], '--', color='#999999')
        axis.set(xlabel='Observed monthly moisture (m3/m3)', ylabel='Held-out prediction (m3/m3)', title=name.upper() + ': n=' + str(len(heldout)) + ', RMSE=' + format(rmse, '.4f') + ', R2=' + format(r2, '.3f'))
        reports[name] = training
    fig.suptitle('Actual shared coarse-cell holdout - limited small-region diagnostic')
    fig.tight_layout()
    fig.savefig(out / 'heldout-diagnostics.png', dpi=150)
    plt.close(fig)
    report = {'status': 'success', 'bounds': bounds, 'EPSG': 4326, 'period': ['2010-01-01', '2010-01-31'], 'soilMoistureUnits': 'm3 m-3', 'sourceFiles': 35, 'monthlyQC': json.loads((out / 'monthly-qc.json').read_text()), 'terrainQC': json.loads((out / 'terrain-qc.json').read_text()), 'trainTable': json.loads((out / 'train-table-qc.json').read_text()), 'evalTable': json.loads((out / 'eval-table-qc.json').read_text()), 'models': reports, 'predictionRowsPerModel': 40000, 'fineResolutionDegrees': 0.01, 'interpretation': 'Statistical spatial inference from 0.25-degree observations and static 2021 surface covariates. Fine pixels are not new independent measurements. Seven heldout coarse cells do not establish spatial/temporal generalization.', 'originalRawFilesExcludedFromPublicResults': True}
    public = ['monthly-moisture.tif', 'valid-days.tif', 'monthly-qc.json', 'terrain-qc.json', 'train.csv', 'eval.csv', 'train-table-qc.json', 'eval-table-qc.json', 'soil-moisture-maps.png', 'heldout-diagnostics.png']
    for name in ['knn', 'rf']:
        public += [name + suffix for suffix in ['-model.pkl', '-scaler.pkl', '-training.json', '-cv.csv', '-heldout.csv', '-predictions.csv', '-predictions.tif']]
    report['resultSHA256'] = {name: digest(out / name) for name in public}
    save('derived-summary.json', report)
    pack(out / 'derived-results.tar.gz', [(out / name, name) for name in public + ['derived-summary.json']])
elif args.stage == 'package':
    for source, destination in [('derived-summary.json', 'somospie-summary.json'), ('derived-results.tar.gz', 'somospie-results.tar.gz'), ('soil-moisture-maps.png', 'published-soil-moisture-maps.png'), ('heldout-diagnostics.png', 'published-heldout-diagnostics.png')]:
        shutil.copyfile(out / source, out / destination)
else:
    raise SystemExit('Unknown stage')
save('stage-' + args.stage + ('-' + args.model if args.model else '') + '.json', {'status': 'success', 'stage': args.stage, 'model': args.model})
