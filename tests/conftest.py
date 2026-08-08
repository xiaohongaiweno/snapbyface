"""pytest 全局夹具。"""
from __future__ import annotations

import os

import pytest

from app.bootstrap import create_application


@pytest.fixture(scope="session")
def qapp():
    """Qt 应用实例（offscreen 平台）。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    """独立的应用目录，并通过环境变量隔离。"""
    d = tmp_path / "app"
    d.mkdir()
    monkeypatch.setenv("SNAPBYFACE_HOME", str(d))
    return d


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """完整的应用上下文（配置+日志+数据库），落在临时目录。"""
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.setenv("SNAPBYFACE_HOME", str(app))
    return create_application(app)


@pytest.fixture
def photo_dir(tmp_path):
    """一个真实存在的照片目录。"""
    d = tmp_path / "photos"
    d.mkdir()
    return d
