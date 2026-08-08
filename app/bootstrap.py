"""应用装配：把配置、日志、数据库组合为统一的 AppContext。

后续各阶段（Service/Repository/UI）统一从 AppContext 获取依赖。
"""
from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from pathlib import Path

from core.config import ConfigManager
from core.logger import get_logger, setup_logging
from core.paths import (
    get_config_path,
    get_data_dir,
    get_default_db_path,
    get_log_dir,
)
from database import Database, init_db


@dataclass
class AppContext:
    """应用运行时上下文。"""

    app_dir: Path
    config: ConfigManager
    logger: Logger
    db: Database


def create_application(app_dir: Path | str | None = None) -> AppContext:
    """创建并初始化应用。

    流程:
        1. 解析应用目录
        2. 加载配置
        3. 初始化日志
        4. 初始化数据库

    参数:
        app_dir: 应用数据目录，默认按平台解析。
    """
    from core.paths import get_app_dir

    resolved = get_app_dir(app_dir)
    config = ConfigManager(get_config_path(resolved))
    if not config.path.exists():
        config.save()  # 首次运行自动生成配置文件，便于用户修改参数
    setup_logging(config, get_log_dir(resolved))

    db_path = Path(config.get("database.path") or get_default_db_path(resolved))
    db = Database(db_path)
    init_db(db)

    logger = get_logger("app")
    logger.info(
        "应用初始化完成，目录=%s，数据库=%s",
        resolved,
        getattr(db, "db_path", db_path),
    )
    return AppContext(app_dir=resolved, config=config, logger=logger, db=db)
