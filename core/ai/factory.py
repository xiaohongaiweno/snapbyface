"""AI 引擎工厂：根据配置创建引擎，并保证无模型时应用可运行。"""
from __future__ import annotations

from typing import Any

import numpy as np

from core.config import ConfigManager
from core.logger import get_logger

logger = get_logger("ai.factory")


class NullFaceEngine:
    """AI 不可用时的空实现：不检测任何人脸。

    保证软件在没有下载模型的情况下也能正常启动和扫描。
    """

    def detect(self, image: np.ndarray) -> list:
        return []

    def embedding(self, image: np.ndarray, face: Any) -> np.ndarray:
        raise RuntimeError("AI 引擎不可用")

    def process(self, image: np.ndarray) -> list:
        return []


def create_face_engine(config: ConfigManager, model_root: str | Path | None = None) -> Any:
    """根据配置创建人脸引擎。

    - 配置 ai.model_dir 指向已下载模型根目录时优先使用
    - 否则使用当前目录下 data/（data/models/<name>）
    - insightface 不可用时回退 NullFaceEngine
    """
    from core.ai.face_engine import InsightFaceEngine
    from core.paths import get_model_root

    try:
        import insightface  # noqa: F401

        if model_root is None:
            model_root = config.get("ai.model_dir") or get_model_root()
        det_thresh = config.get("face.det_thresh")
        engine = InsightFaceEngine(
            model_name="buffalo_l",
            ctx_id=-1,
            det_thresh=float(det_thresh) if det_thresh else None,
            model_root=model_root,
        )
        logger.info("已创建 InsightFaceEngine，模型根目录=%s", model_root)
        return engine
    except Exception as exc:  # noqa: BLE001 - 任何原因降级
        logger.warning("AI 引擎不可用，使用空引擎: %s", exc)
        return NullFaceEngine()
