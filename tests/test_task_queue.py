"""任务队列单元测试。"""
from __future__ import annotations

import queue
import time

from core.task_queue import TaskQueue


class TestTaskQueue:
    def test_put_get(self):
        q = TaskQueue[int]()
        q.put(1)
        q.put(2)
        assert q.get() == 1
        assert q.get() == 2

    def test_empty_and_qsize(self):
        q = TaskQueue[int]()
        assert q.empty()
        assert q.qsize() == 0
        q.put(42)
        assert not q.empty()
        assert q.qsize() == 1

    def test_get_timeout_raises_empty(self):
        q = TaskQueue[int]()
        try:
            q.get(timeout=0.1)
            raise AssertionError("应当抛 Empty")
        except queue.Empty:
            pass

    def test_join_waits_until_task_done(self):
        q = TaskQueue[int]()
        q.put(1)
        q.put(2)
        assert q.get() == 1
        q.task_done()
        # 未调用 task_done 时 join 会阻塞，这里再取并完成即可
        q.get()
        q.task_done()
        q.join()  # 立即返回

    def test_drain(self):
        q = TaskQueue[int]()
        q.put(1)
        q.put(2)
        q.put(3)
        assert q.drain() == [1, 2, 3]
        assert q.empty()
