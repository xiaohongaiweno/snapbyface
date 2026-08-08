"""线程安全任务队列。"""
from __future__ import annotations

import queue
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TaskQueue(Generic[T]):
    """基于 queue.Queue 的命名任务队列。"""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)

    def put(self, item: T) -> None:
        self._queue.put(item)

    def get(self, timeout: float | None = None) -> T:
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    def join(self) -> None:
        """等待所有已入队任务处理完成。"""
        self._queue.join()

    def drain(self) -> list[T]:
        """取出当前所有积压任务。"""
        items: list[T] = []
        while True:
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items
