"""Compare mean and coordinatewise median on paired synthetic marker tracks."""

import numpy as np

MARKERS = np.array([[-12, -8], [-4, -10], [5, -9], [13, -6],
                    [11, 8], [4, 12], [-6, 11], [-13, 5]], dtype=float)
OCCLUSIONS = (0, 2, 4, 8)
OUTLIERS = (0.0, 2.0, 5.0, 10.0)
CASES = [(seed, hidden, bias) for seed in range(16)
         for hidden in OCCLUSIONS for bias in OUTLIERS]


def offsets(angles):
    cosine, sine = np.cos(angles), np.sin(angles)
    x, y = MARKERS.T
    return np.stack((cosine[:, None] * x - sine[:, None] * y,
                     sine[:, None] * x + cosine[:, None] * y), axis=-1)


def estimate(observations, orientations, visible):
    """Use known per-frame orientation to convert sightings into center candidates."""
    count = visible.sum(axis=1)
    mean = np.full((len(observations), 2), np.nan)
    median = mean.copy()
    candidates = observations - offsets(orientations)
    for frame in np.flatnonzero(count):
        selected = candidates[frame, visible[frame]]
        mean[frame] = selected.mean(axis=0)
        median[frame] = np.median(selected, axis=0)
    return count, mean, median


def scenario(case, frames=96):
    seed, hidden, bias = CASES[case]
    rng = np.random.default_rng(seed)
    phase = np.linspace(0, 2 * np.pi, frames, endpoint=False)
    center = np.column_stack((20 * np.cos(phase), 15 * np.sin(2 * phase + seed / 8)))
    angles = phase + seed / 16
    observations = center[:, None, :] + offsets(angles)
    observations += rng.normal(0, 0.25, size=observations.shape)
    choices = rng.random((frames, len(MARKERS))).argsort(axis=1)
    visible = np.ones((frames, len(MARKERS)), dtype=bool)
    if hidden:
        np.put_along_axis(visible, choices[:, :hidden], False, axis=1)
    if hidden < len(MARKERS):
        observations[np.arange(frames), choices[:, hidden], 0] += bias
    return center, angles, observations, visible
