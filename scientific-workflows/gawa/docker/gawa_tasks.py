"""Tile-level GAWA CLI: prepare, process one tile, and consolidate."""
import argparse
import json
import os
from pathlib import Path

ROOT = Path('/data-akoflow/gawa-tiles-run')


def load():
    return json.loads((ROOT / 'results/gawa.cfg').read_text())


def tiles(params):
    from lib.utils import read_FitsCat
    return read_FitsCat(str(Path(params['out_paths']['workdir']) / params['admin']['tiling']['tiles_filename']))


def prepare(count, config):
    import shutil
    import yaml
    from lib.utils import create_mosaic_footprint, update_hpx_parameters, hpx_split_survey
    from lib.gawa import update_filters_in_params, compute_dslices
    from lib.tile_tasks import compute_cmd_masks_job

    if (ROOT / 'results').exists():
        raise RuntimeError('Existing results: use a fresh volume for each experiment.')
    if ROOT == Path('/data') or Path('/data') in ROOT.parents:
        raise ValueError('Workspace must be outside /data')
    shutil.copytree('/data', ROOT, dirs_exist_ok=True)
    os.chdir(ROOT)
    params = yaml.safe_load(Path(config).read_text())
    out = ROOT / 'results'
    out.mkdir()
    (out / 'tiles').mkdir()
    params['out_paths']['workdir'] = str(out)
    survey = params['survey']
    if not params['input_data_structure'][survey]['footprint_hpx_mosaic']:
        create_mosaic_footprint(params['footprint'][survey], str(out / 'footprint'))
        params['footprint'][survey]['mosaic']['dir'] = str(out / 'footprint')
    params = update_hpx_parameters(params, survey, params['input_data_structure'])
    params = update_filters_in_params(params, survey, params['ref_bfilter'], params['ref_rfilter'], params['ref_color'])
    (out / 'gawa.cfg').write_text(json.dumps(params))
    hpx_split_survey(params['footprint'][survey], params['admin']['tiling'], str(out / params['admin']['tiling']['tiles_filename']))
    ids = sorted(int(tile['id']) for tile in tiles(params))
    if ids != list(range(count)):
        raise RuntimeError(f'Generated tiles {ids}; workflow expects IDs 0..{count - 1}. Regenerate workflow for this dataset.')
    (out / 'tile-manifest.json').write_text(json.dumps(ids))
    compute_dslices(params['isochrone_masks'][survey], params['gawa_cfg']['dslices'], str(out))
    compute_cmd_masks_job(params['isochrone_masks'][survey], params['out_paths'], params['gawa_cfg'])
    print(f'Prepared {len(ids)} independent tiles', flush=True)


def process(tile_id):
    from lib.tile_tasks import run_gawa_tile_job
    params = load()
    selected = [tile for tile in tiles(params) if int(tile['id']) == tile_id]
    if len(selected) != 1:
        raise RuntimeError(f'Expected exactly one tile with id={tile_id}')
    run_gawa_tile_job((selected[0], str(ROOT / 'results/gawa.cfg')))
    info = ROOT / 'results/tiles' / f'tile_{tile_id:03d}' / params['out_paths']['gawa']['results'] / 'tile_info.fits'
    if not info.is_file():
        raise RuntimeError(f'Tile {tile_id} did not produce completion metadata')


def merge():
    from lib.gawa import tiles_with_clusters, gawa_concatenate
    params = load()
    all_tiles = tiles(params)
    for tile in all_tiles:
        info = ROOT / 'results/tiles' / f"tile_{int(tile['id']):03d}" / params['out_paths']['gawa']['results'] / 'tile_info.fits'
        if not info.is_file():
            raise RuntimeError(f'Missing tile completion metadata: {info}')
    effective = tiles_with_clusters(params['out_paths'], all_tiles)
    if len(effective) == 0:
        raise RuntimeError('All tiles completed with no clusters. No final catalog was generated; inspect tile_info.fits.')
    result = gawa_concatenate(effective, params['gawa_cfg'], params['out_paths'])
    result.write(str(ROOT / 'results/clusters.fits'), overwrite=True)
    print(f'Consolidated {len(all_tiles)} tiles into results/clusters.fits', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'tile', 'merge'])
    parser.add_argument('--count', type=int, default=14)
    parser.add_argument('--id', type=int)
    parser.add_argument('--workspace', type=Path, default=ROOT)
    parser.add_argument('--config', type=Path, default=Path('/data/gawa.cfg'))
    args = parser.parse_args()
    ROOT = args.workspace.resolve()
    args.config = args.config.resolve()
    os.environ['GAWA_ROOT'] = str(ROOT)
    if args.action != 'prepare':
        os.chdir(ROOT)
    if args.action == 'prepare':
        prepare(args.count, args.config)
    elif args.action == 'tile':
        if args.id is None:
            parser.error('tile requires --id')
        process(args.id)
    else:
        merge()
