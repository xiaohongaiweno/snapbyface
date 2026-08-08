"""日志系统。

配置后同时输出到控制台和轮转日志文件，避免日志无限增长。
每次 setup_logging 会清空旧 handler，保证可重复调用（便于测试）。
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.config import ConfigManager

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "snapbyface.log"
ROOT_LOGGER_NAME = "snapbyface"


def setup_logging(
    config: ConfigManager,
    log_dir: Path | str,
) -> logging.Logger:
    """按配置初始化日志系统，返回根 logger。

    参数:
        config: 配置管理器，读取 log.level / log.max_bytes / log.backup_count。
        log_dir: 日志文件所在目录。
    """
    level_name = str(config.get("log.level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    max_bytes = int(config.get("log.max_bytes", 5 * 1024 * 1024))
    backup_count = int(config.get("log.backup_count", 5))

    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(level)
    root.propagate = False

    # 幂等：清空旧 handler，保证换目录后可重建
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_dir_path / LOG_FILE_NAME,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(file_handler)
    root.info("日志系统初始化完成，级别=%s，目录=%s", level_name, log_dir_path)
    return root


def get_logger(name: str = "") -> logging.Logger:
    """获取应用日志器，name 为空时返回根 logger。"""
    full = ROOT_LOGGER_NAME if not name else f"{ROOT_LOGGER_NAME}.{name}"
    return logging.getLogger(full)
