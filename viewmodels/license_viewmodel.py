"""授权页 ViewModel。"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from services.license_service import LicenseService


class LicenseViewModel(QObject):
    status_changed = pyqtSignal(dict)

    def __init__(self, license_service: LicenseService) -> None:
        super().__init__()
        self._service = license_service

    def machine_code(self) -> str:
        return self._service.machine_code

    def status(self) -> dict:
        st = self._service.status()
        self.status_changed.emit(st)
        return st

    def activate(self, key: str) -> tuple[bool, str]:
        ok, msg = self._service.activate(key)
        if ok:
            self.status_changed.emit(self._service.status())
        return ok, msg
