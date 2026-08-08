"""扫描后台线程：启动时与周期执行增量扫描，新照片入队（规格 §12）。"""
from __future__ import annotations

import threading
import time

from core.logger import get_logger
from models.photo import PhotoStatus
from repositories.photo_repository import PhotoRepository
from services.index_service import IndexService
from services.photo_service import PhotoService
from workers.base_worker import BaseWorker


class ScannerWorker(threading.Thread):
    """周期执行扫描，并把发现的待索引照片交给 IndexService 入队。

    参数:
        photo_service: 照片服务。
        index_service: 索引服务（负责入队）。
        interval: 扫描间隔秒数；None 表示仅启动时扫描一次。
    """

    def __init__(
        self,
        photo_service: PhotoService,
        index_service: IndexService,
        interval: float | None = 5.0,
        logger=None,
    ) -> None:
        super().__init__(name="scanner", daemon=True)
        self._photo_service = photo_service
        self._index_service = index_service
        self._interval = interval
        self._running = threading.Event()
        self._logger = logger or get_logger("worker.scanner")

    def run(self) -> None:
        self._running.set()
        self._logger.info("ScannerWorker 启动")
        while self._running.is_set():
            try:
                self.scan_once()
            except ValueError as exc:
                # 尚未配置照片目录等可恢复情况：仅提示，不刷堆栈
                self._logger.warning("跳过扫描: %s", exc)
                if self._interval is None:
                    break
            except Exception:
                self._logger.exception("周期扫描失败")
            if self._interval is None:
                break
            self._running.wait(self._interval)
        self._logger.info("ScannerWorker 退出")

    def scan_once(self) -> None:
        """执行一次扫描并把新照片加入索引队列。"""
        result = self._photo_service.scan()
        repo = PhotoRepository(self._photo_service._db)
        pending = repo.pending_photos(limit=2000)
        enqueued = 0
        for photo in pending:
            if self._index_service.submit_photo(photo):
                enqueued += 1
        self._logger.info(
            "扫描结果: 新增=%d 待索引入队=%d 队列=%d",
            result.new_photos,
            enqueued,
            self._index_service.queue_size(),
        )

    def stop(self, timeout: float = 5.0) -> None:
        self._running.clear()
        self.join(timeout=timeout)
