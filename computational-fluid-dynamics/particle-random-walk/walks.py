"""Seeded independent grid walks with additive integer moments."""

from collections import Counter

import numpy as np

MOVES = np.array(((1,0),(-1,0),(0,1),(0,-1)),dtype=np.int64)
SCENARIOS = {
    "isotropic":(5,5,5,5),
    "anisotropic":(8,8,2,2),
    "low-drift":(11,5,2,2),
    "high-drift":(14,2,2,2),
}
BATCHES = 64
PARTICLES = 256


def walk(weights, seed, steps, particles=PARTICLES):
    rng=np.random.default_rng(seed)
    drawn=rng.integers(0,sum(weights),size=(particles,steps))
    directions=np.searchsorted(np.cumsum(weights),drawn,side="right")
    return MOVES[directions].sum(axis=1)


def batch(scenario, index, steps):
    if not 0<=index<BATCHES:
        raise ValueError("Batch index outside the manifest")
    ordinal=tuple(SCENARIOS).index(scenario)
    seed=672_000+ordinal*BATCHES+index
    return Counter(map(tuple,walk(SCENARIOS[scenario],seed,steps).tolist()))


def validate(histogram, steps, expected_particles):
    if sum(histogram.values())!=expected_particles:
        raise ValueError("Particle count does not match the manifest")
    for (x,y),count in histogram.items():
        if count<=0 or abs(x)+abs(y)>steps or (x+y-steps)%2:
            raise ValueError("Impossible endpoint or invalid histogram count")


def sufficient_statistics(histogram):
    return (
        sum(histogram.values()),
        sum(count*x for (x,y),count in histogram.items()),
        sum(count*y for (x,y),count in histogram.items()),
        sum(count*x*x for (x,y),count in histogram.items()),
        sum(count*y*y for (x,y),count in histogram.items()),
        sum(count*x*y for (x,y),count in histogram.items()),
    )


def empirical(histogram):
    count,sx,sy,sxx,syy,sxy=sufficient_statistics(histogram)
    mean=np.array((sx,sy))/count
    second=np.array(((sxx,sxy),(sxy,syy)))/count
    return mean,second-np.outer(mean,mean)


def theoretical(weights, steps):
    probabilities=np.array(weights)/sum(weights)
    mean=probabilities@MOVES
    centered=MOVES-mean
    return steps*mean,steps*((centered.T*probabilities)@centered)


def estimate_checks(histogram, scenario, steps):
    """Compare with sampling error bounds fixed before execution."""
    count=BATCHES*PARTICLES
    validate(histogram,steps,count)
    mean,covariance=empirical(histogram)
    expected_mean,expected_covariance=theoretical(SCENARIOS[scenario],steps)
    mean_limit=6*np.sqrt(expected_covariance.diagonal()/count)
    sigma=np.sqrt(expected_covariance.diagonal())
    covariance_limit=0.06*np.outer(sigma,sigma)
    if (np.any(abs(mean-expected_mean)>mean_limit)
            or np.any(abs(covariance-expected_covariance)>covariance_limit)):
        raise ValueError(f"Observed moments exceed mean/covariance tolerance for {scenario}")
    return mean,covariance,expected_mean,expected_covariance
