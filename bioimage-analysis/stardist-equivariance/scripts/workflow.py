import argparse
import csv
import hashlib
import json
import os
import random
import shutil
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from csbdeep.utils import normalize
from matplotlib.colors import ListedColormap
from skimage.segmentation import find_boundaries
from stardist.data import test_image_nuclei_2d
from stardist.matching import matching, relabel_sequential
from stardist.models import StarDist2D

SEED = 20261122
MODEL_DIR = Path("/opt/stardist/models/paper/2D_dsb2018")
TRANSFORMS = {
    "identity": (False, 0), "r90": (False, 1), "r180": (False, 2),
    "r270": (False, 3), "reflect": (True, 0),
    "reflect-r90": (True, 1), "reflect-r180": (True, 2),
    "reflect-r270": (True, 3),
}
EXPECTED_HASHES = {
    "image": "f9ccc1571b92c861ff87e28463068b43f61bd47357ed0503f711e5cd1eb97750",
    "mask": "59ad5e820b7982ca9d13e946fa6e7f64e2714899e00a2ae6c69aa79aad53d46f",
    "config": "03f973864d937d126447fa20ed9d1a0dded63e1da60f21ba8f99ca76c6f12eb7",
    "thresholds": "6d91889ebbccc3e6cb6b04eac8ba1b803507df2cf75bac3700f76d152f566e68",
    "weights": "784816ab04540be9d5069bea3de1183e1843c1a4a91abbec0b373e31f037fd39",
}


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def serializable(stats):
    return {key: value.item() if isinstance(value, np.generic) else value
            for key, value in stats._asdict().items()}


def configure():
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.experimental.enable_op_determinism()


def transform(array, reflected, rotations):
    return np.rot90(np.fliplr(array) if reflected else array, rotations)


def inverse_transform(array, reflected, rotations):
    value = np.rot90(array, -rotations)
    return np.fliplr(value) if reflected else value


def stage_prepare(root):
    image_path = Path("/opt/stardist/stardist/data/images/img2d.tif")
    mask_path = Path("/opt/stardist/stardist/data/images/mask2d.tif")
    paths = {
        "image": image_path, "mask": mask_path,
        "config": MODEL_DIR / "config.json",
        "thresholds": MODEL_DIR / "thresholds.json",
        "weights": MODEL_DIR / "weights_last.h5",
    }
    actual = {name: sha256_file(path) for name, path in paths.items()}
    if actual != EXPECTED_HASHES:
        raise RuntimeError(f"asset hash mismatch: {actual}")
    image, truth = test_image_nuclei_2d(return_mask=True)
    report = {
        "source_revision": "e80c6de700693bc228ed3c9ba1dc19c3785667ee",
        "source_license": "BSD-3-Clause",
        "data_source": "2018 Data Science Bowl / BBBC038",
        "data_license": "CC0-1.0",
        "sha256": actual,
        "image": {"shape": list(image.shape), "dtype": str(image.dtype),
                  "minimum": int(image.min()), "maximum": int(image.max())},
        "truth": {"shape": list(truth.shape), "dtype": str(truth.dtype),
                  "objects": int(np.unique(truth[truth != 0]).size)},
        "seed": SEED,
        "normalization": {"pmin": 1.0, "pmax": 99.8, "clip": False},
        "thresholds": {"probability": 0.4178193636640508, "nms": 0.5},
        "transforms": list(TRANSFORMS),
    }
    dump(root / "input-manifest.json", report)


def stage_predict(root, name):
    configure()
    reflected, rotations = TRANSFORMS[name]
    image, truth = test_image_nuclei_2d(return_mask=True)
    normalized = normalize(image, 1, 99.8, clip=False).astype(np.float32)
    model = StarDist2D(None, name="2D_dsb2018", basedir=str(MODEL_DIR.parent))
    labels, _ = model.predict_instances(
        transform(normalized, reflected, rotations),
        prob_thresh=0.4178193636640508, nms_thresh=0.5,
        n_tiles=None, show_tile_progress=False)
    labels = inverse_transform(labels, reflected, rotations)
    labels = relabel_sequential(labels)[0].astype(np.uint16, copy=False)
    branch = root / "branches" / name
    branch.mkdir(parents=True, exist_ok=True)
    np.save(branch / "labels.npy", labels, allow_pickle=False)
    report = {
        "name": name, "reflected": reflected, "rotations_ccw": rotations,
        "shape": list(labels.shape), "objects": int(labels.max()),
        "label_sha256": hashlib.sha256(labels.tobytes(order="C")).hexdigest(),
        "ground_truth": {str(threshold): serializable(matching(truth, labels, threshold))
                         for threshold in (0.5, 0.75)},
    }
    dump(branch / "metrics.json", report)


