"""Restore the frozen PDEBench inputs from the public DaRUS release."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile


def fetch(file_id, target, byte_range=None):
    command = ["curl", "--fail", "--location", "--retry", "4",
               "--retry-all-errors", "--connect-timeout", "30",
               "--max-time", "300"]
    url = f"https://darus.uni-stuttgart.de/api/access/datafile/{file_id}"
    if byte_range is None:
        subprocess.run(command + ["--output", str(target), url], check=True)
        return

    chunk_size = 64 * 1024 * 1024
    part = target.with_suffix(target.suffix + ".part")
    with target.open("wb") as output:
        for start in range(0, byte_range, chunk_size):
            end = min(byte_range, start + chunk_size) - 1
            part.unlink(missing_ok=True)
            subprocess.run(command + ["--range", f"{start}-{end}",
                                      "--output", str(part), url], check=True)
            expected = end - start + 1
            if part.stat().st_size != expected:
                raise RuntimeError(f"unexpected dataset chunk length: {start}-{end}")
            with part.open("rb") as source:
                shutil.copyfileobj(source, output)
    part.unlink(missing_ok=True)
    if target.stat().st_size != byte_range:
        raise RuntimeError("unexpected dataset range length")


def verify(path, expected):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise RuntimeError(f"checksum mismatch: {path.name}")


def extract_checkpoint(archive, target):
    # PyTorch checkpoints are ZIP files, so a tar containing them can also
    # satisfy zipfile.is_zipfile(). Inspect the outer tar container first.
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as source:
            matches = [member for member in source
                       if member.isfile() and Path(member.name).name == target.name]
            if len(matches) == 1:
                with source.extractfile(matches[0]) as item, target.open("wb") as output:
                    shutil.copyfileobj(item, output)
                return
    elif zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            matches = [name for name in source.namelist() if Path(name).name == target.name]
            if len(matches) == 1:
                with source.open(matches[0]) as item, target.open("wb") as output:
                    shutil.copyfileobj(item, output)
                return
    archive.rename(target)


def main():
    manifest = json.loads(Path("/app/input-manifest.json").read_text())
    root = Path("/inputs")
    root.mkdir(exist_ok=True)
    dataset = manifest["dataset"]
    target = root / f"{dataset['name']}.head"
    fetch(dataset["id"], target, dataset["range_bytes"])
    verify(target, dataset["range_sha256"])
    for key, suffix in (("fno", "FNO"), ("unet", "Unet-PF-20")):
        item = manifest[key]
        archive = root / f"{key}.download"
        target = root / f"1D_Advection_Sols_beta4.0_{suffix}.pt"
        fetch(item["archive_id"], archive)
        extract_checkpoint(archive, target)
        verify(target, item["sha256"])
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
