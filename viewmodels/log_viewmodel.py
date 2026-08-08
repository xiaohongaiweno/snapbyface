"""日志页 ViewModel。"""
from __future__ import annotations

from PyQt6.QtCore import QObject

from repositories.operation_log_repository import OperationLogRepository


class LogViewModel(QObject):
    def __init__(self, op_log_repo: OperationLogRepository) -> None:
        super().__init__()
        self._repo = op_log_repo

    def recent(self, limit: int = 200) -> list[dict]:
        return self._repo.recent(limit=limit)
