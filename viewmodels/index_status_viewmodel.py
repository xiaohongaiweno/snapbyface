"""索引状态页 ViewModel（规格 §13）。"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from services.index_service import IndexService
from services.photo_service import PhotoService


class IndexStatusViewModel(QObject):
    stats_updated = pyqtSignal(dict)

    def __init__(self, photo_service: PhotoService, index_service: IndexService) -> None:
        super().__init__()
        self._photo_service = photo_service
        self._index_service = index_service

    def refresh(self) -> dict:
        stats = self._photo_service.get_stats()
        stats["queue_size"] = self._index_service.queue_size()
        stats["engine_ready"] = getattr(self._index_service._engine, "is_ready", True)
        self.stats_updated.emit(stats)
        return stats
