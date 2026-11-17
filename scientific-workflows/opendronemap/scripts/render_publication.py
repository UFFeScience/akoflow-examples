import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description='Render publication animations from verified real ODM observations and products.')
parser.add_argument('--bundle', type=Path, required=True)
args = parser.parse_args()
bundle = args.bundle.resolve()
outputs = bundle / 'outputs'
media = bundle / 'evidence'
report = json.loads((outputs / 'validation.json').read_text())
source = json.loads((bundle / 'data/source.json').read_text())
for name, expected in report['sha256'].items():
    if hashlib.sha256((outputs / name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Native product checksum mismatch: ' + name)
for item in source['files']:
    if hashlib.sha256((bundle / 'data/images' / item['name']).read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit('Original photo checksum mismatch: ' + item['name'])
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
title = ImageFont.truetype(font, 28)
label = ImageFont.truetype(font, 19)
small = ImageFont.truetype(font, 15)
size = (960, 720)
background = (17, 23, 32)


def frame(heading, detail):
    canvas = Image.new('RGB', size, background)
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 18), heading, font=title, fill='white')
    draw.text((30, 58), detail, font=label, fill=(185, 205, 220))
    return canvas


def fit(image):
    image = image.convert('RGB')
    image.thumbnail((900, 550))
    return image


def place(canvas, image):
    image = fit(image)
    canvas.paste(image, ((960 - image.width) // 2, 100 + (550 - image.height) // 2))


def footer(canvas, text):
    ImageDraw.Draw(canvas).text((30, 682), text, font=small, fill=(190, 205, 215))


def save_gif(frames, durations, path):
    atlas = Image.new('RGB', (160 * 8, 120 * ((len(frames) + 7) // 8)), background)
    for index, image in enumerate(frames):
        sample = image.resize((160, 120))
        atlas.paste(sample, ((index % 8) * 160, (index // 8) * 120))
    palette = atlas.quantize(colors=256)
    indexed = [image.quantize(palette=palette, dither=Image.NONE) for image in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, optimize=False, disposal=2)
    with Image.open(path) as image:
        if image.n_frames < 2:
            raise RuntimeError('Animation did not encode multiple frames')
        for i in range(image.n_frames):
            image.seek(i)
            image.load()
        return {'frames': image.n_frames, 'width': image.width, 'height': image.height,
                'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


frames, durations = [], []
hero = frame('OpenDroneMap | real Caliterra results', '77 original photos | two parallel submodels | native geospatial merge')
with Image.open(outputs / 'orthophoto.png') as image:
    place(hero, image)
footer(hero, 'Measured final orthomosaic. The following assembly sequence is an illustrative presentation of real outputs.')
frames.append(hero)
durations.append(1500)
thumbs = []
for item in source['files']:
    with Image.open(bundle / 'data/images' / item['name']) as image:
        thumb = image.convert('RGB')
        thumb.thumbnail((79, 63))
        thumbs.append(thumb.copy())
for count in [11, 22, 33, 44, 55, 66, 77]:
    canvas = frame('OpenDroneMap | Caliterra', '77 real GPS-tagged photographs | frozen CC0 input dataset')
    for i, image in enumerate(thumbs[:count]):
        col, row = i % 11, i // 11
        canvas.paste(image, (31 + col * 82, 130 + row * 72))
    footer(canvas, 'Input thumbnails; this grid is not a geographic map. Animation is a presentation, not execution timing.')
    frames.append(canvas)
    durations.append(230 if count < 77 else 1000)
canvas = frame('Two overlapping submodels', '59 and 65 photographs | 47 shared | real parallel reconstruction and alignment')
with Image.open(outputs / 'pointcloud.png') as image:
    place(canvas, image)
footer(canvas, f"Measured merged cloud: {report['pointCount']:,} points. Preview of the actual computed product.")
frames.append(canvas)
durations.append(1500)
with Image.open(outputs / 'orthophoto.png') as image:
    mosaic = fit(image)
for count in range(1, 43):
    canvas = frame('Native merge | orthomosaic', 'Revealing the final georeferenced mosaic assembled from both real submodels')
    revealed = Image.new('RGB', mosaic.size, background)
    for tile in range(count):
        col, row = tile % 7, tile // 7
        box = (col * mosaic.width // 7, row * mosaic.height // 6,
               (col + 1) * mosaic.width // 7, (row + 1) * mosaic.height // 6)
        revealed.paste(mosaic.crop(box), box[:2])
    canvas.paste(revealed, ((960 - mosaic.width) // 2, 100 + (550 - mosaic.height) // 2))
    footer(canvas, 'Illustrative reveal of the measured final raster; not intermediate reconstruction frames or a timelapse.')
    frames.append(canvas)
    durations.append(90 if count < 42 else 1800)
canvas = frame('Surface elevation | real DSM', 'Computed from the merged cloud; includes vegetation and structures')
with Image.open(outputs / 'surface.png') as image:
    place(canvas, image)
footer(canvas, 'Display colors and hillshade visualize elevation values. Original GeoTIFF and LAZ remain unchanged.')
frames.append(canvas)
durations.append(1600)
assembly = save_gif(frames, durations, media / 'map-assembly.gif')

with tempfile.TemporaryDirectory() as temporary:
    csv = Path(temporary) / 'points.csv'
    pipeline = {'pipeline': [str(outputs / 'pointcloud.laz'), {'type': 'filters.decimation', 'step': 100},
                             {'type': 'writers.text', 'filename': str(csv),
                              'order': 'X,Y,Z,Red,Green,Blue', 'keep_unspecified': False}]}
    subprocess.run(['/code/SuperBuild/install/bin/pdal', 'pipeline', '--stdin'],
                   input=json.dumps(pipeline), text=True, check=True, capture_output=True)
    points = np.genfromtxt(csv, delimiter=',', names=True)
xyz = np.stack([points[c] for c in ['X', 'Y', 'Z']], axis=1)
xyz -= xyz.mean(axis=0)
colors = np.stack([points[c] for c in ['Red', 'Green', 'Blue']], axis=1)
if colors.max() > 255:
    colors /= 256
colors = np.clip(colors, 0, 255).astype('uint8')
scale = min(820 / max(np.ptp(xyz[:, 0]), np.ptp(xyz[:, 1]), 1), 480 / max(np.ptp(xyz[:, 2]), 1)) * 0.7
rotations = []
for angle in np.linspace(0, 2 * np.pi, 36, endpoint=False):
    u = np.cos(angle) * xyz[:, 0] - np.sin(angle) * xyz[:, 1]
    w = np.sin(angle) * xyz[:, 0] + np.cos(angle) * xyz[:, 1]
    v = 0.45 * w - 0.85 * xyz[:, 2]
    depth = 0.85 * w + 0.45 * xyz[:, 2]
    cols, rows = (u * scale + 480).astype(int), (v * scale + 385).astype(int)
    keep = (cols >= 30) & (cols < 929) & (rows >= 105) & (rows < 650)
    order = np.argsort(depth[keep])
    x, y, rgb = cols[keep][order], rows[keep][order], colors[keep][order]
    canvas = frame('Measured point cloud | 360-degree view', f"{report['pointCount']:,} real reconstructed points | display decimation 1:100")
    pixels = np.array(canvas)
    for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        pixels[y + dy, x + dx] = rgb
    canvas = Image.fromarray(pixels)
    footer(canvas, 'Camera rotation of the computed colored points. No new geometry is generated; the full LAZ is downloadable.')
    rotations.append(canvas)
turntable = save_gif(rotations, [110] * len(rotations), media / 'pointcloud-turntable.gif')
provenance = {'nativeRunId': json.loads((media / 'daemon-run.json').read_text())['runId'],
              'sourceDatasetCommit': source['commit'], 'inputProductSHA256': report['sha256'],
              'assemblyMeaning': 'Presentation animation using the original input thumbnails and an illustrative tile reveal of the final real mosaic; not execution footage or measured temporal reconstruction.',
              'turntableMeaning': 'Orthographic camera rotation of decimated actual LAZ points with their measured RGB; no inferred geometry added.',
              'rendererSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'mapAssembly': assembly, 'pointcloudTurntable': turntable}
(media / 'animation-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps({'assembly': assembly, 'turntable': turntable}, indent=2))
