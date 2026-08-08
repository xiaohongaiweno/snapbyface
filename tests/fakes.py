"""Phase 3/4 测试共用的假引擎与假向量索引。"""
from __future__ import annotations

import numpy as np

from core.ai.base import DetectedFace


class FakeFaceEngine:
    """可配置返回人脸或抛异常的假引擎。"""

    def __init__(self, faces: list[DetectedFace] | None = None, fail: bool = False) -> None:
        self._faces = faces if faces is not None else []
        self._fail = fail
        self.calls = 0

    def detect(self, image):
        self.calls += 1
        if self._fail:
            raise RuntimeError("fake detect failed")
        return self._faces

    def embedding(self, image, face):
        return face.embedding

    def process(self, image):
        self.calls += 1
        if self._fail:
            raise RuntimeError("fake engine failed")
        return self._faces


class FakeVectorIndex:
    """内存版向量索引，用于测试（Phase 5 用 FAISS 替代）。"""

    dim = 512

    def __init__(self) -> None:
        self.data: dict[str, np.ndarray] = {}

    def add_vector(self, vector_id, vector) -> None:
        self.data[vector_id] = np.asarray(vector, dtype=np.float32)

    def search(self, vector, top_k=10):
        scores = []
        v = np.asarray(vector, dtype=np.float32)
        for vid, vec in self.data.items():
            sim = float(np.dot(v, vec))
            scores.append((vid, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def delete(self, vector_id) -> None:
        self.data.pop(vector_id, None)

    def size(self) -> int:
        return len(self.data)


def make_test_image(path, size=(64, 64), color=(128, 128, 128)) -> str:
    """生成一张可被 cv2 读取的测试图片，可通过 color 区分内容。"""
    import cv2

    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = color
    cv2.imwrite(str(path), img)
    return str(path)


def make_face(embedding: bool = True, score: float = 0.95) -> DetectedFace:
    vec = np.random.RandomState(0).normal(size=512).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return DetectedFace(
        bbox=(10, 10, 60, 60),
        embedding=vec if embedding else None,
        quality=score,
        det_score=score,
    )
