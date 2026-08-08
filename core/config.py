"""配置系统。

基于 JSON 文件，支持点号路径读写，例如::

    config.get("face.threshold")  # -> 0.80
    config.set("photo.directory", "D:/SnapPhotos")

用户配置与默认配置做深合并，缺失的键自动取默认值，
保证新增配置项不影响已有用户的配置文件。
"""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from utils.photo_formats import PHOTO_EXTENSIONS

logger = logging.getLogger("snapbyface.config")

DEFAULT_CONFIG: dict[str, Any] = {
    "photo": {
        "directory": "",
        "watch_enabled": True,
        "extensions": list(PHOTO_EXTENSIONS),
    },
    "face": {
        "threshold": 0.80,
        "det_thresh": 0.5,
        "min_face_size": 80,
    },
    "ai": {
        "model_dir": "",
        "det_backend": "auto",
        "rec_model": "arcface_r100_v1",
    },
    "faiss": {
        "index_path": "",
        "dim": 512,
        "metric": "IP",
    },
    "database": {
        "path": "",
    },
    "log": {
        "level": "INFO",
        "max_bytes": 5 * 1024 * 1024,
        "backup_count": 5,
    },
    "license": {
        "trial_days": 15,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并两个字典，override 覆盖 base 中的同名键。"""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class ConfigManager:
    """配置管理器。

    参数:
        config_path: 配置文件路径，不存在时使用默认配置。
    """

    def __init__(self, config_path: Path | str) -> None:
        self._path = Path(config_path)
        self._data: dict[str, Any] = deepcopy(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        """从文件加载配置并与默认值合并。"""
        if not self._path.exists():
            return
        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("配置文件解析失败，使用默认配置: %s", exc)
            return
        if isinstance(loaded, dict):
            self._data = deep_merge(self._data, loaded)

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        """按点号路径读取配置。"""
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return deepcopy(node)

    def all(self) -> dict[str, Any]:
        """返回完整配置的深拷贝。"""
        return deepcopy(self._data)

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any) -> None:
        """按点号路径写入配置（仅内存，需调用 save 持久化）。"""
        parts = key.split(".")
        node: dict[str, Any] = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = deepcopy(value)

    def save(self) -> None:
        """将配置写入磁盘。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, indent=2, ensure_ascii=False)
        self._path.write_text(payload, encoding="utf-8")
        logger.info("配置已保存: %s", self._path)
