"""通用后台 Worker 基类：从任务队列取任务执行。"""
from __future__ import annotations

import queue
import threading
from typing import Callable, Generic, TypeVar

from core.logger import get_logger
from core.task_queue import TaskQueue

T = TypeVar("T")

TaskHandler = Callable[[T], None]


class BaseWorker(threading.Thread, Generic[T]):
    """一个消费 TaskQueue 的后台线程。

    子类实现 process(item)；或直接传入 handler。
    stop() 后线程会在空闲时退出。
    """

    def __init__(
        self,
        queue: TaskQueue[T],
        name: str = "worker",
        handler: TaskHandler[T] | None = None,
        poll_interval: float = 0.2,
    ) -> None:
        super().__init__(name=name, daemon=True)
        self._queue = queue
        self._handler = handler
        self._poll_interval = poll_interval
        self._running = threading.Event()
        self._logger = get_logger(f"worker.{name}")

    def run(self) -> None:
        self._running.set()
        self._logger.info("Worker 启动")
        while self._running.is_set():
            try:
                item = self._queue.get(timeout=self._poll_interval)
            except queue.Empty:
                continue
            try:
                self._safe_process(item)
            finally:
                self._queue.task_done()
        self._logger.info("Worker 退出")

    def _safe_process(self, item: T) -> None:
        try:
            self.process(item)
        except Exception:
            self._logger.exception("处理任务失败: %r", item)

    def process(self, item: T) -> None:
        """处理单个任务，子类可覆写。"""
        if self._handler is not None:
            self._handler(item)
        else:
            raise NotImplementedError("必须实现 process 或提供 handler")

    def start(self) -> None:
        self._running.clear()
        super().start()

    def stop(self, timeout: float = 5.0) -> None:
        """请求停止并等待线程退出。未启动时安全返回。"""
        self._running.clear()
        if self.ident is None:
            return
        self.join(timeout=timeout)
        if self.is_alive():
            self._logger.warning("Worker %s 未能在 %s 秒内退出", self.name, timeout)
