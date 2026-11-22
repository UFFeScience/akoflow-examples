import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from rdkit import Chem, rdBase
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.metrics import mean_absolute_error

from DeepPurpose import CompoundPred
from DeepPurpose.utils import data_process, generate_config


DATA = Path("/opt/tdc/admet_group/caco2_wang")
MODELS = {"morgan": "Morgan", "rdkit2d": "rdkit_2d_normalized", "cnn": "CNN"}
DISPLAY = {"morgan": "Morgan + MLP", "rdkit2d": "RDKit2D + MLP", "cnn": "CNN"}
REFERENCE = {
    "rdkit2d": {"mean": 0.393, "std": 0.024, "interval": [0.345, 0.441]},
    "cnn": {"mean": 0.446, "std": 0.036, "interval": [0.374, 0.518]},
    "morgan": {"mean": 0.908, "std": 0.060, "interval": [0.788, 1.028]},
}
SEEDS = (1, 2, 3, 4, 5)
EXPECTED = {
    "train_val": "e0965b4a0617a3aa2978ef28794e3467d55655090f282a120355ea575ebed6b2",
    "test": "5380c15b0dd9c11e22d3e3843083362d535dae36062dfee08056d3af4cb444df",
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


def scaffold(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"invalid SMILES: {smiles}")
    return MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)


def official_split(frame, seed):
    groups = defaultdict(set)
    for index, smiles in enumerate(frame.Drug):
        groups[scaffold(smiles)].add(index)
    train_size = int(len(frame) * 0.875)
    val_size = int(len(frame) * 0.125)
    big, small = [], []
    for group in groups.values():
        (big if len(group) > val_size / 2 else small).append(group)
    rng = random.Random(seed)
    rng.shuffle(big)
    rng.shuffle(small)
    train, valid = [], []
    for group in big + small:
        (train if len(train) + len(group) <= train_size else valid).extend(group)
    return frame.iloc[train].reset_index(drop=True), frame.iloc[valid].reset_index(drop=True), train, valid


def index_hash(indices):
    return hashlib.sha256(("\n".join(map(str, indices)) + "\n").encode()).hexdigest()


def stage_prepare(root):
    train_val = pd.read_csv(DATA / "train_val.csv")
    test = pd.read_csv(DATA / "test.csv")
    actual = {"train_val": sha256_file(DATA / "train_val.csv"), "test": sha256_file(DATA / "test.csv")}
    if actual != EXPECTED:
        raise RuntimeError(f"dataset hash mismatch: {actual}")
    combined = pd.concat([train_val.assign(partition="train_val"), test.assign(partition="test")], ignore_index=True)
    invalid = [int(i) for i, value in enumerate(combined.Drug) if Chem.MolFromSmiles(value) is None]
    duplicate_groups = []
    for smiles, group in combined.groupby("Drug", sort=False):
        if len(group) > 1:
            duplicate_groups.append({"smiles": smiles, "rows": [int(i) for i in group.index],
                                     "targets": [float(v) for v in group.Y], "partitions": group.partition.tolist(),
                                     "conflicting_targets": group.Y.nunique() > 1})
    test_scaffolds = {scaffold(value) for value in test.Drug}
    split_records = []
    for seed in SEEDS:
        train, valid, train_idx, valid_idx = official_split(train_val, seed)
        train_scaffolds = {scaffold(value) for value in train.Drug}
        valid_scaffolds = {scaffold(value) for value in valid.Drug}
        split_records.append({"seed": seed, "train_rows": len(train), "valid_rows": len(valid),
                              "train_index_sha256": index_hash(train_idx), "valid_index_sha256": index_hash(valid_idx),
                              "train_valid_overlap": len(train_scaffolds & valid_scaffolds),
                              "train_test_overlap": len(train_scaffolds & test_scaffolds),
                              "valid_test_overlap": len(valid_scaffolds & test_scaffolds)})
    report = {
        "passed": not invalid and len(train_val) == 728 and len(test) == 182 and
                  combined.Drug.nunique() == 906 and all(not set(r["partitions"]) == {"train_val", "test"} for r in duplicate_groups) and
                  all(not record[k] for record in split_records for k in ("train_valid_overlap", "train_test_overlap", "valid_test_overlap")),
        "dataset": {"rows": len(combined), "unique_smiles": int(combined.Drug.nunique()),
                    "train_val_rows": len(train_val), "test_rows": len(test), "target": "log10(Papp in cm/s)",
                    "target_min": float(combined.Y.min()), "target_max": float(combined.Y.max()), "sha256": actual},
        "invalid_smiles": invalid, "duplicate_groups": duplicate_groups,
        "scaffolds": {"test_unique": len(test_scaffolds), "rdkit_version": rdBase.rdkitVersion, "include_chirality": False},
        "splits": split_records,
        "provenance": {"tdc_revision": "c310c35f27e3f506411018ac43d97b8ba23ca652",
                       "deeppurpose_revision": "866be98bad0b11e78d4363589b9ee59b5befa307",
                       "admet_group_dataverse_file_id": 4426004,
                       "admet_group_archive_sha256": "bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1"},
    }
    dump(root / "input-audit.json", report)
    if not report["passed"]:
        raise RuntimeError("input or scaffold audit failed")


