"""文件监听服务单元测试。"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from services.watcher_service import PhotoEventHandler, WatcherService


class TestPhotoEventHandler:
    @pytest.fixture
    def handler(self):
        events = []
        h = PhotoEventHandler(events.append, {".jpg", ".jpeg", ".png"})
        return h, events

    class _FakeEvent:
        def __init__(self, path, is_dir=False):
            self.src_path = path
            self.dest_path = path
            self.is_directory = is_dir

    def test_created_photo_callback(self, handler):
        h, events = handler
        h.on_created(self._FakeEvent("/x/photo.jpg"))
        assert events == [Path("/x/photo.jpg")]

    def test_modified_photo_callback(self, handler):
        h, events = handler
        h.on_modified(self._FakeEvent("/x/photo.png"))
        assert events == [Path("/x/photo.png")]

    def test_moved_photo_callback(self, handler):
        h, events = handler
        ev = self._FakeEvent("/x/photo.jpg")
        ev.dest_path = "/x/renamed.jpg"
        h.on_moved(ev)
        assert events == [Path("/x/renamed.jpg")]

    def test_non_photo_ignored(self, handler):
        h, events = handler
        h.on_created(self._FakeEvent("/x/notes.txt"))
        h.on_created(self._FakeEvent("/x/photo.gif"))
        assert events == []

    def test_directory_ignored(self, handler):
        h, events = handler
        h.on_created(self._FakeEvent("/x/dir", is_dir=True))
        assert events == []


class TestWatcherServiceIntegration:
    def test_start_without_directory_raises(self, ctx):
        w = WatcherService(ctx.config, lambda p: None)
        with pytest.raises(ValueError):
            w.start()

    def test_watchdog_notifies_new_file(self, ctx, photo_dir):
        ctx.config.set("photo.directory", str(photo_dir))
        events = []
        watcher = WatcherService(ctx.config, events.append)
        watcher.start()

        try:
            (photo_dir / "new.jpg").write_bytes(b"image-data")
            deadline = time.time() + 5
            while time.time() < deadline and not events:
                time.sleep(0.05)
        finally:
            watcher.stop()

        assert any(str(e).endswith("new.jpg") for e in events)

    def test_stop_stops_observer(self, ctx, photo_dir):
        ctx.config.set("photo.directory", str(photo_dir))
        watcher = WatcherService(ctx.config, lambda p: None)
        watcher.start()
        assert watcher.is_running
        watcher.stop()
        assert not watcher.is_running
