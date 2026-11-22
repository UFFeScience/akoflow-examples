import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from src.open_clip import create_model_and_transforms

SEED = 0
SHARDS = 8
RANKS = ("kingdom", "phylum", "class", "order", "family", "genus", "species")
DATASET_REVISION = "59689732c07819c9472b6a2ef5b9da9b473f7c27"
MODEL_REVISION = "799f1d9eb01abf82c9353de5951967755315725f"
SOURCE_REVISION = "7555b4e00583687b128a12df2e0b70e6a7bc1522"
PUBLISHED_TOP1 = 0.3809
CATALOG = Path("/opt/bioclip/assets/rarespecies-catalog.csv")
LICENSES = Path("/opt/bioclip/assets/licenses.csv")
CHECKPOINT = Path("/opt/bioclip/model/open_clip_pytorch_model.bin")
CLASSIFIER = Path("/opt/bioclip/assets/classifier.pt")
EXPECTED = {
    "catalog": "96c458bd580caf5df4743c639eb38490e62eddef44b92be519d6771bdc2bf8fa",
    "licenses": "8cd23a637cc8c6c9175b652b9cfdd695060b27d077d1677fd154c992eb09c754",
    "checkpoint": "e380384f0c30d425d8c6c40f24471f9dd497fbdfa734a89c461a94aee95f0ef4",
    "config": "86d418d7046fa9212ab70eb7cb3deeef02be46f39d7948bad5dc7649f8277208",
    "tokenizer": "d8b124290bc4bcd18cd3f72747f525e2a1d8c266cf3089e52da38ee417564ac5",
    "classifier": "7ca30fa6c485f8f4a4ba9113db4fb272ad839927bd7f5e649d412f33a1bd2f42",
    "prompt_order": "f5754d551759fc79d78820819b67ea9e58ec7a51b529fa564698d4e6a00bcf71",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_rows():
    with CATALOG.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_licenses():
    with LICENSES.open(newline="", encoding="utf-8") as handle:
        return {row["rarespecies_id"]: row for row in csv.DictReader(handle)}


def prompt(row):
    value = " ".join(row[rank].capitalize() for rank in RANKS)
    return value + (" with common name " + row["common"] if row["common"] else "")


def class_manifest(rows):
    output, seen = [], set()
    for row in rows:
        value = prompt(row)
        if value not in seen:
            seen.add(value)
            output.append({"prompt": value, **{rank: row[rank] for rank in RANKS}})
    return output


def relative_path(row):
    directory = "-".join(row[rank] for rank in RANKS)
    filename = f"{row['eol_content_id']}_{row['eol_page_id']}_eol-full-size-copy.jpg"
    return Path(directory) / filename


def configure(threads):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(threads)


def stage_prepare(root):
    rows, licenses = load_rows(), load_licenses()
    classes = class_manifest(rows)
    prompt_hash = hashlib.sha256(("\n".join(c["prompt"] for c in classes) + "\n").encode()).hexdigest()
    hashes = {
        "catalog": sha256_file(CATALOG),
        "licenses": sha256_file(LICENSES),
        "checkpoint": sha256_file(CHECKPOINT),
        "config": sha256_file("/opt/bioclip/model/open_clip_config.json"),
        "tokenizer": sha256_file("/opt/bioclip/model/tokenizer.json"),
        "classifier": sha256_file(CLASSIFIER),
        "prompt_order": prompt_hash,
    }
    if hashes != EXPECTED:
        raise RuntimeError(f"asset hash mismatch: {hashes}")
    if len(rows) != 11983 or len(licenses) != 11983 or len(classes) != 400:
        raise RuntimeError("unexpected benchmark cardinality")
    counts = Counter(row["license_name"] for row in licenses.values())
    shard_counts = Counter(index % SHARDS for index in range(len(rows)))
    dump(root / "input-manifest.json", {
        "source_revision": SOURCE_REVISION,
        "model_revision": MODEL_REVISION,
        "dataset_revision": DATASET_REVISION,
        "rows": len(rows), "classes": len(classes), "templates_per_class": 81,
        "shards": SHARDS, "shard_counts": dict(shard_counts), "hashes": hashes,
        "licenses": dict(sorted(counts.items())),
        "image_policy": "Transient download; no benchmark photographs retained or published.",
        "precision": "fp32", "seed": SEED, "device": "cpu",
    })
    dump(root / "classes.json", classes)


def download_one(row, license_row, directory):
    relative = relative_path(row)
    destination = directory / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    url_path = "dataset/" + relative.as_posix()
    official_url = ("https://huggingface.co/datasets/imageomics/rare-species/resolve/" +
                    DATASET_REVISION + "/" + urllib.parse.quote(url_path, safe="/"))
    mirror = os.environ.get("BIOCLIP_DATA_MIRROR", "").rstrip("/")
    urls = ([mirror + "/" + urllib.parse.quote(relative.as_posix(), safe="/")] if mirror else []) + [official_url]
    for attempt in range(8):
        last_error = None
        for url in urls:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "akoflow-bioclip-reproduction/1.0"})
                with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
                actual = md5_file(destination)
                if actual != license_row["md5"].lower():
                    raise ValueError(f"MD5 {actual} != {license_row['md5']}")
                with Image.open(destination) as image:
                    image.verify()
                return destination
            except Exception as error:
                last_error = error
                destination.unlink(missing_ok=True)
        if attempt == 7:
            raise last_error
        time.sleep(min(60, 2 ** attempt))


