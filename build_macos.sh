#!/usr/bin/env bash
set -euo pipefail

# Build on macOS only. PyInstaller bundles native dependencies for the
# current architecture, so Intel and Apple Silicon should be built separately.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv-build}"

echo "[1/5] Creating virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "[2/5] Upgrading pip..."
python -m pip install --upgrade pip

echo "[3/5] Installing dependencies..."
python -m pip install -r requirements.txt

echo "[4/5] Installing PyInstaller..."
python -m pip install pyinstaller

echo "[5/5] Building SnapByFace.app..."
pyinstaller --clean --noconfirm snapbyface.spec

echo
echo "Build complete: $ROOT_DIR/dist/SnapByFace.app"
echo
echo "First launch may ask for camera permission."
echo "For distribution, sign and notarize the app on a macOS release machine."
