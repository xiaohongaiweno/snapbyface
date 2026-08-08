"""基于 FAISS 的向量索引（规格 §18：IndexFlatIP）。

特征向量均为 L2 归一化，内积等价余弦相似度（规格 §9）。
向量 id 与位置映射保存在内存并持久化，删除时重建索引（V1 索引量级适用）。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

from core.logger import get_logger

logger = get_logger("vector.faiss")


class FaissIndex:
    """FAISS IndexFlatIP 封装，满足 VectorIndex 协议。"""

    def __init__(
        self,
        dim: int = 512,
        index_path: str | Path | None = None,
        logger=None,
    ) -> None:
        self._dim = int(dim)
        self._path = Path(index_path) if index_path else None
        self._logger = logger or get_logger("vector.faiss")
        self._lock = threading.Lock()

        self._index: Any = None
        self._ids: list[str] = []
        self._vectors: list[np.ndarray] = []
        self._id_to_pos: dict[str, int] = {}

        self._load()

    @property
    def dim(self) -> int:
        return self._dim

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def _paths(self) -> tuple[Path, Path, Path]:
        base = self._path
        return base.with_suffix(".faiss"), base.with_suffix(".json"), base.with_suffix(".npy")

    def _load(self) -> None:
        import faiss

        idx_path, _, _ = self._paths()
        if self._path is None or not idx_path.exists():
            self._index = faiss.IndexFlatIP(self._dim)
            return
        try:
            idx_path, ids_path, npy_path = self._paths()
            self._index = faiss.read_index(str(idx_path))
            self._ids = json.loads(ids_path.read_text(encoding="utf-8"))
            self._vectors = [np.asarray(v, dtype=np.float32) for v in np.load(npy_path)]
            self._id_to_pos = {vid: i for i, vid in enumerate(self._ids)}
            self._logger.info("已加载向量索引: %d 个向量 (%s)", len(self._ids), self._path)
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("向量索引加载失败，重建空索引: %s", exc)
            self._index = faiss.IndexFlatIP(self._dim)
            self._ids = []
            self._vectors = []
            self._id_to_pos = {}

    def save(self) -> None:
        """持久化索引到磁盘。"""
        if self._path is None:
            return
        idx_path, ids_path, npy_path = self._paths()
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        import faiss

        faiss.write_index(self._index, str(idx_path))
        ids_path.write_text(json.dumps(self._ids), encoding="utf-8")
        if self._vectors:
            np.save(npy_path, np.asarray(self._vectors, dtype=np.float32))
        elif npy_path.exists():
            npy_path.unlink()
        self._logger.debug("向量索引已保存: %d 个向量", len(self._ids))

    def _persist(self) -> None:
        self.save()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def add_vector(self, vector_id: str, vector: np.ndarray) -> None:
        """写入一个向量；id 已存在则替换（幂等）。"""
        vec = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if vec.shape[1] != self._dim:
            raise ValueError(f"向量维度 {vec.shape[1]} 与索引维度 {self._dim} 不符")
        vec_norm = vec / max(np.linalg.norm(vec), 1e-12)
        with self._lock:
            if vector_id in self._id_to_pos:
                self._delete_locked(vector_id)
            self._index.add(vec_norm)
            self._id_to_pos[vector_id] = len(self._ids)
            self._ids.append(vector_id)
            self._vectors.append(vec_norm.reshape(-1))
            self._persist()

    def delete(self, vector_id: str) -> None:
        """删除一个向量。"""
        with self._lock:
            self._delete_locked(vector_id)

    def _delete_locked(self, vector_id: str) -> None:
        pos = self._id_to_pos.pop(vector_id, None)
        if pos is None:
            return
        del self._ids[pos]
        del self._vectors[pos]
        self._id_to_pos = {vid: i for i, vid in enumerate(self._ids)}
        self._rebuild_index()
        self._persist()

    def clear(self) -> None:
        """清空索引。"""
        with self._lock:
            import faiss

            self._index = faiss.IndexFlatIP(self._dim)
            self._ids = []
            self._vectors = []
            self._id_to_pos = {}
            self._persist()

    def _rebuild_index(self) -> None:
        import faiss

        new_index = faiss.IndexFlatIP(self._dim)
        if self._vectors:
            new_index.add(np.asarray(self._vectors, dtype=np.float32))
        self._index = new_index

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def search(self, vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        """按相似度降序返回 [(vector_id, score)]。"""
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != self._dim:
            raise ValueError(f"查询向量维度 {query.shape[1]} 与索引维度 {self._dim} 不符")
        query_norm = query / max(np.linalg.norm(query), 1e-12)
        with self._lock:
            if self._index.ntotal == 0:
                return []
            scores, idxs = self._index.search(query_norm, top_k)
        results: list[tuple[str, float]] = []
        for score, pos in zip(scores[0], idxs[0]):
            if pos < 0 or pos >= len(self._ids):
                continue
            results.append((self._ids[pos], float(score)))
        return results

    def size(self) -> int:
        return len(self._ids)
