"""设置页 ViewModel。"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from services.photo_service import PhotoService


class SettingsViewModel(QObject):
    changed = pyqtSignal()

    def __init__(self, photo_service: PhotoService) -> None:
        super().__init__()
        self._photo_service = photo_service

    def get_photo_directory(self) -> str:
        d = self._photo_service.get_photo_directory()
        return str(d) if d else ""

    def set_photo_directory(self, path: str) -> tuple[bool, str]:
        """设置照片目录。返回 (是否成功, 错误信息)。"""
        if not path:
            return False, "目录不能为空"
        try:
            self._photo_service.set_photo_directory(path)
        except (NotADirectoryError, OSError) as exc:
            return False, str(exc)
        self.changed.emit()
        return True, ""

    def get_threshold(self) -> float:
        return self._photo_service._config.get("face.threshold", 0.80)

    def set_threshold(self, value: float) -> None:
        self._photo_service._config.set("face.threshold", float(value))
        self._photo_service._config.save()
        self.changed.emit()
