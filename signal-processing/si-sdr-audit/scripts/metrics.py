"""Independent synthetic tests for SNR, SI-SDR, and SD-SDR."""

import argparse
import json
from math import log10
from pathlib import Path

import numpy as np

TOLERANCE = 1e-6
SAMPLE_RATE = 16_000
FREQUENCIES = np.arange(200, 1601, 200)


def power(signal):
    return float(np.dot(signal, signal))


def decibels(numerator, denominator):
    if numerator == 0:
        return "undefined" if denominator == 0 else "-inf"
    if denominator == 0:
        return "+inf"
    return 10 * log10(numerator / denominator)


def scores(target, estimate):
    signal = power(target)
    if signal == 0:
        return dict.fromkeys(("snr", "si_sdr", "sd_sdr"), "undefined")
    projected = float(np.dot(estimate, target)) / signal * target
    error = power(estimate - target)
    return {
        "snr": decibels(signal, error),
        "si_sdr": decibels(power(projected), power(estimate - projected)),
        "sd_sdr": decibels(power(projected), error),
    }


def gain_sweep():
    target = np.array([1.0, 0.0])
    mixture = np.array([1.0, 1.0])
    rows = []
    for gain in (0.25, 0.5, 1.0, 2.0, 4.0):
        measured = scores(target, gain * mixture)
        denominator = (gain - 1)**2 + gain**2
        expected = {
            "snr": -10 * log10(denominator),
            "si_sdr": 0.0,
            "sd_sdr": 10 * log10(gain**2 / denominator),
        }
        for key, value in expected.items():
            if abs(measured[key] - value) > TOLERANCE:
                raise ValueError(f"{key} mismatch at gain {gain}")
        rows.append({"gain": gain, **measured, "expected": expected})
    endpoints = {
        "silent_target": scores(np.zeros_like(target), mixture),
        "zero_estimate": scores(target, np.zeros_like(target)),
        "exact_match": scores(target, target),
    }
    return {"rows": rows, "endpoints": endpoints}


def spectral_sweep():
    time = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    components = np.sin(2 * np.pi * FREQUENCIES[:, None] * time)
    target = components.sum(axis=0)
    spectrum = np.fft.rfft(target, norm="ortho")
    if not np.allclose(components @ components.T, (SAMPLE_RATE / 2) * np.eye(len(FREQUENCIES)),
                       rtol=0, atol=1e-7):
        raise ValueError("Components must have equal energy and be orthogonal")
    rows = [{"deleted": 0, "retained_fraction": 1.0, **scores(target, target)}]
    previous = float("inf")
    for deleted in range(1, len(FREQUENCIES)):
        filtered = spectrum.copy()
        filtered[FREQUENCIES[-deleted:]] = 0
        estimate = np.fft.irfft(filtered, n=SAMPLE_RATE, norm="ortho")
        fraction = power(estimate) / power(target)
        if not np.isclose(fraction, 1 - deleted / len(FREQUENCIES), rtol=0, atol=1e-12):
            raise ValueError(f"Unexpected retained energy after deleting {deleted} bins")
        expected = 10 * log10(fraction / (1 - fraction))
        measured = scores(target, estimate)
        if abs(measured["si_sdr"] - expected) > TOLERANCE or measured["si_sdr"] >= previous:
            raise ValueError(f"Invalid SI-SDR after deleting {deleted} bins")
        for gain in (0.5, 2.0):
            if abs(scores(target, gain * estimate)["si_sdr"] - expected) > TOLERANCE:
                raise ValueError(f"SI-SDR is not invariant at gain {gain}")
        previous = measured["si_sdr"]
        rows.append({"deleted": deleted, "retained_fraction": fraction,
                     **measured, "expected_si_sdr": expected})
    return {"rows": rows, "frequencies_hz": FREQUENCIES.tolist(), "sample_rate_hz": SAMPLE_RATE}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", choices=("gain", "spectral"))
    args = parser.parse_args()
    result = gain_sweep() if args.branch == "gain" else spectral_sweep()
    Path(f"{args.branch}.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
