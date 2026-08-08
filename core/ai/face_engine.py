"""基于 insightface 的人脸引擎（规格 §7：SCRFD + ArcFace）。

懒加载模型：首次调用时初始化，模型缺失时自动从网络下载
（规格 §3：网络仅用于下载模型/激活授权）。
"""
from __future__ import annotations

from typing import Any

import numpy as np

from core.ai.base import DetectedFace
from core.logger import get_logger

logger = get_logger("ai.face")


class InsightFaceEngine:
    """insightface 实现，满足 FaceEngine 协议。"""

    def __init__(
        self,
        model_name: str = "buffalo_l",
        ctx_id: int = -1,
        det_thresh: float | None = None,
        providers: list[str] | None = None,
        app_factory: Any = None,
        model_root: str | Path | None = None,
    ) -> None:
        self._model_name = model_name
        self._ctx_id = ctx_id
        self._det_thresh = det_thresh
        self._providers = providers
        self._model_root = model_root
        self._app = None
        self._app_factory = app_factory or self._default_app_factory

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------
    def _default_app_factory(self) -> Any:
        from insightface.app import FaceAnalysis

        kwargs: dict[str, Any] = dict(
            name=self._model_name,
            allowed_modules=["detection", "recognition"],
            providers=self._providers,
        )
        if self._model_root is not None:
            kwargs["root"] = str(self._model_root)
        app = FaceAnalysis(**kwargs)
        app.prepare(ctx_id=self._ctx_id, det_thresh=self._det_thresh)
        return app

    def _ensure_loaded(self) -> Any:
        if self._app is None:
            logger.info("加载人脸模型 %s ...", self._model_name)
            self._app = self._app_factory()
            logger.info("人脸模型加载完成")
        return self._app

    @property
    def is_ready(self) -> bool:
        return self._app is not None

    def _to_detected(self, face: Any) -> DetectedFace:
        bbox = tuple(int(v) for v in face.bbox[:4])
        embedding = None
        if hasattr(face, "normed_embedding") and face.normed_embedding is not None:
            embedding = np.asarray(face.normed_embedding, dtype=np.float32)
        landmarks = None
        if hasattr(face, "kps") and face.kps is not None:
            landmarks = [(float(x), float(y)) for x, y in face.kps]
        return DetectedFace(
            bbox=bbox,
            embedding=embedding,
            quality=float(getattr(face, "det_score", 0.0)),
            det_score=float(getattr(face, "det_score", 0.0)),
            landmarks=landmarks,
        )

    # ------------------------------------------------------------------
    # 协议接口
    # ------------------------------------------------------------------
    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        """仅检测人脸位置（SCRFD）。"""
        if image is None:
            return []
        app = self._ensure_loaded()
        try:
            bboxes, kpss = app.det_model.detect(image, max_num=0, metric="default")
        except AttributeError:
            # 某些版本 det_model API 不同，退化为完整流程后丢弃特征
            faces = app.get(image)
            return [self._to_detected(f) for f in faces]
        faces: list[DetectedFace] = []
        if bboxes is not None and len(bboxes) > 0:
            for idx, box in enumerate(bboxes):
                b = tuple(int(v) for v in box[:4])
                score = float(box[4]) if len(box) > 4 else 0.0
                kps = kpss[idx] if kpss is not None and idx < len(kpss) else None
                landmarks = [(float(x), float(y)) for x, y in kps] if kps is not None else None
                faces.append(
                    DetectedFace(bbox=b, quality=score, det_score=score, landmarks=landmarks)
                )
        return faces

    def embedding(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        """提取已定位人脸的 512 维特征。

        通过全图识别结果按 bbox 匹配目标人脸。
        """
        if image is None:
            raise ValueError("图像为空")
        app = self._ensure_loaded()
        target = np.array(face.bbox, dtype=int)
        best: tuple[float, DetectedFace] | None = None
        for f in app.get(image):
            det = self._to_detected(f)
            if det.embedding is None:
                continue
            overlap = self._bbox_overlap(target, np.array(det.bbox, dtype=int))
            if best is None or overlap > best[0]:
                best = (overlap, det)
        if best is None or best[0] <= 0:
            raise ValueError("未能在图像中匹配到目标人脸")
        return best[1].embedding

    def process(self, image: np.ndarray) -> list[DetectedFace]:
        """完整流程：检测 + 对齐 + 特征提取（ArcFace）。"""
        if image is None:
            return []
        app = self._ensure_loaded()
        faces = app.get(image)
        return [self._to_detected(f) for f in faces]

    @staticmethod
    def _bbox_overlap(a: np.ndarray, b: np.ndarray) -> float:
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))
        return inter / area_b
