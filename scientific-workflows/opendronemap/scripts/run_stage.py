import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

import numpy as np
import rasterio
from PIL import Image

sys.path.insert(0, '/code')
from opendm import config, log
from opendm.osfm import OSFMContext, get_submodel_argv
from stages.dataset import ODMLoadDatasetStage
from stages.splitmerge import ODMMergeStage
from opensfm.large import metadataset

ROOT = Path('/tmp/akoflow-odm')
PROJECT = ROOT / 'project'
DATA = Path('/app/data')
PDAL = '/code/SuperBuild/install/bin/pdal'
OPTIONS = ['--project-path', str(ROOT), '--split', '40', '--split-overlap', '40',
           '--feature-quality', 'low', '--min-num-features', '4000', '--pc-quality', 'lowest',
           '--mesh-size', '50000', '--max-concurrency', '2', '--orthophoto-resolution', '20',
           '--dem-resolution', '40', '--dsm', '--skip-report', 'project']


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def archive(path, relative):
    with tarfile.open(path, 'w') as bundle:
        bundle.add(ROOT / relative, arcname=str(relative))


def restore(path):
    with tarfile.open(path) as bundle:
        for member in bundle.getmembers():
            name = Path(member.name)
            require(not name.is_absolute() and '..' not in name.parts, 'Invalid archive member')
            require(not member.isdev(), 'Device in project archive')
            if member.issym() or member.islnk():
                target = os.path.normpath(os.path.join(str(ROOT / name.parent), member.linkname))
                require(target.startswith(str(PROJECT) + '/') or target.startswith(str(DATA / 'images')),
                        'Project link escaped allowed input roots')
        bundle.extractall(ROOT)


def arguments():
    args = config.config(OPTIONS)
    args.project_path = str(PROJECT)
    log.logger.init_json_output([str(PROJECT / 'adapter-log.json')], args)
    log.logger.log_json_stage_run('akoflow-adapter', datetime.now(timezone.utc))
    return args


def dataset():
    args = arguments()
    outputs = {}
    ODMLoadDatasetStage('dataset', args).process(args, outputs)
    return args, outputs


def submodel(index):
    return PROJECT / 'submodels' / f'submodel_{index:04d}'


def check_reconstruction(path):
    result = read(path / 'opensfm/reconstruction.json')
    shots = set().union(*(set(r['shots']) for r in result)) if result else set()
    points = sum(len(r['points']) for r in result)
    require(len(shots) >= 8 and points > 100, 'Submodel reconstruction is incomplete')
    return {'shots': sorted(shots), 'points': points}


def split(output):
    source = read(DATA / 'source.json')
    for item in source['files']:
        path = DATA / 'images' / item['name']
        require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
                'Invalid real photograph: ' + item['name'])
    PROJECT.mkdir(parents=True)
    (PROJECT / 'images').symlink_to(DATA / 'images', target_is_directory=True)
    args, outputs = dataset()
    reconstruction = outputs['reconstruction']
    require(reconstruction.has_geotagged_photos(), 'GPS coordinates are required')
    photos = sorted(reconstruction.photos, key=lambda p: (p.longitude, p.latitude, p.filename))
    groups = [f'{p.filename} {int(i >= len(photos) // 2)}' for i, p in enumerate(photos)]
    (PROJECT / 'image_groups.txt').write_text('\n'.join(groups) + '\n')
    context = OSFMContext(outputs['tree'].opensfm)
    context.setup(args, outputs['tree'].dataset_raw, reconstruction, append_config=[
        'submodels_relpath: ../submodels/opensfm',
        'submodel_relpath_template: ../submodels/submodel_%04d/opensfm',
        'submodel_images_relpath_template: ../submodels/submodel_%04d/images',
        'submodel_size: 40', 'submodel_overlap: 40'])
    context.photos_to_metadata(photos, args.rolling_shutter, args.rolling_shutter_readout)
    context.feature_matching()
    context.run('create_submodels')
    models = [Path(p).parent for p in metadataset.MetaDataSet(context.opensfm_project_path).get_submodel_paths()]
    require(set(p.name for p in models) == {'submodel_0000', 'submodel_0001'}, 'Expected exactly two submodels')
    photo_sets = [set(p.name for p in submodel(i).joinpath('images').iterdir()) for i in range(2)]
    overlap = photo_sets[0] & photo_sets[1]
    require(len(overlap) >= 5 and all(len(s) < 77 for s in photo_sets), 'Invalid overlap or duplicated full datasets')
    archive(output / 'split.tar', Path('project'))
    return {'sourceCommit': source['commit'], 'photographs': len(photos),
            'submodelPhotos': [len(s) for s in photo_sets], 'sharedPhotos': sorted(overlap),
            'splitArchiveSha256': digest(output / 'split.tar'), 'options': OPTIONS}


