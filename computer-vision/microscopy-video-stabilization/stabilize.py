"""Generate and evaluate one deterministic microscopy stabilization case."""

import argparse
import csv
from itertools import product
from pathlib import Path

import numpy as np

SIZE = 96
FRAMES = 40
RADIUS = 24
AMPLITUDES = (0.0, 0.5, 2.0, 6.0)
REGIMES = ((0.0, 0.0), (0.15, 0.6), (0.35, 1.4))
CASES = tuple(product(range(532, 596), AMPLITUDES, REGIMES))
WINDOW = np.outer(np.hanning(SIZE), np.hanning(SIZE))


def generate(seed, amplitude, regime, periodic=False):
    noise, strength = regime
    rng = np.random.default_rng(seed)
    size = 2 * SIZE
    margin = (size - SIZE) // 2
    if periodic:
        background = np.tile(rng.normal(size=(16, 16)), (size // 16, size // 16))
    else:
        background = rng.normal(size=(size, size))
    freq = np.fft.fftfreq(size)
    spectrum = np.fft.fft2(background) * np.exp(-(freq[:, None] ** 2 + freq**2) / 0.035)
    spectrum /= np.fft.ifft2(spectrum).real.std()
    time = np.arange(FRAMES) / (FRAMES - 1)
    truth = amplitude * np.column_stack((time, np.sin(2 * np.pi * time)))
    yy, xx = np.indices((SIZE, SIZE))
    frames = []
    for dy, dx in truth:
        phase = np.exp(-2j * np.pi * (dy * freq[:, None] + dx * freq))
        frame = np.fft.ifft2(spectrum * phase).real[margin:margin + SIZE, margin:margin + SIZE].copy()
        for y, x in rng.uniform(30, 66, size=(4, 2)):
            frame += strength * np.exp(-((yy - y) ** 2 + (xx - x) ** 2) / 18)
        frames.append(frame + noise * rng.normal(size=frame.shape))
    return np.stack(frames), truth


def window_sum(image, width):
    integral = np.pad(image, ((1, 0), (1, 0))).cumsum(axis=0).cumsum(axis=1)
    return integral[width:, width:] - integral[:-width, width:] - integral[width:, :-width] + integral[:-width, :-width]


def ambiguity_ratio(reference, moving):
    tile = reference[RADIUS:-RADIUS, RADIUS:-RADIUS]
    tile = tile - tile.mean()
    width = tile.shape[0]
    count = tile.size
    if not tile.std():
        return 1.0
    padded = np.zeros_like(moving)
    padded[:width, :width] = tile
    valid = moving.shape[0] - width + 1
    corr = np.fft.ifft2(np.fft.fft2(moving) * np.fft.fft2(padded).conj()).real[:valid, :valid]
    summed = window_sum(moving, width)
    energy = np.maximum(0, window_sum(moving**2, width) - summed**2 / count)
    norm = np.sqrt(energy * np.sum(tile**2))
    scores = np.divide(corr, norm, out=np.full_like(corr, -np.inf), where=norm > 0)
    y, x = np.unravel_index(scores.argmax(), scores.shape)
    peak = scores[y, x]
    if not np.isfinite(peak) or peak <= 0:
        return 1.0
    scores[max(0, y-1):y+2, max(0, x-1):x+2] = -np.inf
    second = scores.max()
    return float(peak / second) if second > 0 else float("inf")


def alignment(reference, moving, phase_only):
    a = np.fft.fft2((reference - reference.mean()) * WINDOW)
    b = np.fft.fft2((moving - moving.mean()) * WINDOW)
    cross = a * b.conj()
    if phase_only:
        mag = np.abs(cross)
        cross = np.divide(cross, mag, out=np.zeros_like(cross), where=mag > mag.max() * 1e-12)
    corr = np.fft.ifft2(cross).real
    y, x = np.unravel_index(corr.argmax(), corr.shape)
    height = corr[y, x]
    offsets = []
    for before, after in ((corr[y-1, x], corr[(y+1) % SIZE, x]),
                          (corr[y, x-1], corr[y, (x+1) % SIZE])):
        curvature = before - 2 * height + after
        offsets.append((before - after) / (2 * curvature) if curvature < 0 else 0.0)
    return (np.array((y, x)) + SIZE // 2) % SIZE - SIZE // 2 + offsets


def evaluate(frames, truth):
    yield 0, "unregistered", "ok", 0.0, 0.0, np.nan, 0.0
    for i in range(1, len(frames)):
        yield i, "unregistered", "ok", 0.0, 0.0, np.nan, np.linalg.norm(truth[i])
    for anchored in (True, False):
        ratios = [ambiguity_ratio(frames[0 if anchored else i-1], frames[i])
                  for i in range(1, len(frames))]
        for phase in (False, True):
            name = ("phase" if phase else "cross") + ("-anchored" if anchored else "-chained")
            total = np.zeros(2)
            yield 0, name, "ok", 0.0, 0.0, np.nan, 0.0
            for i, ratio in enumerate(ratios, 1):
                if ratio <= 1.10:
                    status = "ambiguous"
                    total[:] = np.nan
                elif not anchored and not np.isfinite(total).all():
                    status = "unavailable"
                else:
                    status = "ok"
                    step = alignment(frames[0 if anchored else i-1], frames[i], phase)
                    total = step if anchored else total + step
                yield i, name, status, *total, ratio, np.linalg.norm(total + truth[i])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=int, choices=range(len(CASES)), metavar="CASE")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    frames, truth = generate(*CASES[args.case])
    with args.output.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("frame", "method", "status", "alignment_y", "alignment_x",
                         "peak_ratio", "trajectory_error_px", "truth_y", "truth_x"))
        for row in evaluate(frames, truth):
            writer.writerow((*row, *truth[row[0]]))


if __name__ == "__main__":
    main()
