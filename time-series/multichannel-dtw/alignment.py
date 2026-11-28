"""Compare common and independent dynamic time warping paths."""

from itertools import product

import numpy as np

STRATEGIES = ("common", "independent")
SHIFTS = (0, 2, 4, 6, 8, 10, 12, 14)
CASES = tuple(product(range(16), SHIFTS, STRATEGIES))


def loss(a, b):
    return (a[:, None] - b[None, :]) ** 2


def warp(local):
    """Minimize fixed-endpoint path cost, preferring diagonal steps in ties."""
    rows, columns = local.shape
    cost = np.full((rows + 1, columns + 1), np.inf)
    trace = np.zeros((rows + 1, columns + 1), dtype=np.uint8)
    cost[0, 0] = 0.0
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            choices = (cost[i-1, j-1], cost[i-1, j], cost[i, j-1])
            direction = min(range(3), key=choices.__getitem__)
            cost[i, j] = choices[direction] + local[i-1, j-1]
            trace[i, j] = direction
    path = []
    i, j = rows, columns
    while i and j:
        path.append((i-1,j-1))
        direction = trace[i,j]
        i -= direction != 2
        j -= direction != 1
    if i or j:
        raise ValueError("Path did not reach the initial endpoint")
    path.reverse()
    return float(cost[-1,-1]), path


def signals(seed, shift, length=96, joint=False):
    rng=np.random.default_rng(seed)
    first=rng.integers(length//3-4,length//3+5)
    second=rng.integers(2*length//3-4,2*length//3+5)
    anchors=np.array([first,second])
    shifted=anchors+np.array([shift,shift if joint else -shift])
    width=rng.uniform(3,6,size=2)
    grid=np.arange(length)[:,None]
    a=np.exp(-0.5*((grid-anchors)/width)**2)
    b=np.exp(-0.5*((grid-shifted)/width)**2)
    return a,b,anchors,shifted


def channel_losses(a,b):
    return [loss(a[:,channel],b[:,channel]) for channel in range(a.shape[1])]


def solve(a,b,strategy):
    local=channel_losses(a,b)
    if strategy=="common":
        common_cost,path=warp(np.sum(local,axis=0))
        return common_cost,[path]*len(local),local[0].size
    if strategy=="independent":
        solutions=[warp(matrix) for matrix in local]
        return sum(cost for cost,_ in solutions),[path for _,path in solutions],sum(m.size for m in local)
    raise ValueError(f"Unknown strategy: {strategy}")
