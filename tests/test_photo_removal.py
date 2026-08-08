"""照片删除同步单元测试。"""
from __future__ import annotations

import time

import pytest

from models.photo import PhotoStatus
from repositories.photo_repository import PhotoRepository
from services.index_service import IndexService
from services.photo_service import PhotoService
from tests.fakes import FakeFaceEngine, FakeVectorIndex, make_test_image


@pytest.fixture
def indexed_photo(ctx, photo_dir):
    """一张已扫描且完成索引的照片。"""
    from core.ai.base import DetectedFace
    from tests.fakes import make_face

    ps = PhotoService(ctx.db, ctx.config)
    ps.set_photo_directory(photo_dir)
    make_test_image(photo_dir / "a.jpg")
    ps.scan()

    vindex = FakeVectorIndex()
    engine = FakeFaceEngine(faces=[make_face(), make_face()])
    isvc = IndexService(ctx.db, ctx.config, engine, vindex)
    photo = PhotoRepository(ctx.db).get_by_path(str(photo_dir / "a.jpg"))
    isvc.process_photo(photo.id)
    return isvc, vindex, photo


class TestRemovePhoto:
    def test_remove_by_path(self, ctx, indexed_photo, photo_dir):
        isvc, vindex, photo = indexed_photo
        assert vindex.size() == 2
        assert isvc.remove_photo_by_path(str(photo_dir / "a.jpg")) is True
        assert PhotoRepository(ctx.db).get_by_id(photo.id) is None
        assert vindex.size() == 0
        assert ctx.db.scalar("SELECT COUNT(*) FROM face") == 0
        assert ctx.db.scalar("SELECT COUNT(*) FROM face_embedding") == 0

    def test_remove_nonexistent_path_returns_false(self, ctx, indexed_photo):
        isvc, _, _ = indexed_photo
        assert isvc.remove_photo_by_path("/no/such.jpg") is False

    def test_remove_by_id(self, ctx, indexed_photo):
        isvc, vindex, photo = indexed_photo
        assert isvc.remove_photo(photo.id) is True
        assert vindex.size() == 0
        assert isvc.remove_photo(photo.id) is False

    def test_reindex_after_delete(self, ctx, photo_dir):
        """删除后重新扫描应能重新入库索引。"""
        from tests.fakes import make_face

        ps = PhotoService(ctx.db, ctx.config)
        ps.set_photo_directory(photo_dir)
        make_test_image(photo_dir / "b.jpg")
        ps.scan()
        vindex = FakeVectorIndex()
        isvc = IndexService(ctx.db, ctx.config, FakeFaceEngine(faces=[make_face()]), vindex)
        photo = PhotoRepository(ctx.db).get_by_path(str(photo_dir / "b.jpg"))
        isvc.process_photo(photo.id)
        assert vindex.size() == 1

        isvc.remove_photo_by_path(str(photo_dir / "b.jpg"))
        # 重新扫描（文件仍在）→ 重新入库
        ps.scan()
        photo2 = PhotoRepository(ctx.db).get_by_path(str(photo_dir / "b.jpg"))
        assert photo2 is not None
        isvc.process_photo(photo2.id)
        assert vindex.size() == 1
