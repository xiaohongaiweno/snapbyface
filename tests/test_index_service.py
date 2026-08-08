"""索引服务单元测试。"""
from __future__ import annotations

import time

import pytest

from models.photo import PhotoStatus
from repositories.face_repository import FaceRepository
from repositories.photo_repository import PhotoRepository
from services.index_service import IndexService
from services.photo_service import PhotoService
from tests.fakes import FakeFaceEngine, FakeVectorIndex, make_face, make_test_image


@pytest.fixture
def photo_dir(tmp_path):
    d = tmp_path / "photos"
    d.mkdir()
    return d


_MISSING = object()


def _build(ctx, photo_dir, engine=None, vector_index=_MISSING):
    photo_service = PhotoService(ctx.db, ctx.config)
    if photo_dir is not None:
        photo_service.set_photo_directory(photo_dir)
    engine = engine or FakeFaceEngine()
    if vector_index is _MISSING:
        vector_index = FakeVectorIndex()
    index_service = IndexService(ctx.db, ctx.config, engine, vector_index)
    return photo_service, index_service, engine, vector_index


def _add_photo(photo_service, photo_dir, name="a.jpg"):
    path = make_test_image(photo_dir / name)
    photo_service.scan()
    repo = PhotoRepository(photo_service._db)
    return repo.get_by_path(path)


class TestProcessPhoto:
    def test_happy_path_with_faces(self, ctx, photo_dir):
        photo_service, index_service, engine, vindex = _build(ctx, photo_dir)
        engine._faces = [make_face() for _ in range(2)]
        photo = _add_photo(photo_service, photo_dir)

        assert index_service.process_photo(photo.id) is True

        repo = PhotoRepository(ctx.db)
        updated = repo.get_by_id(photo.id)
        assert updated.status == PhotoStatus.DONE.value
        assert updated.face_count == 2
        assert vindex.size() == 2  # 特征已入向量库

        faces = FaceRepository(ctx.db).get_by_photo(photo.id)
        assert len(faces) == 2
        assert all(f["vector_id"] for f in faces)  # 有关联向量

    def test_no_faces_marks_done(self, ctx, photo_dir):
        photo_service, index_service, engine, vindex = _build(ctx, photo_dir)
        engine._faces = []
        photo = _add_photo(photo_service, photo_dir)

        assert index_service.process_photo(photo.id) is True
        updated = PhotoRepository(ctx.db).get_by_id(photo.id)
        assert updated.status == PhotoStatus.DONE.value
        assert updated.face_count == 0

    def test_failure_marks_failed(self, ctx, photo_dir):
        photo_service, index_service, engine, vindex = _build(
            ctx, photo_dir, engine=FakeFaceEngine(fail=True)
        )
        photo = _add_photo(photo_service, photo_dir)

        assert index_service.process_photo(photo.id) is False
        updated = PhotoRepository(ctx.db).get_by_id(photo.id)
        assert updated.status == PhotoStatus.FAILED.value

    def test_missing_photo_returns_false(self, ctx):
        _, index_service, _, _ = _build(ctx, None)
        assert index_service.process_photo(99999) is False

    def test_embedding_without_vector_index_keeps_face(self, ctx, photo_dir):
        photo_service, index_service, engine, _ = _build(ctx, photo_dir, vector_index=None)
        engine._faces = [make_face()]
        photo = _add_photo(photo_service, photo_dir)
        assert index_service.process_photo(photo.id) is True
        faces = FaceRepository(ctx.db).get_by_photo(photo.id)
        assert len(faces) == 1
        assert faces[0]["vector_id"] is None


class TestSubmit:
    def test_submit_photo_enqueues(self, ctx, photo_dir):
        photo_service, index_service, _, _ = _build(ctx, photo_dir)
        photo = _add_photo(photo_service, photo_dir)
        assert index_service.submit_photo(photo) is True
        assert index_service.queue_size() == 1

    def test_submit_done_photo_skipped(self, ctx, photo_dir):
        photo_service, index_service, engine, _ = _build(ctx, photo_dir)
        photo = _add_photo(photo_service, photo_dir)
        index_service.process_photo(photo.id)  # 置为 done
        assert index_service.submit_photo(photo) is False

    def test_submit_in_flight_skipped(self, ctx, photo_dir):
        photo_service, index_service, _, _ = _build(ctx, photo_dir)
        photo = _add_photo(photo_service, photo_dir)
        assert index_service.submit_photo(photo) is True
        assert index_service.submit_photo(photo) is False  # 已在处理中

    def test_submit_path_unknown_returns_false(self, ctx):
        _, index_service, _, _ = _build(ctx, None)
        assert index_service.submit_path("/no/such/photo.jpg") is False


class TestEndToEndWithWorker:
    def test_worker_consumes_queue(self, ctx, photo_dir):
        photo_service, index_service, engine, vindex = _build(ctx, photo_dir)
        engine._faces = [make_face()]
        photo = _add_photo(photo_service, photo_dir)

        index_service.start()
        index_service.submit_photo(photo)
        deadline = time.time() + 5
        while time.time() < deadline:
            if PhotoRepository(ctx.db).get_by_id(photo.id).status == PhotoStatus.DONE.value:
                break
            time.sleep(0.02)
        index_service.stop()

        updated = PhotoRepository(ctx.db).get_by_id(photo.id)
        assert updated.status == PhotoStatus.DONE.value
        assert vindex.size() == 1