def reconstruct(output, index):
    restore(output / 'split.tar')
    args = arguments()
    context = OSFMContext(str(submodel(index) / 'opensfm'))
    context.create_tracks()
    context.reconstruct(args.sfm_algorithm, args.rolling_shutter, not args.sfm_no_partial)
    result = check_reconstruction(submodel(index))
    archive(output / f'reconstructed-{index}.tar', Path('project/submodels') / submodel(index).name)
    return result


def align(output):
    restore(output / 'split.tar')
    for index in range(2):
        restore(output / f'reconstructed-{index}.tar')
        check_reconstruction(submodel(index))
    OSFMContext(str(PROJECT / 'opensfm')).align_reconstructions(False)
    for index in range(2):
        directory = submodel(index) / 'opensfm'
        aligned = directory / 'reconstruction.aligned.json'
        require(aligned.is_file(), 'Native alignment did not produce both submodels')
        (directory / 'reconstruction.json').replace(directory / 'reconstruction.unaligned.json')
        aligned.replace(directory / 'reconstruction.json')
        check_reconstruction(submodel(index))
    archive(output / 'aligned.tar', Path('project'))
    return {'submodelsAligned': 2, 'algorithm': 'OpenSfM align_reconstructions',
            'alignedArchiveSha256': digest(output / 'aligned.tar')}


def process(output, index):
    restore(output / 'aligned.tar')
    args = arguments()
    sys.argv = ['/code/run.py']
    argv = get_submodel_argv(args, str(PROJECT / 'submodels'), submodel(index).name)
    subprocess.run([sys.executable, *argv], cwd='/code', check=True)
    model = submodel(index)
    paths = ['odm_georeferencing/odm_georeferenced_model.laz', 'odm_orthophoto/odm_orthophoto.tif',
             'odm_orthophoto/odm_orthophoto_feathered.tif', 'odm_orthophoto/odm_orthophoto_cut.tif',
             'odm_dem/dsm.tif', 'odm_dem/dsm.euclideand.tif']
    for path in paths:
        require((model / path).is_file() and (model / path).stat().st_size > 0, 'Native product missing: ' + path)
    archive(output / f'products-{index}.tar', Path('project/submodels') / model.name)
    return {'submodel': model.name, 'products': paths, 'archiveSha256': digest(output / f'products-{index}.tar')}


def raster_stats(path):
    with rasterio.open(path) as image:
        require(image.crs is not None and image.width > 10 and image.height > 10, 'Invalid georeferenced raster')
        sample = image.read(1, masked=True, out_shape=(min(image.height, 512), min(image.width, 512)))
        require(sample.count() > 100 and np.isfinite(sample.compressed()).all(), 'Raster has no valid observations')
        return {'width': image.width, 'height': image.height, 'bands': image.count,
                'crs': image.crs.to_string(), 'bounds': list(image.bounds), 'validSamplePixels': int(sample.count()),
                'range': [float(sample.min()), float(sample.max())]}


