"""USB 摄像头服务：后台线程持续采集最新帧（规格 §20 找片）。"""
from __future__ import annotations

import threading
from typing import Any

import cv2
import numpy as np

from core.logger import get_logger

logger = get_logger("service.camera")


class CameraService:
    """封装 OpenCV VideoCapture。

    输入源仅支持 USB 摄像头索引（int）。

    start() 后在后台线程持续读取，read() 返回最新一帧；
    capture_once() 立即抓取一帧（供拍照搜索）。
    """

    def __init__(self, source: int = 0, logger=None) -> None:
        if not isinstance(source, int):
            raise TypeError("CameraService 只支持 USB 摄像头索引，不支持视频文件")
        self._source = source
        self._logger = logger or get_logger("service.camera")
        self._cap: Any = None
        self._latest: np.ndarray | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

    # ------------------------------------------------------------------
    # 摄像头检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_cameras(max_index: int = 5) -> list[int]:
        """探测可用的摄像头索引。"""
        import cv2

        available: list[int] = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
            cap.release()
        return available

    @property
    def source(self) -> int:
        return self._source

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """打开摄像头并启动采集线程。返回是否成功。"""
        if self.is_running:
            return True
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            self._logger.warning("无法打开摄像头源: %r", self._source)
            cap.release()
            return False
        self._cap = cap
        self._running.set()
        self._thread = threading.Thread(target=self._capture_loop, name="camera", daemon=True)
        self._thread.start()
        self._logger.info("摄像头源 %r 已启动", self._source)
        return True

    def _capture_loop(self) -> None:
        while self._running.is_set():
            ok, frame = self._cap.read()
            if ok:
                with self._lock:
                    self._latest = frame
            else:
                self._logger.warning("读取摄像头帧失败")

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._latest = None
        self._logger.info("摄像头已停止")

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def read(self) -> np.ndarray | None:
        """返回最新一帧的拷贝；未启动或失败返回 None。"""
        with self._lock:
            frame = self._latest
        return frame.copy() if frame is not None else None

    def capture_once(self) -> np.ndarray | None:
        """立即抓取一帧（同步），用于拍照搜索。"""
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if ok:
            with self._lock:
                self._latest = frame
            return frame
        return None
