"""搜索服务单元测试。"""
from __future__ import annotations

import numpy as np
import pytest

from models.photo import PhotoStatus
from repositories.face_repository import FaceRepository
from repositories.photo_repository import PhotoRepository
from services.photo_service import PhotoService
from services.search_service import SearchService
from core.vector.faiss_index import FaissIndex
from tests.fakes import FakeFaceEngine, make_test_image
from core.ai.base import DetectedFace


def _unit(seed, dim=512):
    rng = np.random.RandomState(seed)
    v = rng.normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _build(ctx, photo_dir, threshold=0.8):
    ctx.config.set("face.threshold", threshold)
    ctx.config.save()
    photo_service = PhotoService(ctx.db, ctx.config)
    photo_service.set_photo_directory(photo_dir)
    index = FaissIndex(dim=512, index_path=photo_dir.parent / "data" / "idx")
    engine = FakeFaceEngine()
    service = SearchService(engine, index, ctx.db, ctx.config)
    return photo_service, service, index, engine


def _add_photo(photo_service, photo_dir, name, vector):
    make_test_image(photo_dir / name, color=(0, 0, len(name) * 10))
    photo_service.scan()
    repo = PhotoRepository(photo_service._db)
    photo = repo.get_by_path(str(photo_dir / name))
    vid = f"vid_{name}"
    FaceRepository(photo_service._db).insert_face_with_embedding(
        photo.id, "[0,0,10,10]", 0.9, vid, dim=512
    )
    photo_service._db.execute(
        "UPDATE photo SET status=? WHERE id=?", (PhotoStatus.DONE.value, photo.id)
    )
    return photo, vid, vector


class TestSearchImage:
    def test_returns_best_matching_photo(self, ctx, photo_dir):
        photo_service, service, index, engine = _build(ctx, photo_dir)
        v1 = _unit(1)
        photo_a, vid_a, _ = _add_photo(photo_service, photo_dir, "a.jpg", v1)
        index.add_vector(vid_a, v1)

        # 游客拍到的人脸特征与 v1 相同
        engine._faces = [DetectedFace(bbox=(0, 0, 10, 10), embedding=v1)]
        results = service.search_image(np.zeros((64, 64, 3), dtype=np.uint8))
        assert len(results) == 1
        assert results[0].photo_id == photo_a.id
        assert results[0].similarity > 0.99

    def test_threshold_filters_low_similarity(self, ctx, photo_dir):
        photo_service, service, index, engine = _build(ctx, photo_dir, threshold=0.9)
        v1 = _unit(1)
        photo_a, vid_a, _ = _add_photo(photo_service, photo_dir, "a.jpg", v1)
        index.add_vector(vid_a, v1)

        # 相似度约 0.5 的查询被 0.9 阈值过滤
        query = _unit(2)
        results = service.search_embedding(query, top_k=5)
        assert results == []

    def test_dedup_by_photo(self, ctx, photo_dir):
        photo_service, service, index, engine = _build(ctx, photo_dir)
        v1 = _unit(1)
        photo_a, vid_a, _ = _add_photo(photo_service, photo_dir, "a.jpg", v1)
        vid_b = "vid_a2"
        FaceRepository(photo_service._db).insert_face_with_embedding(
            photo_a.id, "[5,5,20,20]", 0.85, vid_b, dim=512
        )
        index.add_vector(vid_a, v1)
        index.add_vector(vid_b, v1)  # 同一张照片两个人脸都命中

        results = service.search_embedding(v1, top_k=10)
        ids = [r.photo_id for r in results]
        assert ids.count(photo_a.id) == 1  # 去重后只保留一次
        assert len(results) == 1

    def test_search_image_no_faces_returns_empty(self, ctx, photo_dir):
        photo_service, service, index, engine = _build(ctx, photo_dir)
        engine._faces = []
        assert service.search_image(np.zeros((10, 10, 3), dtype=np.uint8)) == []

    def test_empty_index_returns_empty(self, ctx, photo_dir):
        _, service, _, engine = _build(ctx, photo_dir)
        engine._faces = [DetectedFace(bbox=(0, 0, 10, 10), embedding=_unit(1))]
        assert service.search_image(np.zeros((10, 10, 3), dtype=np.uint8)) == []

    def test_search_image_none(self, ctx, photo_dir):
        _, service, _, _ = _build(ctx, photo_dir)
        assert service.search_image(None) == []


class TestThreshold:
    def test_threshold_property(self, ctx, photo_dir):
        _, service, _, _ = _build(ctx, photo_dir, threshold=0.85)
        assert service.threshold == pytest.approx(0.85)
