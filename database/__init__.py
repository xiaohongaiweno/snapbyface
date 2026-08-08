"""数据库层对外接口。"""
from __future__ import annotations

from database.connection import Database
from database.schema import SCHEMA_STATEMENTS, SCHEMA_VERSION, ALL_TABLE_NAMES
from core.logger import get_logger

logger = get_logger("database")


def init_db(db: Database) -> None:
    """初始化数据库：创建缺失的表并升级 schema 版本。

    参数:
        db: 数据库封装实例。
    """
    with db.transaction():
        for statement in SCHEMA_STATEMENTS:
            db.execute(statement)
        db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    logger.info("数据库初始化完成，schema_version=%s", SCHEMA_VERSION)


__all__ = [
    "Database",
    "init_db",
    "SCHEMA_STATEMENTS",
    "SCHEMA_VERSION",
    "ALL_TABLE_NAMES",
]
