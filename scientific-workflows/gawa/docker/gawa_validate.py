"""Validate the produced catalog and render a measured-result preview."""
import argparse
import hashlib
import json
from pathlib import Path


def validate(folder):
    import numpy as np
    from astropy.table import Table
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    config = json.loads((folder / 'gawa.cfg').read_text())
    ids = json.loads((folder / 'tile-manifest.json').read_text())
    tables = []
    for tile_id in ids:
        path = folder / 'tiles' / f'tile_{tile_id:03d}' / config['out_paths']['gawa']['results'] / 'tile_info.fits'
        tables.append(Table.read(str(path)))
    catalog = Table.read(str(folder / 'clusters.fits'))
    keys = config['gawa_cfg']['clkeys']
    ra = np.asarray(catalog[keys['key_ra']], dtype=float)
    dec = np.asarray(catalog[keys['key_dec']], dtype=float)
    snr = np.asarray(catalog[keys['key_snr']], dtype=float)
    if not len(catalog) or not np.isfinite(np.concatenate([ra, dec, snr])).all():
        raise RuntimeError('Empty catalog or nonfinite coordinates/SNR')
    if not ((ra >= 0) & (ra < 360) & (dec >= -90) & (dec <= 90)).all():
        raise RuntimeError('Invalid equatorial coordinates')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    scatter = axes[0].scatter(ra, dec, c=snr, cmap='viridis', s=35, edgecolors='black', linewidths=.3)
    axes[0].set(xlabel='Right ascension (degrees)', ylabel='Declination (degrees)', title='GAWA candidate detections')
    axes[0].invert_xaxis()
    fig.colorbar(scatter, ax=axes[0], label='Signal-to-noise ratio')
    axes[1].hist(snr, bins=min(20, max(3, len(catalog))), color='#444444', edgecolor='white')
    axes[1].set(xlabel='Signal-to-noise ratio', ylabel='Candidate count', title=f'{len(catalog)} candidates across {len(ids)} tiles')
    fig.suptitle('MOCK_DES reference data — measured GAWA output')
    fig.tight_layout()
    fig.savefig(str(folder / 'catalog-preview.png'), dpi=160)
    plt.close(fig)
    summary = {'validation': 'passed', 'tilesExpected': len(ids), 'tilesCompleted': len(tables), 'candidateCount': len(catalog), 'catalogColumns': list(catalog.colnames), 'snrRange': [float(snr.min()), float(snr.max())], 'raRange': [float(ra.min()), float(ra.max())], 'decRange': [float(dec.min()), float(dec.max())], 'catalogSha256': hashlib.sha256((folder / 'clusters.fits').read_bytes()).hexdigest(), 'note': 'Structural and numeric checks only; candidates are not confirmed astronomical objects. Completeness and purity were not measured.'}
    catalog.write(str(folder / 'clusters.csv'), format='ascii.csv', overwrite=True)
    (folder / 'validation.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    validate(parser.parse_args().folder)
