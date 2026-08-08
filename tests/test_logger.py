"""日志系统单元测试。"""
from __future__ import annotations

from pathlib import Path

from core.config import ConfigManager
from core.logger import LOG_FILE_NAME, get_logger, setup_logging


def _config(tmp_path, **overrides) -> ConfigManager:
    cfg = ConfigManager(tmp_path / "config.json")
    for key, value in overrides.items():
        cfg.set(key, value)
    return cfg


class TestSetupLogging:
    def test_log_file_created_and_written(self, tmp_path):
        log_dir = tmp_path / "logs"
        cfg = _config(tmp_path)
        setup_logging(cfg, log_dir)

        logger = get_logger("test")
        logger.info("hello snapbyface")

        log_file = Path(log_dir) / LOG_FILE_NAME
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "hello snapbyface" in content

    def test_handlers_added(self, tmp_path):
        cfg = _config(tmp_path)
        root = setup_logging(cfg, tmp_path / "logs")
        assert len(root.handlers) == 2  # 控制台 + 文件

    def test_setup_is_idempotent_repoints_to_new_dir(self, tmp_path):
        dir1 = tmp_path / "logs1"
        dir2 = tmp_path / "logs2"
        cfg = _config(tmp_path)
        setup_logging(cfg, dir1)
        setup_logging(cfg, dir2)

        get_logger("test").info("second dir")
        assert Path(dir2 / LOG_FILE_NAME).exists()
        # 旧目录不再接收
        assert not Path(dir1 / LOG_FILE_NAME).exists() or \
            "second dir" not in Path(dir1 / LOG_FILE_NAME).read_text(encoding="utf-8")

    def test_rotating_handlers_configured(self, tmp_path):
        cfg = _config(tmp_path, **{"log.max_bytes": 1024, "log.backup_count": 3})
        root = setup_logging(cfg, tmp_path / "logs")
        from logging.handlers import RotatingFileHandler

        rotating = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(rotating) == 1
        assert rotating[0].maxBytes == 1024
        assert rotating[0].backupCount == 3


class TestGetLogger:
    def test_named_logger_is_child_of_root(self):
        assert get_logger("photo").name == "snapbyface.photo"
        assert get_logger().name == "snapbyface"
