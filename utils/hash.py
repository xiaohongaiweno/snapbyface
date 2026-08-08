"""文件哈希工具（规格 §11 不重复扫描）。"""
from __future__ import annotations

import hashlib
from pathlib import Path

_READ_CHUNK = 1024 * 1024  # 1MB


def hash_file(path: Path | str, algorithm: str = "sha256") -> str:
    """计算文件内容哈希，用于去重。"""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        while chunk := fh.read(_READ_CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """计算字节流哈希。"""
    return hashlib.new(algorithm, data).hexdigest()
