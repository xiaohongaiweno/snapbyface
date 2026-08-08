"""基础 Worker 单元测试。"""
from __future__ import annotations

import threading
import time

from core.task_queue import TaskQueue
from workers.base_worker import BaseWorker


class TestBaseWorker:
    def test_processes_items(self):
        q = TaskQueue[int]()
        seen: list[int] = []
        worker = BaseWorker(q, name="t1", handler=lambda x: seen.append(x * 2))
        worker.start()
        q.put(1)
        q.put(2)
        q.put(3)
        q.join()
        worker.stop()
        assert sorted(seen) == [2, 4, 6]

    def test_handler_exception_does_not_kill_worker(self):
        q = TaskQueue[int]()
        seen: list[int] = []

        def handler(x):
            if x == 1:
                raise ValueError("boom")
            seen.append(x)

        worker = BaseWorker(q, name="t2", handler=handler)
        worker.start()
        q.put(1)
        q.put(2)
        q.join()
        worker.stop()
        assert seen == [2]

    def test_stop_exits_thread(self):
        q = TaskQueue[int]()
        worker = BaseWorker(q, name="t3", handler=lambda x: None)
        worker.start()
        time.sleep(0.05)
        assert worker.is_alive()
        worker.stop()
        assert not worker.is_alive()

    def test_subclass_process(self):
        q = TaskQueue[int]()
        seen: list[int] = []

        class MyWorker(BaseWorker[int]):
            def process(self, item: int) -> None:
                seen.append(item + 1)

        w = MyWorker(q, name="t4")
        w.start()
        q.put(10)
        q.join()
        w.stop()
        assert seen == [11]

    def test_multi_worker_shared_queue(self):
        q = TaskQueue[int]()
        seen: list[int] = []
        lock = threading.Lock()

        def handler(x):
            with lock:
                seen.append(x)

        workers = [BaseWorker(q, name=f"w{i}", handler=handler) for i in range(3)]
        for w in workers:
            w.start()
        for i in range(30):
            q.put(i)
        q.join()
        for w in workers:
            w.stop()
        assert sorted(seen) == list(range(30))

    def test_stop_before_start_is_safe(self):
        q = TaskQueue[int]()
        worker = BaseWorker(q, name="t5", handler=lambda x: None)
        worker.stop()  # 不应抛异常

    def test_double_stop_is_safe(self):
        q = TaskQueue[int]()
        worker = BaseWorker(q, name="t6", handler=lambda x: None)
        worker.start()
        worker.stop()
        worker.stop()  # 重复停止不应抛异常
