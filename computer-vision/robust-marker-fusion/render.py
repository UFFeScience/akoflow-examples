"""Render trajectory and error panels from a verified marker-fusion scenario."""


import numpy as np
from PIL import Image, ImageDraw

COLORS = {"truth": "#283d5c", "mean": "#a63834", "median": "#117856"}


def values(rows, keys):
    return np.array([[float(row[key]) if row[key] else np.nan for key in keys]
                     for row in rows])


def coordinates(points, bounds, box):
    min_x, max_x, min_y, max_y = bounds
    left, top, right, bottom = box
    return [(left + (x-min_x)/(max_x-min_x)*(right-left),
             bottom - (y-min_y)/(max_y-min_y)*(bottom-top)) for x,y in points]


def frame(rows, end):
    image = Image.new("RGB", (920, 450), "#f7fafc")
    draw = ImageDraw.Draw(image)
    draw.text((32, 23), "Marker fusion under occlusion and biased observations", fill="#162335")
    draw.text((32, 50), f"Frame {end} / {len(rows)} · {rows[end-1]['visible_count']} markers visible",
              fill="#394b60")
    trajectory = {method: values(rows, (f"{method}_x", f"{method}_y")) for method in COLORS}
    errors = {method: values(rows, (f"{method}_error",))[:, 0] for method in ("mean", "median")}
    boxes = ((48, 118, 437, 392), (497, 118, 884, 392))
    for box, title in zip(boxes, ("Planar trajectory", "Position error by frame"), strict=True):
        draw.rectangle(box, outline="#8492a6")
        draw.text((box[0], 92), title, fill="#162335")
    coordinates_all = np.concatenate(list(trajectory.values()))
    low = np.nanmin(coordinates_all, axis=0) - 2
    high = np.nanmax(coordinates_all, axis=0) + 2
    spatial = (low[0], high[0], low[1], high[1])
    error_extent = max(float(np.nanmax(np.concatenate(list(errors.values())))), 0.1)
    for method, series in trajectory.items():
        points = coordinates(series[:end], spatial, boxes[0])
        if len(points) > 1:
            draw.line(points, fill=COLORS[method], width=2)
        x, y = points[-1]
        draw.ellipse((x-3, y-3, x+3, y+3), fill=COLORS[method])
    for method, series in errors.items():
        points = coordinates(zip(range(end), series[:end]), (0, len(rows)-1, 0, error_extent), boxes[1])
        if len(points) > 1:
            draw.line(points, fill=COLORS[method], width=2)
    draw.text((497, 399), "0", fill="#394b60")
    draw.text((845, 399), str(len(rows)-1), fill="#394b60")
    draw.text((497, 101), f"{error_extent:.2f} units", fill="#394b60", anchor="lb")
    for index, (method, color) in enumerate(COLORS.items()):
        draw.text((48 + 104*index, 415), method.title(), fill=color)
    return image


def render(rows, output):
    output.mkdir(parents=True, exist_ok=True)
    frame(rows, len(rows)).save(output / "trajectory-errors.png")
    stops = np.unique(np.linspace(1, len(rows), 24, dtype=int))
    images = [frame(rows, end) for end in stops]
    images[0].save(output / "trajectory-errors.gif", save_all=True, append_images=images[1:],
                   duration=120, loop=0, optimize=False)
