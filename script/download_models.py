#!/usr/bin/env python3
"""Download AI models required by packaged SnapByFace builds."""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = "buffalo_l"
DEFAULT_MODEL_URL = (
    "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
)
REQUIRED_FILES = {
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "genderage.onnx",
    "w600k_r50.onnx",
}


def model_dir(root: Path, name: str) -> Path:
    return root / "models" / name


def verify_model(path: Path) -> bool:
    if not path.is_dir():
        return False
    for filename in REQUIRED_FILES:
        candidate = path / filename
        if not candidate.is_file() or candidate.stat().st_size <= 0:
            return False
    return True


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        total = int(response.headers.get("Content-Length", "0") or "0")
        written = 0
        with destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                written += len(chunk)
                if total:
                    percent = written * 100 // total
                    print(f"\rDownloaded {percent:3d}% ({written // 1024 // 1024} MB)", end="")
        print()


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if os.path.commonpath([destination_root, target]) != str(destination_root):
                raise SystemExit(f"Unsafe path in model archive: {member.filename}")
        archive.extractall(destination)


def install_from_zip(zip_path: Path, target_dir: Path, model_name: str) -> None:
    with tempfile.TemporaryDirectory(prefix="snapbyface-model-") as tmp:
        tmp_dir = Path(tmp)
        safe_extract(zip_path, tmp_dir)
        extracted_model_dir = tmp_dir / model_name
        source_dir = extracted_model_dir if extracted_model_dir.is_dir() else tmp_dir

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

    if not verify_model(target_dir):
        missing = ", ".join(sorted(REQUIRED_FILES - {p.name for p in target_dir.glob("*.onnx")}))
        raise SystemExit(f"Model verification failed: {target_dir}; missing {missing}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="InsightFace model name.")
    parser.add_argument(
        "--root",
        default=str(ROOT_DIR / "data"),
        help="Model root. Final path is <root>/models/<model>.",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("SNAPBYFACE_MODEL_URL", DEFAULT_MODEL_URL),
        help="Model archive URL. Can also be set with SNAPBYFACE_MODEL_URL.",
    )
    parser.add_argument("--force", action="store_true", help="Download and reinstall even if present.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify local model files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    target_dir = model_dir(root, args.model)
    zip_path = root / "models" / f"{args.model}.zip"

    if args.verify_only:
        if verify_model(target_dir):
            print(f"Model verified: {target_dir}")
            return 0
        raise SystemExit(f"Model is missing or incomplete: {target_dir}")

    if verify_model(target_dir) and not args.force:
        print(f"Model already present: {target_dir}")
        return 0

    if args.force and target_dir.exists():
        shutil.rmtree(target_dir)
    if args.force and zip_path.exists():
        zip_path.unlink()

    download(args.url, zip_path)
    install_from_zip(zip_path, target_dir, args.model)
    print(f"Model ready: {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
