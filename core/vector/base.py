"""向量索引协议（规格 §18：FAISS IndexFlatIP）。"""
from __future__ import annotations

from typing import Protocol

import numpy as np


class VectorIndex(Protocol):
    """向量索引协议，Phase 5 用 FAISS 实现。"""

    dim: int

    def add_vector(self, vector_id: str, vector: np.ndarray) -> None:
        """写入一个向量。"""
        ...

    def search(self, vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        """按相似度降序返回 [(vector_id, score)]。"""
        ...

    def delete(self, vector_id: str) -> None:
        """删除一个向量。"""
        ...

    def size(self) -> int:
        """向量总数。"""
        ...
