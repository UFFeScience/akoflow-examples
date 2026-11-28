"""Record tile errors and aggregate comparable seam and I/O statistics."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from gaussian import FILTERS, GRID, SHAPES, cases, convolve, core, filter_tile, image, kernel, seam_distances
from render import render

COLUMNS = ("image", "filter", "tile", "radius", "halo", "seam_distance", "pixels",
           "absolute_error_sum", "max_absolute_error", "input_pixels")


def filename(i, f, t):
    return f"tile-{i:02d}-{f:02d}-{t:02d}.csv"


def tile_rows(i, f, t):
    source = image(i)
    sigma, radius = FILTERS[f]
    weights = kernel(sigma, radius)
    bounds = core(source.shape, t)
    top, bottom, left, right = bounds
    reference = convolve(source, weights)[top:bottom, left:right]
    distance = seam_distances(source.shape, bounds)
    for halo in (0, radius // 3, radius):
        actual, read = filter_tile(source, weights, bounds, halo)
        errors = abs(actual - reference)
        if halo == radius and np.max(errors) > 1e-14:
            raise ValueError("The full-radius halo changed the convolution")
        for offset in np.unique(distance):
            values = errors[distance == offset]
            yield (i, f, t, radius, halo, int(offset), values.size,
                   float(values.sum()), float(values.max()), read)


def aggregate(source, output):
    groups = defaultdict(lambda: [0, 0.0, 0.0])
    inventory = defaultdict(lambda: [0, 0])
    for i, f, t in cases():
        radius = FILTERS[f][1]
        top, bottom, left, right = core(SHAPES[i], t)
        distances, counts = np.unique(seam_distances(SHAPES[i], (top, bottom, left, right)), return_counts=True)
        expected = {(halo, int(offset)): int(n) for halo in (0, radius // 3, radius)
                    for offset, n in zip(distances, counts, strict=True)}
        tile_reads = {}
        with (source / filename(i, f, t)).open(newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise ValueError("Unexpected tile CSV columns")
            for row in reader:
                halo, offset, pixels, read = (int(row[k]) for k in
                                              ("halo", "seam_distance", "pixels", "input_pixels"))
                error_sum = float(row["absolute_error_sum"])
                maximum = float(row["max_absolute_error"])
                if (tuple(int(row[k]) for k in ("image", "filter", "tile", "radius")) != (i, f, t, radius)
                        or expected.pop((halo, offset), None) != pixels
                        or not 0 <= maximum <= error_sum <= pixels * maximum + 1e-12
                        or (halo == radius and maximum > 1e-14)):
                    raise ValueError(f"Invalid tile evidence for {(i, f, t)}")
                height, width = SHAPES[i]
                patch_area = ((min(height, bottom + halo) - max(0, top - halo))
                              * (min(width, right + halo) - max(0, left - halo)))
                if read != patch_area:
                    raise ValueError("Incorrect input pixel count")
                tile_reads[halo] = read
                cell = groups[f, halo, offset]
                cell[0] += pixels
                cell[1] += error_sum
                cell[2] = max(cell[2], maximum)
        if expected:
            raise ValueError("Missing seam distances or halo cases")
        for halo, read in tile_reads.items():
            cell = inventory[i, f, halo]
            cell[0] += (bottom - top) * (right - left)
            cell[1] += read

    with (output / "seam-errors.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("filter", "halo", "seam_distance", "pixels", "mean_absolute_error", "max_absolute_error"))
        for (f, halo, offset), (count, total, peak) in sorted(groups.items()):
            writer.writerow((f, halo, offset, count, total / count, peak))
    with (output / "halo-io.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("image", "filter", "halo", "output_pixels", "input_pixels", "duplicated_pixels"))
        for (i, f, halo), (count, read) in sorted(inventory.items()):
            height, width = SHAPES[i]
            if count != height * width:
                raise ValueError("Tile cores do not cover the image exactly")
            writer.writerow((i, f, halo, count, read, read - count))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    tile = commands.add_parser("tile")
    tile.add_argument("image", type=int, choices=range(len(SHAPES)))
    tile.add_argument("filter", type=int, choices=range(len(FILTERS)))
    tile.add_argument("tile", type=int, choices=range(GRID**2))
    tile.add_argument("out", type=Path)
    reduction = commands.add_parser("aggregate")
    reduction.add_argument("source", type=Path)
    reduction.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.action == "tile":
        with (args.out / filename(args.image, args.filter, args.tile)).open("w", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(COLUMNS)
            writer.writerows(tile_rows(args.image, args.filter, args.tile))
    else:
        aggregate(args.source, args.out)
        render(args.out)