def merge(output):
    restore(output / 'split.tar')
    for index in range(2):
        restore(output / f'products-{index}.tar')
    args, outputs = dataset()
    counts = [point_summary(submodel(i) / 'odm_georeferencing/odm_georeferenced_model.laz')['num_points'] for i in range(2)]
    for i in range(2):
        require((submodel(i) / 'odm_orthophoto/odm_orthophoto_cut.tif').is_file(), 'Missing submodel merge cutline')
    outputs['large'] = True
    ODMMergeStage('merge', args).process(args, outputs)
    paths = {'orthophoto.tif': 'odm_orthophoto/odm_orthophoto.tif',
             'surface.tif': 'odm_dem/dsm.tif',
             'pointcloud.laz': 'odm_georeferencing/odm_georeferenced_model.laz'}
    for name, path in paths.items():
        require((PROJECT / path).is_file(), 'Native merge did not produce: ' + path)
        shutil.copyfile(PROJECT / path, output / name)
    cloud = point_summary(output / 'pointcloud.laz')
    require(cloud['num_points'] == sum(counts), 'Merged cloud did not retain both complete submodel clouds')
    return {'mergedSubmodels': 2, 'inputPointCounts': counts, 'orthophoto': raster_stats(output / 'orthophoto.tif'),
            'surface': raster_stats(output / 'surface.tif'), 'pointcloud': cloud}


def point_summary(path):
    result = subprocess.run([PDAL, 'info', '--summary', str(path)], check=True, capture_output=True, text=True)
    value = json.loads(result.stdout)['summary']
    require(value['num_points'] > 1000, 'Merged cloud has too few real points')
    return value


def previews(output):
    with rasterio.open(output / 'orthophoto.tif') as image:
        scale = min(1, 1400 / max(image.width, image.height))
        height, width = int(image.height * scale), int(image.width * scale)
        rgb = image.read([1, 2, 3], out_shape=(3, height, width))
        Image.fromarray(np.moveaxis(rgb, 0, 2).astype('uint8')).save(output / 'orthophoto.png')
    with rasterio.open(output / 'surface.tif') as image:
        scale = min(1, 1400 / max(image.width, image.height))
        surface = image.read(1, masked=True, out_shape=(int(image.height * scale), int(image.width * scale)))
        valid = ~np.ma.getmaskarray(surface)
        lo, hi = np.percentile(surface.compressed(), [2, 98])
        normalized = np.clip((surface.filled(lo) - lo) / max(hi - lo, 1e-6), 0, 1)
        ramp = np.array([[30, 60, 115], [45, 140, 125], [165, 195, 110], [220, 155, 85], [245, 240, 225]])
        rgb = np.stack([np.interp(normalized, np.linspace(0, 1, len(ramp)), ramp[:, i]) for i in range(3)], axis=-1)
        dy, dx = np.gradient(surface.filled(lo))
        hillshade = np.clip(0.8 + (dx - dy) * 0.06, 0.4, 1)
        rgb = (rgb * hillshade[..., None]).clip(0, 255).astype('uint8')
        rgb[~valid] = [245, 245, 245]
        Image.fromarray(rgb).save(output / 'surface.png')
    with (output / 'cloud-preview.csv').open('w') as stream:
        pipeline = {'pipeline': [str(output / 'pointcloud.laz'), {'type': 'filters.decimation', 'step': 25},
                                 {'type': 'writers.text', 'filename': str(output / 'cloud-preview.csv'),
                                  'order': 'X,Y,Z,Red,Green,Blue', 'keep_unspecified': False}]}
    subprocess.run([PDAL, 'pipeline', '--stdin'], input=json.dumps(pipeline), text=True, check=True)
    points = np.genfromtxt(output / 'cloud-preview.csv', delimiter=',', names=True)
    x, y, z = points['X'], points['Y'], points['Z']
    u, v = (x - x.mean()) - (y - y.mean()), 0.45 * ((x - x.mean()) + (y - y.mean())) - 2 * (z - z.mean())
    scale = min(1250 / max(np.ptp(u), 1), 900 / max(np.ptp(v), 1))
    cols, rows = ((u - u.min()) * scale + 30).astype(int), ((v - v.min()) * scale + 30).astype(int)
    canvas = np.full((int(rows.max()) + 31, int(cols.max()) + 31, 3), 245, dtype='uint8')
    colors = np.stack([points[c] for c in ['Red', 'Green', 'Blue']], axis=1)
    if colors.max() > 255:
        colors = colors / 256
    order = np.argsort(z)
    canvas[rows[order], cols[order]] = colors[order].clip(0, 255).astype('uint8')
    Image.fromarray(canvas).save(output / 'pointcloud.png')
    (output / 'cloud-preview.csv').unlink()
    return {'sampledRealPoints': len(points), 'surfacePercentilesMeters': [float(lo), float(hi)],
            'pointCloudView': 'Oblique projection of measured reconstruction points; decimation step 25'}


