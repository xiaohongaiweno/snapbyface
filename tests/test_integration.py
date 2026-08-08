"""端到端集成测试：扫描 → 索引 → 搜索 全链路。

使用假人脸引擎（避免依赖模型下载），其余全部走真实实现
（SQLite、FaissIndex、ScannerWorker、IndexService、SearchService）。
"""
from __future__ import annotations

import time

import numpy as np
import pytest

import app.application as app_mod
from core.ai.base import DetectedFace
from models.photo import PhotoStatus
from tests.fakes import FakeFaceEngine, make_test_image


@pytest.fixture
def app_with_engine(app_dir, photo_dir, monkeypatch):
    """构建注入假引擎的完整 Application。"""
    engine = FakeFaceEngine(faces=[DetectedFace(bbox=(5, 5, 40, 40), embedding=_unit(7))])
    monkeypatch.setattr(app_mod, "create_face_engine", lambda config: engine)

    app = app_mod.Application(app_dir)
    app.ctx.config.set("photo.directory", str(photo_dir))
    app.ctx.config.set("photo.watch_enabled", False)
    app.ctx.config.set("photo.scan_interval", None)
    return app, engine


def _unit(seed, dim=512):
    rng = np.random.RandomState(seed)
    v = rng.normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


class TestFullPipeline:
    def test_scan_index_search(self, qapp, app_with_engine, photo_dir):
        app, engine = app_with_engine

        # 准备照片
        make_test_image(photo_dir / "tourist.jpg", color=(10, 20, 30))
        make_test_image(photo_dir / "other.jpg", color=(200, 200, 10))

        # 启动后台：扫描 + 索引
        app.start_background(watch=False)

        # 等待索引完成（2 张照片都应为 done）
        deadline = time.time() + 10
        while time.time() < deadline:
            stats = app.photo_service.get_stats()
            if stats["done"] == 2 and stats["indexing"] == 0 and stats["pending"] == 0:
                break
            time.sleep(0.05)
        stats = app.photo_service.get_stats()
        assert stats["done"] == 2, f"索引未完成: {stats}"

        # 向量索引中有 2 个向量（每张照片 1 个人脸）
        assert app.vector_index.size() == 2

        # 用与 tourist 相同的人脸特征检索
        results = app.search_service.search_embedding(_unit(7), top_k=5)
        assert len(results) >= 1
        top = results[0]
        assert top.file_name == "tourist.jpg"
        assert top.similarity > 0.99

        # 按图搜索也命中
        results_by_image = app.search_service.search_image(
            np.zeros((64, 64, 3), dtype=np.uint8)
        )
        assert any(r.file_name == "tourist.jpg" for r in results_by_image)

        app.shutdown()

    def test_incremental_rescan_no_duplicates(self, qapp, app_with_engine, photo_dir):
        app, engine = app_with_engine
        make_test_image(photo_dir / "a.jpg")

        app.start_background(watch=False)
        deadline = time.time() + 10
        while time.time() < deadline:
            if app.photo_service.get_stats()["done"] == 1:
                break
            time.sleep(0.05)

        # 再次全量扫描：不产生重复向量
        app.photo_service.scan()
        assert app.vector_index.size() == 1
        assert app.photo_service.get_stats()["total"] == 1

        app.shutdown()
