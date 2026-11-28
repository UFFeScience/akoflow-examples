"""Write per-tile CSVs and visualize the verified projections."""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from projection import SHAPES, Tile, combine, project, tiles, voxels

FIELDS = ("y", "x", "maximum", "depth")


def filename(tile):
    return "tile-{:03d}-{:03d}-{:03d}.csv".format(*tile.start)


def write_csv(path, origin, intensity, depth):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        for y, x in np.ndindex(intensity.shape):
            writer.writerow((origin[0] + y, origin[1] + x, intensity[y, x], depth[y, x]))


def read_tile(path, tile, shape):
    _, y_region, x_region = tile.slices(shape)
    size = (y_region.stop - y_region.start, x_region.stop - x_region.start)
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Unexpected schema in {path.name}")
        rows = [tuple(int(row[field]) for field in FIELDS) for row in reader]
    expected = [(y_region.start + y, x_region.start + x) for y, x in np.ndindex(size)]
    if [row[:2] for row in rows] != expected:
        raise ValueError(f"Unexpected coordinates in {path.name}")
    if any(not -32768 <= value <= 32767 or not 0 <= depth < shape[0]
           for _, _, value, depth in rows):
        raise ValueError(f"Invalid value or depth in {path.name}")
    intensity = np.array([row[2] for row in rows], dtype=np.int16).reshape(size)
    depth = np.array([row[3] for row in rows], dtype=np.int32).reshape(size)
    return intensity, depth


def panel(intensity, depth, depth_extent):
    scaled = np.clip((intensity.astype(np.float64) + 42) / 282, 0, 1)
    distance = depth / max(depth_extent - 1, 1)
    colors = np.stack([distance, 1 - abs(2 * distance - 1), 1 - distance], axis=-1)
    layers = [Image.fromarray(np.uint8(scaled * 255)).convert("RGB"),
              Image.fromarray(np.uint8(colors * 255))]
    width, height = layers[0].size
    composite = Image.new("RGB", (6 * width + 30, 3 * height + 55), "#171c26")
    draw = ImageDraw.Draw(composite)
    for i, (layer, title) in enumerate(zip(layers, ("Maximum intensity", "Earliest depth"), strict=True)):
        x = 10 + i * (3 * width + 10)
        composite.paste(layer.resize((3 * width, 3 * height), Image.Resampling.NEAREST), (x, 28))
        draw.text((x, 9), title, fill="white")
    return composite


def aggregate(shape, source, output):
    partition = tiles(shape)
    if {path.name for path in source.glob("tile-*.csv")} != {filename(tile) for tile in partition}:
        raise ValueError("Tile CSV inventory does not cover the volume")
    results = [(tile, read_tile(source / filename(tile), tile, shape)) for tile in reversed(partition)]
    intensity, depth = combine(shape, results)
    volume = voxels(tuple(slice(0, length) for length in shape))
    np.testing.assert_array_equal(intensity, volume.max(axis=0))
    np.testing.assert_array_equal(depth, volume.argmax(axis=0))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "projection.csv", (0, 0), intensity, depth)
    panel(intensity, depth, shape[0]).save(output / "projection.png")
    frames = []
    for end in (*range(4, shape[0], 4), shape[0]):
        prefix = volume[:end]
        frame = panel(prefix.max(axis=0), prefix.argmax(axis=0), shape[0])
        ImageDraw.Draw(frame).text((10, frame.height - 19), f"Depth scan: {end}/{shape[0]} slices",
                                   fill="white")
        frames.append(frame)
    frames[0].save(output / "depth-scan.gif", save_all=True, append_images=frames[1:],
                   duration=180, loop=0, optimize=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shape", choices=SHAPES)
    commands = parser.add_subparsers(dest="command", required=True)
    block = commands.add_parser("tile")
    block.add_argument("start", nargs=3, type=int)
    block.add_argument("output", type=Path)
    reducer = commands.add_parser("aggregate")
    reducer.add_argument("source", type=Path)
    reducer.add_argument("output", type=Path)
    args = parser.parse_args()
    shape = SHAPES[args.shape]
    if args.command == "tile":
        tile = Tile(tuple(args.start))
        if tile not in tiles(shape):
            parser.error("invalid tile origin")
        write_csv(args.output / filename(tile), tile.start[1:], *project(tile, shape))
    else:
        aggregate(shape, args.source, args.output)
