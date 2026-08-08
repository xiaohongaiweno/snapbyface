"""扫描线程单元测试。"""
from __future__ import annotations

import time

from repositories.photo_repository import PhotoRepository
from services.index_service import IndexService
from services.photo_service import PhotoService
from tests.fakes import FakeFaceEngine, FakeVectorIndex, make_test_image
from workers.scanner_worker import ScannerWorker


def _setup(ctx, photo_dir):
    photo_service = PhotoService(ctx.db, ctx.config)
    photo_service.set_photo_directory(photo_dir)
    index_service = IndexService(ctx.db, ctx.config, FakeFaceEngine(), FakeVectorIndex())
    return photo_service, index_service


class TestScannerWorker:
    def test_scan_once_enqueues_pending(self, ctx, photo_dir):
        photo_service, index_service = _setup(ctx, photo_dir)
        make_test_image(photo_dir / "a.jpg", color=(255, 0, 0))
        make_test_image(photo_dir / "b.jpg", color=(0, 255, 0))

        worker = ScannerWorker(photo_service, index_service, interval=None)
        worker.run()  # 单次扫描

        assert PhotoRepository(ctx.db).count() == 2
        assert index_service.queue_size() == 2

    def test_worker_daemon_loop_with_stop(self, ctx, photo_dir):
        photo_service, index_service = _setup(ctx, photo_dir)
        make_test_image(photo_dir / "a.jpg")

        worker = ScannerWorker(photo_service, index_service, interval=0.05)
        worker.start()
        time.sleep(0.2)  # 至少跑一次
        worker.stop()
        assert not worker.is_alive()
        assert PhotoRepository(ctx.db).count() == 1