def validate(output, require_parallel=False):
    source = read(DATA / 'source.json')
    partition = read(output / 'split.json')
    require(partition['photographs'] == len(source['files']) == 77, 'Photograph count mismatch')
    require(len(partition['sharedPhotos']) >= 5, 'No overlap between submodels')
    require(read(output / 'align.json')['submodelsAligned'] == 2, 'Both reconstructions must align')
    reconstructed = set().union(*(set(read(output / f'reconstruct-{i}.json')['shots']) for i in range(2)))
    require(reconstructed == {item['name'] for item in source['files']}, 'Some source photos were not reconstructed')
    overlaps = {}
    for prefix in ['reconstruct', 'process']:
        pair = [read(output / f'{prefix}-{i}.json') for i in range(2)]
        overlaps[prefix] = max(0, min(p['finishedEpoch'] for p in pair) - max(p['startedEpoch'] for p in pair))
        if require_parallel:
            require(overlaps[prefix] > 0, 'Worker activities did not overlap: ' + prefix)
    stats = {name: raster_stats(output / name) for name in ['orthophoto.tif', 'surface.tif']}
    require(stats['orthophoto.tif']['crs'] == stats['surface.tif']['crs'], 'Merged CRS mismatch')
    require(stats['surface.tif']['range'][1] > stats['surface.tif']['range'][0], 'Flat or empty surface')
    cloud = point_summary(output / 'pointcloud.laz')
    require(cloud['num_points'] == sum(read(output / 'merge.json')['inputPointCounts']), 'Incomplete merged cloud')
    for name in ['orthophoto.png', 'surface.png', 'pointcloud.png']:
        with Image.open(output / name) as image:
            require(min(image.size) > 50, 'Invalid preview')
            image.verify()
    artifacts = ['orthophoto.tif', 'surface.tif', 'pointcloud.laz', 'orthophoto.png', 'surface.png', 'pointcloud.png']
    return {'status': 'success', 'sourceCommit': source['commit'], 'photographs': 77, 'mergedSubmodels': 2,
            'workerOverlapSeconds': overlaps, 'rasters': stats, 'pointCount': cloud['num_points'],
            'sha256': {name: digest(output / name) for name in artifacts}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        write(output / 'validation.json', validate(output, require_parallel=True))
        print('Validated real ODM products and overlapping reconstruction/processing activities')
        return
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir()
    started = time.time()
    if args.stage.startswith('reconstruct-'):
        value = reconstruct(output, int(args.stage[-1]))
    elif args.stage.startswith('process-'):
        value = process(output, int(args.stage[-1]))
    else:
        value = {'split': split, 'align': align, 'merge': merge, 'previews': previews,
                 'validate': lambda path: validate(path, require_parallel=True)}[args.stage](output)
    finished = time.time()
    value.update(stage=args.stage, startedEpoch=started, finishedEpoch=finished,
                 startedAt=datetime.fromtimestamp(started, timezone.utc).isoformat(),
                 durationSeconds=finished - started)
    write(output / ('validation.json' if args.stage == 'validate' else args.stage + '.json'), value)
    if args.stage == 'validate':
        final = output / 'results'
        final.mkdir()
        names = list(value['sha256']) + ['split.json', 'reconstruct-0.json', 'reconstruct-1.json',
                'align.json', 'process-0.json', 'process-1.json', 'merge.json', 'previews.json', 'validation.json']
        for name in names:
            shutil.copyfile(output / name, final / name)
    print(f'Completed native ODM stage {args.stage} in {finished - started:.3f}s')


if __name__ == '__main__':
    main()
