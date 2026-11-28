"""Synthetic Gaussian filtering with explicit tile ownership and margins."""

from itertools import product

import numpy as np

SHAPES = ((128, 128), (125, 119), (111, 133), (107, 141),
          (129, 127), (116, 123), (135, 121), (117, 131))
FILTERS = ((1.25, 5), (2.0, 8), (3.0, 12), (4.0, 16))
GRID = 4


def cases():
    return product(range(len(SHAPES)), range(len(FILTERS)), range(GRID**2))


def image(index):
    height, width = SHAPES[index]
    y, x = np.indices((height, width), dtype=np.float64)
    cx, cy = width // 2, height // 2
    stripes = 0.20 * np.sin((x + y) * (0.12 + 0.02 * index))
    step = 0.45 * (x >= cx + (y - cy) / 3)
    disk = 0.38 * ((x - cx)**2 + (y - cy)**2 <= (22 + index)**2)
    samples = 0.2 + stripes + step + disk
    samples[cy - 1:cy + 1, cx - 1:cx + 1] += 1.2
    samples[0, 0] += 0.8
    samples[-1, -1] += 0.6
    return samples


def kernel(sigma, radius):
    offsets = np.arange(-radius, radius + 1, dtype=np.float64)
    weights = np.exp(-0.5 * (offsets / sigma)**2)
    return weights / weights.sum()


def convolve(source, weights):
    radius = len(weights) // 2
    padded = np.pad(source, ((0, 0), (radius, radius)), mode="edge")
    horizontal = sum(weight * padded[:, offset:offset + source.shape[1]]
                     for offset, weight in enumerate(weights))
    padded = np.pad(horizontal, ((radius, radius), (0, 0)), mode="edge")
    return sum(weight * padded[offset:offset + source.shape[0], :]
               for offset, weight in enumerate(weights))


def core(shape, tile):
    row, column = divmod(tile, GRID)
    height, width = shape
    return (row * height // GRID, (row + 1) * height // GRID,
            column * width // GRID, (column + 1) * width // GRID)


def filter_tile(source, weights, bounds, halo):
    top, bottom, left, right = bounds
    h, w = source.shape
    y0, y1 = max(top - halo, 0), min(bottom + halo, h)
    x0, x1 = max(left - halo, 0), min(right + halo, w)
    patch = source[y0:y1, x0:x1]
    filtered = convolve(patch, weights)
    return filtered[top-y0:bottom-y0, left-x0:right-x0], patch.size


def seam_distances(shape, bounds):
    top, bottom, left, right = bounds
    y, x = np.mgrid[top:bottom, left:right]
    distances = np.full_like(y, max(shape))
    for edge, position, distance in (
        (top, 0, y - top), (bottom, shape[0], bottom - 1 - y),
        (left, 0, x - left), (right, shape[1], right - 1 - x),
    ):
        if edge != position:
            np.minimum(distances, distance, out=distances)
    return distances
