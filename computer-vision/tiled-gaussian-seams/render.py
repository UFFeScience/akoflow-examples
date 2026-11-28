"""Render fixed-scale error maps for successive Gaussian input margins."""

import numpy as np
from PIL import Image, ImageDraw

from gaussian import FILTERS, GRID, convolve, core, filter_tile, image, kernel


def error_map(source, weights, reference, halo):
    errors = np.empty_like(source)
    for tile in range(GRID**2):
        bounds = core(source.shape, tile)
        top, bottom, left, right = bounds
        local, _ = filter_tile(source, weights, bounds, halo)
        errors[top:bottom, left:right] = abs(local - reference[top:bottom, left:right])
    return errors


def panel(errors, limit, size):
    fraction = np.sqrt(np.clip(errors / limit, 0, 1))
    colors = np.stack((12 + 238 * fraction, 23 + 144 * fraction, 42 + 9 * fraction), axis=-1)
    tile = Image.fromarray(colors.astype(np.uint8)).resize(size, Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(tile)
    height, width = errors.shape
    for index in range(1, GRID):
        y = (index * height // GRID) * size[1] // height
        x = (index * width // GRID) * size[0] // width
        for offset in range(0, max(size), 8):
            if offset < size[0]:
                draw.line((offset, y, min(offset + 2, size[0] - 1), y), fill="#8795a9")
            if offset < size[1]:
                draw.line((x, offset, x, min(offset + 2, size[1] - 1)), fill="#8795a9")
    return tile


def render(output):
    source = image(1)
    sigma, radius = FILTERS[2]
    weights = kernel(sigma, radius)
    reference = convolve(source, weights)
    maps = [error_map(source, weights, reference, halo) for halo in range(radius + 1)]
    limit = max(float(errors.max()) for errors in maps)
    if limit <= 0 or maps[-1].max() > 1e-14:
        raise ValueError("The seam visualization requires a positive control and an exact reconstruction")
    subtitle = f"Absolute error 0 to {limit:.3f} (square-root scale). Dotted lines mark tile boundaries."
    color = "#f3f6fa"
    background = "#172131"
    figure = Image.new("RGB", (757, 308), background)
    draw = ImageDraw.Draw(figure)
    draw.text((16, 15), f"Gaussian filtering by tile   |   sigma {sigma:g}, radius {radius} pixels", fill=color)
    for index, halo in enumerate((0, radius // 3, radius)):
        x = 16 + 245 * index
        draw.text((x, 47), f"Input margin: {halo} px", fill=color)
        figure.paste(panel(maps[halo], limit, (230, 208)), (x, 68))
    draw.text((16, 285), subtitle, fill=color)
    figure.save(output / "gaussian-seam-errors.png")

    frames = []
    for halo, errors in enumerate(maps):
        frame = Image.new("RGB", (413, 419), background)
        draw = ImageDraw.Draw(frame)
        draw.text((16, 15), f"Input margin: {halo:2d} px  |  Maximum error: {float(errors.max()):.4f}", fill=color)
        draw.text((16, 36), f"Fixed scale from 0 to {limit:.3f}. Gaussian radius: {radius} px.", fill=color)
        frame.paste(panel(errors, limit, (381, 352)), (16, 53))
        frames.append(frame)
    frames[0].save(output / "gaussian-halo-sweep.gif", save_all=True,
                   append_images=frames[1:], duration=[240] * radius + [1000], loop=0)