def stage_aggregate(root):
    records = []
    labels = {}
    for name in TRANSFORMS:
        branch = root / "branches" / name
        records.append(json.loads((branch / "metrics.json").read_text()))
        labels[name] = np.load(branch / "labels.npy", allow_pickle=False)
    identity = labels["identity"]
    for record in records:
        candidate = labels[record["name"]]
        record["identity_consistency"] = serializable(matching(identity, candidate, 0.5))
        record["pixel_disagreement_fraction"] = float(
            np.mean((identity > 0) != (candidate > 0)))
    base = next(record for record in records if record["name"] == "identity")
    checks = []
    for record in records:
        name = record["name"]
        checks.extend([
            {"name": f"{name}-shape", "passed": record["shape"] == [512, 512]},
            {"name": f"{name}-count", "passed": abs(record["objects"] - base["objects"]) <= 2},
            {"name": f"{name}-identity-f1", "passed": record["identity_consistency"]["f1"] >= 0.95},
            {"name": f"{name}-gt50-f1", "passed": record["ground_truth"]["0.5"]["f1"] >= base["ground_truth"]["0.5"]["f1"] - 0.03},
            {"name": f"{name}-gt50-pq", "passed": record["ground_truth"]["0.5"]["panoptic_quality"] >= base["ground_truth"]["0.5"]["panoptic_quality"] - 0.03},
            {"name": f"{name}-gt75-f1", "passed": record["ground_truth"]["0.75"]["f1"] >= base["ground_truth"]["0.75"]["f1"] - 0.05},
        ])
    report = {"branches": records, "checks": checks,
              "passed": len(records) == 8 and all(c["passed"] for c in checks),
              "worst_identity_consistency": min(r["identity_consistency"]["f1"] for r in records)}
    dump(root / "aggregate.json", report)
    with (root / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["transform", "objects", "gt_f1_050", "gt_pq_050", "gt_f1_075", "identity_f1_050", "pixel_disagreement_fraction"])
        for r in records:
            writer.writerow([r["name"], r["objects"], r["ground_truth"]["0.5"]["f1"],
                             r["ground_truth"]["0.5"]["panoptic_quality"],
                             r["ground_truth"]["0.75"]["f1"],
                             r["identity_consistency"]["f1"], r["pixel_disagreement_fraction"]])
    if not report["passed"]:
        raise RuntimeError("scientific acceptance gates failed")


def boundary_overlay(image, truth, labels):
    base = normalize(image, 1, 99.8, clip=True)
    rgb = np.repeat(base[..., None], 3, axis=-1)
    rgb[find_boundaries(truth, mode="outer")] = (0.15, 0.85, 0.3)
    rgb[find_boundaries(labels, mode="outer")] = (1.0, 0.2, 0.15)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def stage_render(root):
    image, truth = test_image_nuclei_2d(return_mask=True)
    labels = {name: np.load(root / "branches" / name / "labels.npy", allow_pickle=False)
              for name in TRANSFORMS}
    fig, axes = plt.subplots(2, 4, figsize=(12, 6), constrained_layout=True)
    frames = []
    for ax, name in zip(axes.flat, TRANSFORMS):
        frame = boundary_overlay(image, truth, labels[name])
        frames.append(frame)
        ax.imshow(frame)
        ax.set_title(name)
        ax.axis("off")
    fig.suptitle("StarDist D4 robustness — green: target, red: prediction")
    fig.savefig(root / "stardist-d4-overlays.png", dpi=160)
    plt.close(fig)
    identity = labels["identity"] > 0
    disagreement = np.stack([(labels[name] > 0) != identity for name in TRANSFORMS]).sum(axis=0)
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    image_plot = ax.imshow(disagreement, cmap="magma", vmin=0, vmax=7)
    fig.colorbar(image_plot, ax=ax, label="Disagreeing transforms")
    ax.set_title("Foreground disagreement against identity")
    ax.axis("off")
    fig.savefig(root / "stardist-disagreement.png", dpi=160)
    plt.close(fig)
    imageio.mimsave(root / "stardist-d4-animation.gif", frames, duration=0.75, loop=0)
    dump(root / "gallery.json", {
        "files": ["stardist-d4-overlays.png", "stardist-disagreement.png", "stardist-d4-animation.gif"],
        "animation_frames": len(frames), "frame_shape": list(frames[0].shape)})


def stage_validate(root):
    aggregate = json.loads((root / "aggregate.json").read_text())
    gallery = json.loads((root / "gallery.json").read_text())
    files = [root / name for name in gallery["files"]] + [root / "metrics.csv", root / "aggregate.json"]
    checks = {
        "aggregate_passed": aggregate["passed"],
        "eight_branches": len(aggregate["branches"]) == 8,
        "all_files_nonempty": all(path.is_file() and path.stat().st_size > 0 for path in files),
        "animation_eight_frames": len(imageio.mimread(root / "stardist-d4-animation.gif")) == 8,
        "finite_metrics": all(np.isfinite(r["ground_truth"][t][metric])
                              for r in aggregate["branches"] for t in ("0.5", "0.75")
                              for metric in ("f1", "panoptic_quality")),
    }
    retained = root / "results"
    retained.mkdir(exist_ok=True)
    for path in files + [root / "input-manifest.json", root / "gallery.json"]:
        shutil.copyfile(path, retained / path.name)
    shutil.copytree(root / "branches", retained / "branches", dirs_exist_ok=True)
    retained_files = sorted(path for path in retained.rglob("*") if path.is_file())
    report = {"passed": all(checks.values()), "checks": checks,
              "artifacts": {str(path.relative_to(root)): {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in retained_files}}
    dump(root / "validation.json", report)
    if not report["passed"]:
        raise RuntimeError("validation failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "predict", "aggregate", "render", "validate"])
    parser.add_argument("--output", default=".")
    parser.add_argument("--transform", choices=list(TRANSFORMS))
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.stage == "prepare": stage_prepare(root)
    elif args.stage == "predict":
        if args.transform is None: parser.error("--transform is required")
        stage_predict(root, args.transform)
    elif args.stage == "aggregate": stage_aggregate(root)
    elif args.stage == "render": stage_render(root)
    else: stage_validate(root)


if __name__ == "__main__":
    main()
