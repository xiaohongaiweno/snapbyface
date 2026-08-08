"""FAISS 向量索引单元测试。"""
from __future__ import annotations

import numpy as np
import pytest

from core.vector.faiss_index import FaissIndex


def _unit_vector(seed, dim=512):
    rng = np.random.RandomState(seed)
    v = rng.normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def idx(tmp_path) -> FaissIndex:
    return FaissIndex(dim=512, index_path=tmp_path / "data" / "face_index")


class TestAddSearch:
    def test_add_and_search_returns_id(self, idx):
        idx.add_vector("a", _unit_vector(1))
        results = idx.search(_unit_vector(1), top_k=5)
        assert results[0][0] == "a"

    def test_search_order_by_similarity(self, idx):
        v1 = _unit_vector(1)
        idx.add_vector("a", v1)
        idx.add_vector("b", _unit_vector(2))
        idx.add_vector("c", v1)  # 与 a 相同向量

        results = idx.search(v1, top_k=3)
        ids = [r[0] for r in results]
        assert ids[0] == "a" or ids[0] == "c"  # 相似度最高
        assert set(ids[:2]) == {"a", "c"}

    def test_cosine_score_close_to_one_for_same_vector(self, idx):
        v = _unit_vector(7)
        idx.add_vector("same", v)
        _, score = idx.search(v, top_k=1)[0]
        assert score > 0.99

    def test_size(self, idx):
        assert idx.size() == 0
        idx.add_vector("a", _unit_vector(1))
        idx.add_vector("b", _unit_vector(2))
        assert idx.size() == 2

    def test_empty_search_returns_empty(self, idx):
        assert idx.search(_unit_vector(1), top_k=5) == []

    def test_dim_mismatch_raises(self, idx):
        with pytest.raises(ValueError):
            idx.add_vector("x", np.zeros(128, dtype=np.float32))

    def test_add_replaces_existing_id(self, idx):
        idx.add_vector("a", _unit_vector(1))
        idx.add_vector("a", _unit_vector(2))  # 替换
        assert idx.size() == 1
        results = idx.search(_unit_vector(2), top_k=1)
        assert results[0][0] == "a"


class TestDelete:
    def test_delete_removes(self, idx):
        idx.add_vector("a", _unit_vector(1))
        idx.add_vector("b", _unit_vector(2))
        idx.delete("a")
        assert idx.size() == 1
        results = idx.search(_unit_vector(1), top_k=3)
        assert all(r[0] != "a" for r in results)

    def test_delete_nonexistent_is_noop(self, idx):
        idx.delete("nope")  # 不报错

    def test_delete_then_reuse_id(self, idx):
        idx.add_vector("a", _unit_vector(1))
        idx.delete("a")
        idx.add_vector("a", _unit_vector(3))
        assert idx.size() == 1
        assert idx.search(_unit_vector(3), top_k=1)[0][0] == "a"


class TestPersistence:
    def test_save_load_roundtrip(self, idx):
        v = _unit_vector(11)
        idx.add_vector("a", v)
        idx.add_vector("b", _unit_vector(12))

        loaded = FaissIndex(dim=512, index_path=idx._path)
        assert loaded.size() == 2
        results = loaded.search(v, top_k=1)
        assert results[0][0] == "a"

    def test_load_missing_file_starts_empty(self, tmp_path):
        idx = FaissIndex(dim=512, index_path=tmp_path / "nope")
        assert idx.size() == 0

    def test_clear(self, idx):
        idx.add_vector("a", _unit_vector(1))
        idx.clear()
        assert idx.size() == 0
        assert idx.search(_unit_vector(1)) == []
