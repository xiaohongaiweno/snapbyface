#!/usr/bin/env bash
set -euo pipefail

# Build on macOS only. PyInstaller bundles native dependencies for the current
# architecture, so Intel and Apple Silicon should be built on matching runners.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS."
  exit 1
fi

"${PYTHON_BIN:-python3}" script/build.py --platform macos "$@"
