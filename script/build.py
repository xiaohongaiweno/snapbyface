#!/usr/bin/env python3
"""Build SnapByFace installers for local machines and GitHub Actions."""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

APP_NAME = "SnapByFace"
ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT_DIR / "script"
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
INSTALLER_DIR = DIST_DIR / "installers"
SPEC_PATH = SCRIPT_DIR / "snapbyface.spec"
WINDOWS_INSTALLER_SCRIPT = SCRIPT_DIR / "installer_windows.iss"
DEFAULT_VENV_DIR = ROOT_DIR / ".venv-build"
MODEL_DIR = ROOT_DIR / "data" / "models" / "buffalo_l"
REQUIRED_MODEL_FILES = {
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "genderage.onnx",
    "w600k_r50.onnx",
}

TRUE_VALUES = {"1", "true", "yes", "on"}


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    """Run a command from the repository root with readable logging."""
    printable = " ".join(f'"{part}"' if " " in part else part for part in command)
    print(f"+ {printable}", flush=True)
    subprocess.run(command, cwd=ROOT_DIR, env=env, check=True)


def current_target() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return system


def venv_python(venv_dir: Path) -> Path:
    if platform.system().lower() == "windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_venv(venv_dir: Path, python_bin: str) -> Path:
    if not venv_dir.exists():
        print(f"Creating virtual environment: {venv_dir}")
        if Path(python_bin).resolve() == Path(sys.executable).resolve():
            venv.create(venv_dir, with_pip=True)
        else:
            run([python_bin, "-m", "venv", str(venv_dir)])
    python = venv_python(venv_dir)
    if not python.exists():
        raise SystemExit(f"Virtual environment python not found: {python}")
    return python


def install_dependencies(python: Path) -> None:
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-r", str(ROOT_DIR / "requirements.txt")])
    run([str(python), "-m", "pip", "install", "pyinstaller>=6.0"])


def resolve_version(raw_version: str | None) -> str:
    version = raw_version or os.environ.get("SNAPBYFACE_VERSION") or "0.1.0"
    version = version.removeprefix("refs/tags/").removeprefix("v")
    version = re.sub(r"[^0-9A-Za-z._+-]+", "-", version).strip(".-")
    return version or "0.1.0"


def resolve_include_models(mode: str) -> bool:
    env_value = os.environ.get("SNAPBYFACE_INCLUDE_MODELS")
    if env_value and mode == "auto":
        return env_value.lower() in TRUE_VALUES
    if mode == "yes":
        return True
    if mode == "no":
        return False
    return model_ready()


def model_ready() -> bool:
    return all((MODEL_DIR / filename).is_file() for filename in REQUIRED_MODEL_FILES)


def build_with_pyinstaller(python: Path, include_models: bool) -> None:
    if include_models and not model_ready():
        raise SystemExit(
            f"AI model directory is missing or incomplete: {MODEL_DIR}. "
            "Run script/download_models.py before packaging."
        )
    env = os.environ.copy()
    env["SNAPBYFACE_INCLUDE_MODELS"] = "1" if include_models else "0"
    print(f"Bundled AI models: {'yes' if include_models else 'no'}")
    run(
        [
            str(python),
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
            str(SPEC_PATH),
        ],
        env=env,
    )


def create_windows_installer(version: str) -> Path:
    source_dir = DIST_DIR / APP_NAME
    if not source_dir.exists():
        raise SystemExit(f"PyInstaller output not found: {source_dir}")

    iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc is None:
        raise SystemExit(
            "Inno Setup compiler not found. Install Inno Setup or run on GitHub Actions."
        )

    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            iscc,
            f"/DSourceDir={source_dir}",
            f"/DOutputDir={INSTALLER_DIR}",
            f"/DAppVersion={version}",
            str(WINDOWS_INSTALLER_SCRIPT),
        ]
    )
    installer = INSTALLER_DIR / f"{APP_NAME}-Windows-{version}-Setup.exe"
    if not installer.exists():
        raise SystemExit(f"Windows installer was not created: {installer}")
    return installer


def create_macos_dmg(version: str) -> Path:
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if not app_path.exists():
        raise SystemExit(f"PyInstaller app bundle not found: {app_path}")

    arch = platform.machine() or "unknown"
    staging_dir = BUILD_DIR / "dmg"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    run(["ditto", str(app_path), str(staging_dir / f"{APP_NAME}.app")])
    os.symlink("/Applications", staging_dir / "Applications")

    dmg_path = INSTALLER_DIR / f"{APP_NAME}-macOS-{version}-{arch}.dmg"
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    if dmg_path.exists():
        dmg_path.unlink()
    run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging_dir),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )
    return dmg_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        choices=["auto", "windows", "macos"],
        default="auto",
        help="Target platform. GitHub Actions should set this from the matrix.",
    )
    parser.add_argument("--version", help="Installer version. Defaults to SNAPBYFACE_VERSION.")
    parser.add_argument(
        "--venv",
        default=str(DEFAULT_VENV_DIR),
        help="Build virtual environment directory.",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("PYTHON_BIN", sys.executable),
        help="Python executable used when a build venv must be created.",
    )
    parser.add_argument(
        "--install-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Install/upgrade build dependencies before packaging.",
    )
    parser.add_argument(
        "--include-models",
        choices=["auto", "yes", "no"],
        default="auto",
        help="Bundle data/models when available. Defaults to auto.",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Only run PyInstaller; do not create .exe/.dmg installer artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = current_target() if args.platform == "auto" else args.platform
    host = current_target()
    if target != host:
        raise SystemExit(f"Cannot build {target!r} installer on {host!r}. Use a matching runner.")

    version = resolve_version(args.version)
    include_models = resolve_include_models(args.include_models)
    python = ensure_venv(Path(args.venv), args.python)

    if args.install_deps:
        install_dependencies(python)

    build_with_pyinstaller(python, include_models)

    artifact: Path
    if args.skip_installer:
        artifact = DIST_DIR / APP_NAME
    elif target == "windows":
        artifact = create_windows_installer(version)
    elif target == "macos":
        artifact = create_macos_dmg(version)
    else:
        raise SystemExit(f"Unsupported target: {target}")

    print(f"\nBuild complete: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
