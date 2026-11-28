"""Integrate a homogeneous soil column through a constant four-hour storm."""

from math import log1p
from time import perf_counter

STORM_HOURS = 4
INTERVALS_PER_HOUR = 30
SUBSTEPS = 64
MASS_TOLERANCE_MM = 1e-8


def ponding_time(rain, conductivity, suction_deficit):
    if rain <= conductivity:
        return float("inf")
    return conductivity * suction_deficit / (rain * (rain - conductivity))


def advance(depth, dt, conductivity, suction_deficit):
    def rate(value):
        return conductivity * (1 + suction_deficit / value)

    first = rate(depth)
    second = rate(depth + dt * first / 2)
    third = rate(depth + dt * second / 2)
    fourth = rate(depth + dt * third)
    return depth + dt * (first + 2 * second + 2 * third + fourth) / 6


def sample_column(rain, conductivity, suction_deficit, phase_time=None):
    onset = ponding_time(rain, conductivity, suction_deficit)
    depth = previous_time = 0.0
    yield 0.0, 0.0, 0.0
    for index in range(1, STORM_HOURS * INTERVALS_PER_HOUR + 1):
        start_clock = perf_counter() if phase_time is not None else 0.0
        end = index / INTERVALS_PER_HOUR
        rainfall = rain * end
        if end <= onset:
            depth = rainfall
        else:
            start = max(onset, previous_time)
            if start == onset:
                depth = rain * onset
            dt = (end - start) / SUBSTEPS
            for _ in range(SUBSTEPS):
                depth = advance(depth, dt, conductivity, suction_deficit)
        if not 0 <= depth <= rainfall + MASS_TOLERANCE_MM:
            raise ArithmeticError(f"Infiltration exceeded rainfall at hour {end}")
        runoff = max(0.0, rainfall - depth)
        if phase_time is not None:
            phase = "rainfall_only" if end <= onset else "post_ponding"
            phase_time[phase] += perf_counter() - start_clock
        yield end, depth, runoff
        previous_time = end


def bracketed_depth(rain, conductivity, suction_deficit, end):
    onset = ponding_time(rain, conductivity, suction_deficit)
    if end <= onset:
        return rain * end
    initial = rain * onset
    low, high = initial, rain * end
    for _ in range(60):
        estimate = (low + high) / 2
        change = estimate - initial
        elapsed = (change - suction_deficit * log1p(change / (initial + suction_deficit))) / conductivity
        if elapsed < end - onset:
            low = estimate
        else:
            high = estimate
    return (low + high) / 2
