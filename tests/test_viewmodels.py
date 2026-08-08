"""ViewModel 单元测试。"""
from __future__ import annotations

import numpy as np
import pytest

from services.camera_service import CameraService
from services.search_service import SearchService
from viewmodels.search_viewmodel import SearchViewModel
from viewmodels.settings_viewmodel import SettingsViewModel
from viewmodels.index_status_viewmodel import IndexStatusViewModel


class TestSearchViewModel:
    def test_search_sync_returns_results(self, qapp, ctx, photo_dir, monkeypatch):
        from services.photo_service import PhotoService
        from core.vector.faiss_index import FaissIndex
        from tests.fakes import FakeFaceEngine, make_test_image
        from core.ai.base import DetectedFace

        ps = PhotoService(ctx.db, ctx.config)
        ps.set_photo_directory(photo_dir)
        make_test_image(photo_dir / "a.jpg")
        ps.scan()

        from repositories.photo_repository import PhotoRepository
        photo = PhotoRepository(ctx.db).get_by_path(str(photo_dir / "a.jpg"))
        vid = "v1"
        v = np.random.RandomState(0).normal(size=512).astype(np.float32)
        v /= np.linalg.norm(v)
        from repositories.face_repository import FaceRepository
        FaceRepository(ctx.db).insert_face_with_embedding(photo.id, "[0,0,9,9]", 0.9, vid)
        ctx.db.execute("UPDATE photo SET status='done' WHERE id=?", (photo.id,))

        index = FaissIndex(dim=512, index_path=photo_dir.parent / "idx")
        index.add_vector(vid, v)

        engine = FakeFaceEngine(faces=[DetectedFace(bbox=(0, 0, 9, 9), embedding=v)])
        search = SearchService(engine, index, ctx.db, ctx.config)
        cam = CameraService()

        vm = SearchViewModel(cam, search)
        results, err = vm.search_sync(np.zeros((16, 16, 3), dtype=np.uint8))
        assert err == ""
        assert len(results) == 1
        assert results[0].photo_id == photo.id

    def test_search_sync_error(self, qapp, ctx, photo_dir):
        from core.vector.faiss_index import FaissIndex
        from tests.fakes import FakeFaceEngine
        from services.photo_service import PhotoService

        engine = FakeFaceEngine(fail=True)
        index = FaissIndex(dim=512, index_path=photo_dir.parent / "idx")
        search = SearchService(engine, index, ctx.db, ctx.config)
        cam = CameraService()
        vm = SearchViewModel(cam, search)
        results, err = vm.search_sync(np.zeros((8, 8, 3), dtype=np.uint8))
        assert results == []
        assert "fake engine failed" in err

    def test_start_search_no_frame_emits_error(self, qapp, ctx, photo_dir):
        from core.vector.faiss_index import FaissIndex
        from tests.fakes import FakeFaceEngine
        from services.photo_service import PhotoService

        search = SearchService(
            FakeFaceEngine(), FaissIndex(dim=512, index_path=photo_dir.parent / "i"),
            ctx.db, ctx.config,
        )
        vm = SearchViewModel(CameraService(), search)
        errors = []
        vm.search_error.connect(errors.append)
        assert vm.start_search() is False
        assert len(errors) == 1

    def test_start_search_with_frame_does_not_crash(self, qapp, ctx, photo_dir):
        """回归：摄像头已有帧时，read() 返回数组，不应触发
        numpy 真值判断 ValueError（历史崩溃）。"""
        import time

        from core.vector.faiss_index import FaissIndex
        from tests.fakes import FakeFaceEngine
        from viewmodels.search_viewmodel import SearchViewModel

        class StubCamera:
            def __init__(self):
                self._frame = np.zeros((16, 16, 3), dtype=np.uint8)

            def read(self):
                return self._frame

            def capture_once(self):
                return self._frame

        search = SearchService(
            FakeFaceEngine(), FaissIndex(dim=512, index_path=photo_dir.parent / "i"),
            ctx.db, ctx.config,
        )
        vm = SearchViewModel(StubCamera(), search)
        got = []
        vm.results_ready.connect(lambda r: got.append(r))
        assert vm.start_search() is True

        deadline = time.time() + 10
        while time.time() < deadline and not got:
            qapp.processEvents()
            time.sleep(0.02)
        assert got, "search worker 未返回结果"
        assert got[0] == []  # 无索引照片 → 空结果，但流程完整不崩溃


class TestSettingsViewModel:
    def test_set_photo_directory(self, ctx, photo_dir):
        from services.photo_service import PhotoService

        vm = SettingsViewModel(PhotoService(ctx.db, ctx.config))
        ok, err = vm.set_photo_directory(str(photo_dir))
        assert ok and err == ""
        assert vm.get_photo_directory() == str(photo_dir.resolve())

    def test_set_invalid_directory(self, ctx):
        from services.photo_service import PhotoService

        vm = SettingsViewModel(PhotoService(ctx.db, ctx.config))
        ok, err = vm.set_photo_directory("/no/such/dir")
        assert not ok
        assert "不存在" in err

    def test_threshold_roundtrip(self, ctx):
        from services.photo_service import PhotoService

        vm = SettingsViewModel(PhotoService(ctx.db, ctx.config))
        vm.set_threshold(0.85)
        assert vm.get_threshold() == pytest.approx(0.85)


class TestIndexStatusViewModel:
    def test_refresh_returns_stats(self, ctx, photo_dir):
        from services.photo_service import PhotoService
        from services.index_service import IndexService
        from tests.fakes import FakeFaceEngine, FakeVectorIndex

        ps = PhotoService(ctx.db, ctx.config)
        ps.set_photo_directory(photo_dir)
        idx_svc = IndexService(ctx.db, ctx.config, FakeFaceEngine(), FakeVectorIndex())
        vm = IndexStatusViewModel(ps, idx_svc)
        stats = vm.refresh()
        assert stats["total"] == 0
        assert stats["queue_size"] == 0