def stage_train(root, model_key, seed):
    if not (root / "input-audit.json").is_file():
        raise RuntimeError("prepare artifact is missing")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    train_val = pd.read_csv(DATA / "train_val.csv")
    test_frame = pd.read_csv(DATA / "test.csv")
    train, valid, train_idx, valid_idx = official_split(train_val, seed)
    encoding = MODELS[model_key]
    train_data = data_process(X_drug=train.Drug.values, y=train.Y.values, drug_encoding=encoding, split_method="no_split")
    valid_data = data_process(X_drug=valid.Drug.values, y=valid.Y.values, drug_encoding=encoding, split_method="no_split")
    test_data = data_process(X_drug=test_frame.Drug.values, y=test_frame.Y.values, drug_encoding=encoding, split_method="no_split")
    branch = root / "branches" / model_key / f"seed-{seed}"
    config = generate_config(drug_encoding=encoding, cls_hidden_dims=[512], train_epoch=50,
                             LR=0.001, batch_size=128, result_folder=str(branch / "training"))
    model = CompoundPred.model_initialize(**config)
    model.train(train_data, valid_data, test_data, verbose=False)
    predictions = np.asarray(model.predict(test_data, verbose=False), dtype=np.float64)
    branch.mkdir(parents=True, exist_ok=True)
    np.save(branch / "predictions.npy", predictions, allow_pickle=False)
    torch.save(model.model.state_dict(), branch / "checkpoint.pt")
    raw_mae = float(mean_absolute_error(test_frame.Y, predictions))
    report = {"model": model_key, "display_name": DISPLAY[model_key], "seed": seed,
              "mae": raw_mae, "tdc_rounded_mae": round(raw_mae, 3), "predictions": len(predictions),
              "finite_predictions": bool(np.isfinite(predictions).all()), "train_rows": len(train),
              "valid_rows": len(valid), "test_rows": len(test_frame), "train_index_sha256": index_hash(train_idx),
              "valid_index_sha256": index_hash(valid_idx), "prediction_sha256": sha256_file(branch / "predictions.npy"),
              "checkpoint_sha256": sha256_file(branch / "checkpoint.pt"),
              "configuration": {"encoding": encoding, "epochs": 50, "learning_rate": 0.001,
                                "batch_size": 128, "classifier_hidden": [512], "python_seed": seed,
                                "torch_seed": seed, "numpy_seed": seed, "deterministic_algorithms": True}}
    dump(branch / "metrics.json", report)
    if len(predictions) != 182 or not report["finite_predictions"]:
        raise RuntimeError("prediction completeness failed")


