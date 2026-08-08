"""应用装配单元测试。"""
from __future__ import annotations

from pathlib import Path

from app.bootstrap import create_application
from core.config import DEFAULT_CONFIG


class TestCreateApplication:
    def test_creates_config_log_db(self, app_dir):
        ctx = create_application(app_dir)
        assert ctx.app_dir == Path(app_dir)
        assert (Path(app_dir) / "config.json").exists()
        assert (Path(app_dir) / "logs" / "snapbyface.log").exists()
        assert ctx.db.db_path.exists()

    def test_context_exposes_deps(self, app_dir):
        ctx = create_application(app_dir)
        assert ctx.config.get("face.threshold") == DEFAULT_CONFIG["face"]["threshold"]
        assert ctx.logger.name == "snapbyface.app"
        # 数据库可读写
        ctx.db.execute(
            "INSERT INTO photo (path, file_name, hash) VALUES (?,?,?)",
            ("/boot.jpg", "boot.jpg", "h0"),
        )
        assert ctx.db.scalar("SELECT COUNT(*) FROM photo") == 1

    def test_custom_database_path_in_config(self, app_dir):
        ctx = create_application(app_dir)
        custom = ctx.app_dir / "custom" / "x.db"
        ctx.config.set("database.path", str(custom))
        ctx.config.save()

        ctx2 = create_application(app_dir)
        assert ctx2.db.db_path == custom
        assert custom.exists()
