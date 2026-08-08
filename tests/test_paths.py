"""路径解析单元测试。"""
from __future__ import annotations

from pathlib import Path

from core import paths


class TestGetAppDir:
    def test_explicit_takes_priority(self):
        assert paths.get_app_dir("/tmp/xyz") == Path("/tmp/xyz")

    def test_env_var(self, app_dir, monkeypatch):
        assert paths.get_app_dir() == Path(app_dir)

    def test_env_overrides_explicit_default(self, app_dir, monkeypatch):
        # env 生效
        assert paths.get_app_dir() == Path(app_dir)

    def test_default_home(self, monkeypatch):
        monkeypatch.delenv("SNAPBYFACE_HOME", raising=False)
        assert paths.get_app_dir() == Path.home() / ".snapbyface"


class TestSubPaths:
    def test_config_path(self):
        assert paths.get_config_path("/a") == Path("/a/config.json")

    def test_log_dir(self):
        assert paths.get_log_dir("/a") == Path("/a/logs")

    def test_data_dir(self):
        assert paths.get_data_dir("/a") == Path("/a/data")

    def test_default_db_path(self):
        assert paths.get_default_db_path("/a") == Path("/a/data/snapbyface.db")

    def test_default_faiss_path(self):
        assert paths.get_default_faiss_path("/a") == Path("/a/data/face_index.faiss")
