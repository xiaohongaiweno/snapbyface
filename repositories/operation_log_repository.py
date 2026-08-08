"""操作日志数据访问层。"""
from __future__ import annotations

from datetime import datetime

from database.connection import Database


class OperationLogRepository:
    """operation_log 表操作。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def log(self, category: str, message: str, level: str = "INFO") -> None:
        """写入一条操作日志。"""
        self._db.execute(
            "INSERT INTO operation_log (category, message, level, created_at) VALUES (?, ?, ?, ?)",
            (category, message, level, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    def recent(self, limit: int = 200) -> list[dict]:
        """最近操作日志（新的在前）。"""
        return self._db.fetchall(
            "SELECT * FROM operation_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
