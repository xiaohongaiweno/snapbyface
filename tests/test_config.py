"""配置系统单元测试。"""
from __future__ import annotations

import json

import pytest

from core.config import DEFAULT_CONFIG, ConfigManager, deep_merge


@pytest.fixture
def config(tmp_path) -> ConfigManager:
    return ConfigManager(tmp_path / "config.json")


class TestDefaults:
    def test_default_face_threshold(self, config):
        assert config.get("face.threshold") == 0.80

    def test_default_trial_days(self, config):
        assert config.get("license.trial_days") == 15

    def test_default_telemetry_settings(self, config):
        assert config.get("telemetry.enabled") is True
        assert config.get("telemetry.endpoint") == "https://snapbyface.com/api/v1/telemetry"
        assert config.get("telemetry.timeout_seconds") == 3

    def test_default_photo_extensions(self, config):
        extensions = config.get("photo.extensions")
        assert ".jpg" in extensions
        assert ".cr2" in extensions
        assert ".nef" in extensions
        assert ".mp4" not in extensions

    def test_missing_key_returns_default(self, config):
        assert config.get("no.such.key", "fallback") == "fallback"

    def test_missing_key_returns_none(self, config):
        assert config.get("no.such.key") is None


class TestReadWrite:
    def test_set_get_roundtrip(self, config):
        config.set("face.threshold", 0.90)
        assert config.get("face.threshold") == 0.90

    def test_set_save_load_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        c1 = ConfigManager(path)
        c1.set("photo.directory", "D:/SnapPhotos")
        c1.save()
        assert path.exists()

        c2 = ConfigManager(path)
        assert c2.get("photo.directory") == "D:/SnapPhotos"

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "deep" / "config.json"
        c = ConfigManager(path)
        c.set("photo.directory", "x")
        c.save()
        assert path.exists()

    def test_get_returns_copy(self, config):
        exts = config.get("photo.extensions")
        exts.append(".example")
        assert ".example" not in config.get("photo.extensions")


class TestLoadMerge:
    def test_user_values_override_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"face": {"threshold": 0.95}}), encoding="utf-8")
        config = ConfigManager(path)
        assert config.get("face.threshold") == 0.95
        # 未覆盖的默认值保留
        assert config.get("license.trial_days") == 15

    def test_invalid_json_falls_back_to_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{ not valid json", encoding="utf-8")
        config = ConfigManager(path)
        assert config.get("face.threshold") == 0.80


class TestDeepMerge:
    def test_nested_merge(self):
        merged = deep_merge(
            {"a": {"b": 1, "c": 2}, "d": 3},
            {"a": {"c": 9}, "e": 5},
        )
        assert merged == {"a": {"b": 1, "c": 9}, "d": 3, "e": 5}

    def test_deep_merge_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        deep_merge(base, {"a": {"b": 2}})
        assert base["a"]["b"] == 1

    def test_defaults_are_not_shared(self):
        c1 = ConfigManager(__import__("tempfile").mkdtemp() + "/c.json")
        c2 = ConfigManager(__import__("tempfile").mkdtemp() + "/c.json")
        c1.set("photo.extensions", [".gif"])
        assert c2.get("photo.extensions") == DEFAULT_CONFIG["photo"]["extensions"]
