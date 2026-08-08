"""图片信息工具：EXIF 拍摄时间读取。"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import cv2
import numpy as np

from core.logger import get_logger
from utils.photo_formats import is_raw_path

logger = get_logger("utils.image")


def read_image(path: Path | str) -> np.ndarray | None:
    """Read a still image as an OpenCV BGR array.

    Standard formats use OpenCV. Camera RAW files are decoded with rawpy and
    converted from RGB to BGR for the existing face-engine contract.
    """
    p = Path(path)
    try:
        if is_raw_path(p):
            import rawpy

            with rawpy.imread(str(p)) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=True,
                    output_bps=8,
                )
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return cv2.imread(str(p), cv2.IMREAD_COLOR)
    except Exception as exc:
        logger.warning("读取照片失败: %s (%s)", p, exc)
        return None


def read_captured_at(path: Path | str) -> str | None:
    """读取照片 EXIF 拍摄时间，返回 ISO 字符串；读取失败回退文件修改时间。

    参数:
        path: 图片文件路径。
    返回:
        "YYYY-MM-DD HH:MM:SS" 或 None。
    """
    p = Path(path)
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(p) as img:
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    if TAGS.get(tag_id) == "DateTimeOriginal":
                        text = str(value).strip()
                        try:
                            dt = _dt.datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
                            return dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            logger.warning("EXIF 时间格式无法解析: %s", text)
                            break
    except Exception as exc:  # noqa: BLE001 - 任何读取失败都回退
        logger.debug("读取 EXIF 失败，回退文件时间: %s", exc)

    try:
        mtime = p.stat().st_mtime
        return _dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return None
