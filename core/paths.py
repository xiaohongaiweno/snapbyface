"""应用路径解析。

统一管理应用数据目录，避免代码中写死路径。

优先级：
1. 显式传入的 explicit 目录
2. 环境变量 SNAPBYFACE_HOME
3. Windows: %APPDATA%/SnapByFace
4. 其他平台: ~/.snapbyface
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "SnapByFace"
ENV_HOME = "SNAPBYFACE_HOME"


def get_app_dir(explicit: Path | str | None = None) -> Path:
    """返回应用根目录。"""
    if explicit is not None:
        return Path(explicit).expanduser()
    env = os.environ.get(ENV_HOME)
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
    return Path.home() / ".snapbyface"


def get_config_path(app_dir: Path | str) -> Path:
    """返回配置文件路径。"""
    return Path(app_dir) / "config.json"


def get_log_dir(app_dir: Path | str) -> Path:
    """返回日志目录。"""
    return Path(app_dir) / "logs"


def get_data_dir(app_dir: Path | str) -> Path:
    """返回数据目录（数据库、FAISS 索引等）。"""
    return Path(app_dir) / "data"


def get_default_db_path(app_dir: Path | str) -> Path:
    """返回默认 SQLite 数据库路径。"""
    return get_data_dir(app_dir) / "snapbyface.db"


def get_default_faiss_path(app_dir: Path | str) -> Path:
    """返回默认 FAISS 索引路径。"""
    return get_data_dir(app_dir) / "face_index.faiss"


def get_project_root() -> Path:
    """返回项目根目录（core/paths.py 所在目录的上两级）。"""
    return Path(__file__).resolve().parents[1]


def get_model_root() -> Path:
    """返回默认 AI 模型根目录（当前目录下 data/）。

    insightface 会把模型存放在 <root>/models/<name>/，
    故 root 取 data/，模型最终位于 data/models/buffalo_l/。
    可通过配置 ai.model_dir 覆盖。
    """
    return get_project_root() / "data"
