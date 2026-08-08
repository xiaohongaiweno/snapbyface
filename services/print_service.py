"""打印服务：保存打印记录并调用系统打印（规格 §20 打印）。"""
from __future__ import annotations

from datetime import datetime

from core.logger import get_logger
from database.connection import Database
from models.photo import PhotoStatus
from repositories.operation_log_repository import OperationLogRepository
from repositories.photo_repository import PhotoRepository

logger = get_logger("service.print")


class PrintService:
    """负责照片打印与 print_record 记录。"""

    def __init__(self, db: Database, logger=None) -> None:
        self._db = db
        self._photo_repo = PhotoRepository(db)
        self._op_log = OperationLogRepository(db)
        self._logger = logger or get_logger("service.print")

    def print_photo(self, photo_id: int, similarity: float | None = None,
                    operator: str = "admin") -> bool:
        """打印一张照片。

        返回:
            True 表示记录已写入（实际打印由系统打印对话框完成）。
        """
        photo = self._photo_repo.get_by_id(photo_id)
        if photo is None:
            self._logger.warning("打印失败：照片不存在 id=%s", photo_id)
            return False
        try:
            with self._db.transaction():
                self._db.execute(
                    """
                    INSERT INTO print_record (photo_id, similarity, operator, printed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (photo_id, similarity, operator,
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
            self._op_log.log("print", f"打印照片 {photo.file_name} (相似度 {similarity or 0:.1%})")
            self._logger.info("已打印: %s", photo.path)
            return True
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("打印记录失败: %s", exc)
            return False

    def recent_records(self, limit: int = 100) -> list[dict]:
        """最近打印记录。"""
        return self._db.fetchall(
            "SELECT * FROM print_record ORDER BY id DESC LIMIT ?",
            (limit,),
        )
