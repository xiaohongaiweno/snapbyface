"""Application version helpers."""
from __future__ import annotations

import os

APP_NAME = "SnapByFace"
DEFAULT_APP_VERSION = "0.1.0"


def app_version() -> str:
    """Return the runtime application version."""
    version = os.environ.get("SNAPBYFACE_VERSION") or DEFAULT_APP_VERSION
    version = version.removeprefix("refs/tags/").removeprefix("v").strip()
    return version[:32] or DEFAULT_APP_VERSION
