"""搜索页 ViewModel：摄像头 + 人脸检索（规格 §6.3）。"""
from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from services.camera_service import CameraService
from services.search_service import SearchService


class SearchWorker(QThread):
    """后台执行人脸检索，避免阻塞 UI。"""

    done = pyqtSignal(list, str)  # (results, error)

    def __init__(self, search_service: SearchService, image: np.ndarray) -> None:
        super().__init__()
        self._service = search_service
        self._image = image

    def run(self) -> None:
        try:
            results = self._service.search_image(self._image)
            self.done.emit(results, "")
        except Exception as exc:  # noqa: BLE001
            self.done.emit([], str(exc))


class SearchViewModel(QObject):
    search_started = pyqtSignal()
    results_ready = pyqtSignal(list)
    search_error = pyqtSignal(str)
    status_message = pyqtSignal(str)
    camera_changed = pyqtSignal(bool)

    def __init__(
        self,
        camera_service: CameraService,
        search_service: SearchService,
        logger=None,
    ) -> None:
        super().__init__()
        self._camera = camera_service
        self._search = search_service
        self._worker: SearchWorker | None = None

    # ------------------------------------------------------------------
    # 摄像头
    # ------------------------------------------------------------------
    def start_camera(self) -> bool:
        ok = self._camera.start()
        self.camera_changed.emit(ok)
        if ok:
            self.status_message.emit("摄像头已启动")
        else:
            self.status_message.emit("无法打开摄像头")
        return ok

    def stop_camera(self) -> None:
        self._camera.stop()
        self.camera_changed.emit(False)
        self.status_message.emit("摄像头已停止")

    def is_camera_running(self) -> bool:
        return self._camera.is_running

    def get_latest_frame(self) -> np.ndarray | None:
        return self._camera.read()

    def capture_frame(self) -> np.ndarray | None:
        """Capture one frame from the active camera."""
        return self._camera.capture_once()

    # ------------------------------------------------------------------
    # 搜索（异步）
    # ------------------------------------------------------------------
    def search_sync(self, image: np.ndarray) -> tuple[list, str]:
        """同步检索核心，便于测试。返回 (results, error)。"""
        try:
            return self._search.search_image(image), ""
        except Exception as exc:  # noqa: BLE001
            return [], str(exc)

    def start_search(self) -> bool:
        """基于最新帧发起搜索。返回是否已启动。"""
        frame = self._camera.read()
        if frame is None:
            frame = self._camera.capture_once()
        if frame is None:
            self.search_error.emit("无可用摄像头画面")
            self.status_message.emit("无可用摄像头画面")
            return False
        return self.start_image_search(frame)

    def start_image_search(self, image: np.ndarray) -> bool:
        """基于一张静态照片发起搜索。"""
        if image is None:
            self.search_error.emit("照片无法读取")
            self.status_message.emit("照片无法读取")
            return False
        if self._worker is not None and self._worker.isRunning():
            self.status_message.emit("已有搜索正在进行")
            return False
        self.search_started.emit()
        self.status_message.emit("搜索中...")
        self._worker = SearchWorker(self._search, image)
        self._worker.done.connect(self._on_search_done)
        self._worker.start()
        return True

    def _on_search_done(self, results: list, error: str) -> None:
        if error:
            self.search_error.emit(error)
            self.status_message.emit(f"搜索失败: {error}")
        else:
            self.results_ready.emit(results)
            self.status_message.emit(f"搜索完成，命中 {len(results)} 张照片")
        self._worker = None