def stage_aggregate(root):
    records = []
    for model_key in MODELS:
        for seed in SEEDS:
            records.append(json.loads((root / "branches" / model_key / f"seed-{seed}" / "metrics.json").read_text()))
    models = {}
    for model_key in MODELS:
        rows = [record for record in records if record["model"] == model_key]
        values = np.array([record["mae"] for record in rows])
        mean, std = float(values.mean()), float(values.std(ddof=0))
        low, high = REFERENCE[model_key]["interval"]
        models[model_key] = {"display_name": DISPLAY[model_key], "seed_mae": values.tolist(), "mean_mae": mean,
                             "population_std": std, "reference": REFERENCE[model_key], "mean_in_acceptance_interval": low <= mean <= high}
    report = {"passed": len(records) == 15 and all(value["mean_in_acceptance_interval"] for value in models.values()),
              "metric": "mean absolute error on log10(Papp in cm/s)", "aggregation": "population standard deviation (ddof=0)",
              "models": models, "runs": records}
    dump(root / "aggregate.json", report)
    with (root / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model", "seed", "test_mae"])
        for record in records:
            writer.writerow([record["model"], record["seed"], record["mae"]])
    if not report["passed"]:
        raise RuntimeError("published-reference acceptance gate failed")


def stage_render(root):
    report = json.loads((root / "aggregate.json").read_text())
    order = ["rdkit2d", "cnn", "morgan"]
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    positions = np.arange(len(order))
    means = [report["models"][key]["mean_mae"] for key in order]
    errors = [report["models"][key]["population_std"] for key in order]
    bars = ax.bar(positions, means, yerr=errors, capsize=5, color=["#277da1", "#43aa8b", "#f8961e"])
    for index, key in enumerate(order):
        reference = report["models"][key]["reference"]
        ax.scatter(index, reference["mean"], marker="D", color="black", zorder=3)
        for seed, value in enumerate(report["models"][key]["seed_mae"], 1):
            ax.scatter(index + (seed - 3) * 0.035, value, color="white", edgecolor="black", s=24, zorder=4)
    ax.set_xticks(positions, [DISPLAY[key] for key in order])
    ax.set_ylabel("Test MAE — log10(Papp in cm/s)")
    ax.set_title("TDC Caco2_Wang: five official scaffold splits")
    ax.legend([bars[0], plt.Line2D([], [], marker="D", color="black", linestyle="")], ["Reproduced mean ± population SD", "Published mean"])
    fig.savefig(root / "caco2-baselines.png", dpi=180)
    plt.close(fig)


def stage_validate(root):
    aggregate = json.loads((root / "aggregate.json").read_text())
    audit = json.loads((root / "input-audit.json").read_text())
    required = [root / "aggregate.json", root / "metrics.csv", root / "input-audit.json", root / "caco2-baselines.png"]
    branch_files = [path for path in (root / "branches").rglob("*") if path.is_file() and path.name in {"metrics.json", "predictions.npy", "checkpoint.pt"}]
    checks = {"input_audit_passed": audit["passed"], "aggregate_passed": aggregate["passed"],
              "fifteen_metrics": len(list((root / "branches").glob("*/seed-*/metrics.json"))) == 15,
              "fifteen_predictions": len(list((root / "branches").glob("*/seed-*/predictions.npy"))) == 15,
              "fifteen_checkpoints": len(list((root / "branches").glob("*/seed-*/checkpoint.pt"))) == 15,
              "required_files_nonempty": all(path.is_file() and path.stat().st_size > 0 for path in required)}
    retained = root / "results"
    retained.mkdir(exist_ok=True)
    for path in required:
        shutil.copyfile(path, retained / path.name)
    shutil.copytree(root / "branches", retained / "branches", dirs_exist_ok=True)
    artifacts = {str(path.relative_to(root)): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in sorted(retained.rglob("*")) if path.is_file()}
    report = {"passed": all(checks.values()), "checks": checks, "artifacts": artifacts,
              "limitations": "Benchmark reproduction only; predictive accuracy is not experimental or clinical validation."}
    dump(root / "validation.json", report)
    if not report["passed"]:
        raise RuntimeError("final validation failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "train", "aggregate", "render", "validate"])
    parser.add_argument("--output", default=".")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--seed", type=int, choices=SEEDS)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.stage == "prepare": stage_prepare(root)
    elif args.stage == "train":
        if args.model is None or args.seed is None:
            parser.error("train requires --model and --seed")
        stage_train(root, args.model, args.seed)
    elif args.stage == "aggregate": stage_aggregate(root)
    elif args.stage == "render": stage_render(root)
    else: stage_validate(root)


if __name__ == "__main__":
    main()
