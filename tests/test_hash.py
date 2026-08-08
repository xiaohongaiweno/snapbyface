"""文件哈希工具测试。"""
from __future__ import annotations

from utils.hash import hash_bytes, hash_file


def test_hash_file_consistent(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello world" * 1000)
    assert hash_file(f) == hash_file(f)


def test_hash_differs_for_different_content(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"abc")
    b.write_bytes(b"abd")
    assert hash_file(a) != hash_file(b)


def test_hash_large_file(tmp_path):
    f = tmp_path / "big.bin"
    f.write_bytes(b"x" * (3 * 1024 * 1024 + 17))  # 跨多个 1MB chunk
    assert hash_file(f) == hash_bytes(b"x" * (3 * 1024 * 1024 + 17))


def test_hash_algorithm_arg(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"data")
    assert len(hash_file(f, "md5")) == 32


def test_hash_bytes():
    assert hash_bytes(b"abc") == hash_bytes(b"abc")
    assert hash_bytes(b"abc") != hash_bytes(b"abd")
