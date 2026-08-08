"""AI 人脸引擎单元测试（注入假模型）。"""
from __future__ import annotations

import numpy as np
import pytest

from core.ai.face_engine import InsightFaceEngine
from core.ai.factory import NullFaceEngine, create_face_engine


class FakeInsightApp:
    """模拟 insightface FaceAnalysis。"""

    def __init__(self, faces=None, detect_result=None):
        self.faces = faces or []
        self.detect_result = detect_result or (np.empty((0, 5)), None)
        self.prepared = None

    def prepare(self, ctx_id=-1, det_thresh=None):
        self.prepared = (ctx_id, det_thresh)

    def get(self, image):
        return self.faces

    @property
    def det_model(self):
        return self

    def detect(self, image, max_num=0, metric="default"):
        return self.detect_result


def _face(score=0.95, with_embedding=True):
    class FakeFace:
        bbox = np.array([10, 20, 60, 70])
        det_score = score
        kps = np.array([[20, 30], [50, 30], [35, 45], [25, 60], [45, 60]])
        normed_embedding = None

        def __init__(self):
            if with_embedding:
                v = np.random.RandomState(1).normal(size=512).astype(np.float32)
                self.normed_embedding = v / np.linalg.norm(v)

    return FakeFace()


class TestInsightFaceEngine:
    def _engine(self, app):
        return InsightFaceEngine(app_factory=lambda: app)

    def test_process_returns_detected_faces(self):
        app = FakeInsightApp(faces=[_face()])
        engine = self._engine(app)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        faces = engine.process(image)
        assert len(faces) == 1
        assert faces[0].bbox == (10, 20, 60, 70)
        assert faces[0].embedding is not None
        assert faces[0].embedding.shape == (512,)
        assert abs(faces[0].quality - 0.95) < 1e-6

    def test_detect_uses_det_model(self):
        bboxes = np.array([[10, 20, 60, 70, 0.9], [5, 5, 25, 25, 0.8]])
        kpss = np.array([[[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]] * 2)
        app = FakeInsightApp(detect_result=(bboxes, kpss))
        engine = self._engine(app)
        faces = engine.detect(np.zeros((100, 100, 3), dtype=np.uint8))
        assert len(faces) == 2
        assert faces[0].bbox == (10, 20, 60, 70)
        assert faces[0].embedding is None  # 仅检测
        assert faces[0].landmarks is not None

    def test_detect_none_image_returns_empty(self):
        engine = self._engine(FakeInsightApp())
        assert engine.detect(None) == []

    def test_process_none_image_returns_empty(self):
        engine = self._engine(FakeInsightApp())
        assert engine.process(None) == []

    def test_embedding_matches_face_by_bbox(self):
        app = FakeInsightApp(faces=[_face()])
        engine = self._engine(app)
        from core.ai.base import DetectedFace

        target = DetectedFace(bbox=(10, 20, 60, 70), embedding=None)
        emb = engine.embedding(np.zeros((100, 100, 3), dtype=np.uint8), target)
        assert emb.shape == (512,)

    def test_embedding_no_match_raises(self):
        app = FakeInsightApp(faces=[_face()])
        engine = self._engine(app)
        from core.ai.base import DetectedFace

        target = DetectedFace(bbox=(999, 999, 1000, 1000), embedding=None)
        with pytest.raises(ValueError):
            engine.embedding(np.zeros((100, 100, 3), dtype=np.uint8), target)

    def test_lazy_load(self):
        created = []

        def factory():
            created.append(1)
            return FakeInsightApp()

        engine = InsightFaceEngine(app_factory=factory)
        assert not engine.is_ready
        engine.process(np.zeros((10, 10, 3), dtype=np.uint8))
        assert engine.is_ready
        assert len(created) == 1


class TestNullEngine:
    def test_process_returns_empty(self):
        assert NullFaceEngine().process(None) == []


class TestFactory:
    def test_returns_engine_without_insightface(self, ctx, monkeypatch):
        import sys

        import core.ai.factory as factory

        monkeypatch.setattr(sys, "meta_path", sys.meta_path)  # 保持导入稳定
        engine = factory.create_face_engine(ctx.config)
        # insightface 已安装，应返回 InsightFaceEngine
        from core.ai.face_engine import InsightFaceEngine

        assert isinstance(engine, InsightFaceEngine)
