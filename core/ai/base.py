"""人脸/向量相关数据模型与协议。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass
class DetectedFace:
    """检测到的一张人脸。"""

    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    embedding: np.ndarray | None = None  # 512 维特征（仅 embedding 阶段有）
    quality: float = 0.0
    det_score: float = 0.0
    landmarks: list[tuple[float, float]] | None = None


class FaceEngine(Protocol):
    """AI 人脸引擎协议（规格 §7：SCRFD 检测 + ArcFace 特征）。

    Phase 4 提供 insightface 实现；本协议保证可替换与可测试。
    """

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        """检测图像中的人脸（只定位）。"""
        ...

    def embedding(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        """对已检测人脸提取 512 维特征。"""
        ...

    def process(self, image: np.ndarray) -> list[DetectedFace]:
        """完整流程：检测 + 对齐 + 特征提取。"""
        ...
