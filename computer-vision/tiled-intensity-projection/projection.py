"""Project geometric synthetic volumes with deterministic depth tie-breaking."""

from dataclasses import dataclass
from itertools import product

import numpy as np

BLOCK = 16
REFERENCE = (64, 128, 128)
PARTIAL = (61, 123, 115)
LARGE = (96, 160, 160)
SHAPES = {"standard": REFERENCE, "partial": PARTIAL, "large": LARGE}


@dataclass(frozen=True)
class Tile:
    start: tuple[int, int, int]

    def slices(self, shape):
        return tuple(slice(start, min(start + BLOCK, extent))
                     for start, extent in zip(self.start, shape, strict=True))


def tiles(shape):
    return [Tile(start) for start in product(*(range(0, extent, BLOCK) for extent in shape))]


def voxels(region):
    """Generate integer voxels in global coordinates without reading a shared file."""
    z, y, x = np.ogrid[region]
    patterned_background = -30 - ((13 * x + 17 * y + 29 * z) % 13)
    sphere = (z - 29)**2 + (y - 42)**2 + (x - 34)**2 < 16**2
    marker = ((z == 12) | (z == 43)) & ((y - 78)**2 + (x - 71)**2 <= 29**2)
    second_marker = (z == 54) & ((y - 84)**2 + (x - 93)**2 <= 13**2)
    return np.where(marker, 240, np.where(second_marker, 180,
                    np.where(sphere, 60 + z, patterned_background))).astype(np.int16)


def project(tile, shape):
    region = tile.slices(shape)
    block = voxels(region)
    depth = (block.argmax(axis=0) + tile.start[0]).astype(np.int32)
    return block.max(axis=0), depth


def combine(shape, results):
    expected = set(tiles(shape))
    seen = set()
    intensity = np.full(shape[1:], np.iinfo(np.int16).min, dtype=np.int16)
    depth = np.full(shape[1:], shape[0], dtype=np.int32)
    for tile, (local_intensity, local_depth) in results:
        if tile not in expected or tile in seen:
            raise ValueError(f"Unexpected or duplicated tile: {tile}")
        seen.add(tile)
        depth_slice, *projection_slices = tile.slices(shape)
        crop = tuple(projection_slices)
        current_i = intensity[crop]
        current_z = depth[crop]
        if (local_intensity.shape != current_i.shape or local_intensity.dtype != np.int16
                or local_depth.shape != current_z.shape or local_depth.dtype != np.int32
                or np.any(local_depth < depth_slice.start) or np.any(local_depth >= depth_slice.stop)):
            raise ValueError(f"Invalid projection data for tile: {tile}")
        replace = (local_intensity > current_i) | ((local_intensity == current_i)
                                                   & (local_depth < current_z))
        np.copyto(current_i, local_intensity, where=replace)
        np.copyto(current_z, local_depth, where=replace)
    if seen != expected:
        raise ValueError(f"Missing {len(expected - seen)} tiles")
    return intensity, depth
