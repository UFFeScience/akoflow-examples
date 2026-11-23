#!/usr/bin/env python3
"""Render the measured BioCLIP taxonomic-rank traversal as a deterministic GIF."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image


RANKS = ("kingdom", "phylum", "class", "order", "family", "genus", "species")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    values = [100 * report["metrics"]["rank_accuracy"][rank] for rank in RANKS]
    top1 = 100 * report["metrics"]["top1"]
    published = 100 * report["acceptance"]["published_top1"]
    args.output.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    with tempfile.TemporaryDirectory(prefix="bioclip-ranks-") as temporary:
        temporary = Path(temporary)
        for current, rank in enumerate(RANKS):
            fig, axis = plt.subplots(figsize=(9.6, 5.4), constrained_layout=True)
            colors = ["#111111" if index == current else "#b9b9b9" for index in range(len(RANKS))]
            bars = axis.barh([item.title() for item in RANKS], values, color=colors)
            for index, bar in enumerate(bars):
                if index <= current:
                    axis.text(values[index] + 1.0, bar.get_y() + bar.get_height() / 2,
                              f"{values[index]:.2f}%", va="center", fontsize=10)
            axis.axvline(published, color="#777777", linestyle="--", linewidth=1.5,
                         label=f"Published species top-1: {published:.2f}%")
            axis.set_xlim(0, 107)
            axis.invert_yaxis()
            axis.set_xlabel("Top-1 agreement with the target taxonomy")
            axis.set_title(f"Taxonomic resolution: {rank.title()} · measured agreement {values[current]:.2f}%")
            axis.legend(loc="lower right", frameon=False)
            fig.suptitle(
                "BioCLIP Rare Species · 11,983 images · 400 held-out species\n"
                f"Frozen CPU/FP32 result; reproduced species top-1 {top1:.2f}%",
                fontsize=13,
            )
            frame_path = temporary / f"rank-{current:02d}.png"
            fig.savefig(frame_path, dpi=100, metadata={"Software": "AkôFlow Community Explorer"})
            plt.close(fig)
            with Image.open(frame_path) as image:
                frames.append(image.convert("P", palette=Image.Palette.ADAPTIVE))

        frames[0].save(
            args.output,
            save_all=True,
            append_images=frames[1:],
            duration=900,
            loop=0,
            optimize=False,
            disposal=2,
        )

    with Image.open(args.output) as animation:
        frame_count = animation.n_frames
        width, height = animation.size
        signature = args.output.read_bytes()[:6].decode("ascii")
    if frame_count != len(RANKS) or signature not in {"GIF87a", "GIF89a"}:
        raise RuntimeError("animation validation failed")

    evidence = {
        "artifact": args.output.name,
        "artifact_sha256": sha256(args.output),
        "source": str(args.input.as_posix()),
        "source_sha256": sha256(args.input),
        "dimensions": [width, height],
        "frames": frame_count,
        "frame_duration_ms": 900,
        "evolving_dimension": "Measured top-1 agreement while traversing taxonomic ranks from kingdom to species.",
        "contains_source_photographs": False,
        "metrics": {rank: report["metrics"]["rank_accuracy"][rank] for rank in RANKS},
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
