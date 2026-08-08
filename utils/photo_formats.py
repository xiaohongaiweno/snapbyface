"""Supported still-image formats.

Video formats are intentionally absent. OpenCV is used for live camera
capture, but the photo import pipeline only accepts still images.
"""
from __future__ import annotations

from pathlib import Path

PHOTO_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".cr2",
    ".cr3",
    ".nef",
    ".nrw",
    ".arw",
    ".dng",
    ".orf",
    ".rw2",
    ".raf",
    ".pef",
    ".srw",
    ".3fr",
    ".iiq",
)

RAW_EXTENSIONS = frozenset({
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".dng", ".orf",
    ".rw2", ".raf", ".pef", ".srw", ".3fr", ".iiq",
})


def is_raw_path(path: str | Path) -> bool:
    """Return whether a path uses a supported camera RAW extension."""
    return Path(path).suffix.lower() in RAW_EXTENSIONS