class Images(Dataset):
    def __init__(self, records, transform):
        self.records, self.transform = records, transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        row_index, row, path, target = self.records[index]
        with Image.open(path) as image:
            value = self.transform(image.convert("RGB"))
        return value, target, row_index


def stage_infer(root, shard):
    if not 0 <= shard < SHARDS:
        raise ValueError(f"shard must be in [0,{SHARDS})")
    configure(2)
    rows, licenses = load_rows(), load_licenses()
    classes = class_manifest(rows)
    class_to_index = {entry["prompt"]: index for index, entry in enumerate(classes)}
    selected = [(index, row) for index, row in enumerate(rows) if index % SHARDS == shard]
    branch = root / "shards" / f"shard-{shard:02d}"
    branch.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix=f"bioclip-shard-{shard:02d}-") as temporary:
        directory = Path(temporary)
        paths = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(download_one, row, licenses[row["rarespecies_id"]], directory): index
                       for index, row in selected}
            for future in as_completed(futures):
                paths[futures[future]] = future.result()
        model, _, preprocess = create_model_and_transforms(
            "ViT-B-16", pretrained=str(CHECKPOINT), precision="fp32", device="cpu", output_dict=True)
        model.eval()
        classifier = torch.load(CLASSIFIER, map_location="cpu", weights_only=True)
        records = [(index, row, paths[index], class_to_index[prompt(row)]) for index, row in selected]
        # Keep tensors in the main process so the workflow also runs under the
        # Docker default 64 MiB /dev/shm used by the AkôFlow local driver.
        loader = DataLoader(Images(records, preprocess), batch_size=32, shuffle=False, num_workers=0)
        output = []
        with torch.inference_mode():
            for images, targets, indices in loader:
                features = F.normalize(model.encode_image(images), dim=-1)
                logits = model.logit_scale.exp() * features @ classifier
                values, candidates = logits.topk(5, dim=1, largest=True, sorted=True)
                for target, top, scores, row_index in zip(
                        targets.tolist(), candidates.tolist(), values.tolist(), indices.tolist()):
                    output.append({
                        "row_index": row_index, "rarespecies_id": rows[row_index]["rarespecies_id"],
                        "target_class": target, "predicted_class": top[0],
                        "top5_classes": " ".join(map(str, top)),
                        "top5_logits": " ".join(f"{score:.8f}" for score in scores),
                    })
    output.sort(key=lambda record: record["row_index"])
    with (branch / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader(); writer.writerows(output)
    dump(branch / "summary.json", {
        "shard": shard, "rows": len(output), "minimum_row": output[0]["row_index"],
        "maximum_row": output[-1]["row_index"], "elapsed_seconds": time.time() - started,
        "predictions_sha256": sha256_file(branch / "predictions.csv"),
    })


def stage_aggregate(root):
    rows, classes = load_rows(), class_manifest(load_rows())
    predictions = []
    summaries = []
    for shard in range(SHARDS):
        branch = root / "shards" / f"shard-{shard:02d}"
        summaries.append(json.loads((branch / "summary.json").read_text()))
        with (branch / "predictions.csv").open(newline="", encoding="utf-8") as handle:
            predictions.extend(csv.DictReader(handle))
    predictions.sort(key=lambda record: int(record["row_index"]))
    indices = [int(record["row_index"]) for record in predictions]
    if indices != list(range(len(rows))):
        raise RuntimeError("shard output is not an exact partition of the catalog")
    top = Counter(); rank_correct = Counter(); per_class = defaultdict(lambda: [0, 0])
    for record in predictions:
        target, predicted = int(record["target_class"]), int(record["predicted_class"])
        candidates = [int(value) for value in record["top5_classes"].split()]
        for k in (1, 3, 5):
            top[k] += int(target in candidates[:k])
        for rank in RANKS:
            rank_correct[rank] += int(classes[target][rank] == classes[predicted][rank])
        per_class[target][0] += int(target == predicted); per_class[target][1] += 1
    class_accuracy = [per_class[index][0] / per_class[index][1] for index in range(len(classes))]
    metrics = {
        "top1": top[1] / len(rows), "top3": top[3] / len(rows), "top5": top[5] / len(rows),
        "macro_top1": sum(class_accuracy) / len(class_accuracy),
        "rank_accuracy": {rank: rank_correct[rank] / len(rows) for rank in RANKS},
        "min_class_top1": min(class_accuracy), "max_class_top1": max(class_accuracy),
    }
    report = {
        "metrics": metrics, "published_top1": PUBLISHED_TOP1, "absolute_tolerance": 0.01,
        "absolute_error": abs(metrics["top1"] - PUBLISHED_TOP1),
        "passed": abs(metrics["top1"] - PUBLISHED_TOP1) <= 0.01,
        "rows": len(rows), "classes": len(classes), "shards": summaries,
    }
    dump(root / "aggregate.json", report)
    with (root / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader(); writer.writerows(predictions)
    if not report["passed"]:
        raise RuntimeError("published top-1 acceptance gate failed")


def stage_render(root):
    report = json.loads((root / "aggregate.json").read_text())
    metrics = report["metrics"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    labels = ["Published", "Top-1", "Top-3", "Top-5"]
    values = [PUBLISHED_TOP1, metrics["top1"], metrics["top3"], metrics["top5"]]
    bars = axes[0].bar(labels, np.array(values) * 100, color=["#777777", "#111111", "#555555", "#999999"])
    axes[0].bar_label(bars, fmt="%.2f%%", padding=3)
    axes[0].set_ylim(0, 75); axes[0].set_ylabel("Accuracy"); axes[0].set_title("Rare Species zero-shot reproduction")
    rank_values = [metrics["rank_accuracy"][rank] * 100 for rank in RANKS]
    bars = axes[1].barh([rank.title() for rank in RANKS], rank_values, color="#222222")
    axes[1].bar_label(bars, fmt="%.1f%%", padding=3)
    axes[1].set_xlim(0, 105); axes[1].set_xlabel("Top-1 taxonomic agreement"); axes[1].set_title("Hierarchical error profile")
    fig.suptitle("BioCLIP ViT-B/16 · 11,983 images · 400 held-out species")
    figure = root / "bioclip-rare-species.png"
    fig.savefig(figure, dpi=180); plt.close(fig)
    dump(root / "gallery.json", {
        "files": [figure.name], "contains_source_photographs": False,
        "license_note": "Derived metrics only; mixed-license benchmark images are not republished.",
    })


def stage_validate(root):
    manifest = json.loads((root / "input-manifest.json").read_text())
    aggregate = json.loads((root / "aggregate.json").read_text())
    gallery = json.loads((root / "gallery.json").read_text())
    required = [root / "predictions.csv", root / "aggregate.json", root / gallery["files"][0]]
    checks = {
        "assets_frozen": manifest["hashes"] == EXPECTED,
        "benchmark_complete": aggregate["rows"] == 11983 and aggregate["classes"] == 400,
        "eight_shards": len(aggregate["shards"]) == SHARDS,
        "published_gate": aggregate["passed"],
        "topk_order": aggregate["metrics"]["top1"] <= aggregate["metrics"]["top3"] <= aggregate["metrics"]["top5"],
        "no_source_photographs": not gallery["contains_source_photographs"],
        "outputs_nonempty": all(path.is_file() and path.stat().st_size > 0 for path in required),
    }
    report = {"checks": checks, "passed": all(checks.values()),
              "output_sha256": {path.name: sha256_file(path) for path in required}}
    dump(root / "validation.json", report)
    if not report["passed"]:
        raise RuntimeError(f"validation failed: {checks}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "infer", "aggregate", "render", "validate"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--shard", type=int)
    args = parser.parse_args()
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    if args.stage == "prepare": stage_prepare(root)
    elif args.stage == "infer":
        if args.shard is None: parser.error("infer requires --shard")
        stage_infer(root, args.shard)
    elif args.stage == "aggregate": stage_aggregate(root)
    elif args.stage == "render": stage_render(root)
    else: stage_validate(root)


if __name__ == "__main__":
    main()
