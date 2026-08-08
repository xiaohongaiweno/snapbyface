"""UI 冒烟测试：确认窗口与页面可构建、导航正常。"""
from __future__ import annotations

from app.application import Application
from ui.main_window import MainWindow


def _build(app_dir):
    app = Application(app_dir)
    window = MainWindow(app)
    return app, window


class TestMainWindow:
    def test_window_has_six_pages(self, qapp, app_dir):
        _, window = _build(app_dir)
        assert window.stack.count() == 6
        assert set(window._pages.keys()) == {"home", "search", "index", "settings", "license", "logs"}

    def test_navigation(self, qapp, app_dir):
        _, window = _build(app_dir)
        window.navigate_to("search")
        assert window.stack.currentWidget() is window._pages["search"]
        window.navigate_to("logs")
        assert window.stack.currentWidget() is window._pages["logs"]

    def test_nav_list_row_changes_page(self, qapp, app_dir):
        _, window = _build(app_dir)
        window.nav.setCurrentRow(2)  # 索引状态
        assert window.stack.currentWidget() is window._pages["index"]

    def test_show_message(self, qapp, app_dir):
        _, window = _build(app_dir)
        window.show_message("hello")
        assert "hello" in window.status.currentMessage()


class TestApplicationBackground:
    def test_start_background_no_directory_warns_not_crash(self, qapp, app_dir):
        app = Application(app_dir)
        app.start_background(watch=True)
        app.shutdown()

    def test_start_background_with_directory(self, qapp, app_dir, photo_dir):
        app = Application(app_dir)
        app.ctx.config.set("photo.directory", str(photo_dir))
        app.ctx.config.set("photo.watch_enabled", False)
        app.start_background(watch=False)
        # 启动扫描应该发现空目录下的 0 张照片
        assert app.photo_service.get_stats()["total"] == 0
        app.shutdown()

    def test_photo_file_changed_imports_and_submits(self, qapp, app_dir, photo_dir):
        app = Application(app_dir)
        app.ctx.config.set("photo.directory", str(photo_dir))
        submitted = []

        class FakeIndexService:
            def submit_photo(self, photo):
                submitted.append(photo)
                return True

            def stop(self):
                pass

        app.index_service = FakeIndexService()
        path = photo_dir / "live.jpg"
        path.write_bytes(b"live")
        app._on_photo_file_changed(path)
        assert submitted
        assert submitted[0].file_name == "live.jpg"
        app.shutdown()

    def test_refresh_photo_directory_scans_and_enqueues(self, qapp, app_dir, photo_dir):
        app = Application(app_dir)
        app.ctx.config.set("photo.directory", str(photo_dir))
        (photo_dir / "a.jpg").write_bytes(b"a")
        summary = app.refresh_photo_directory(watch=False)
        assert summary["total_files"] == 1
        assert summary["new_photos"] == 1
        assert summary["enqueued"] == 1
        assert app.photo_service.get_stats()["pending"] == 1
        app.shutdown()
