"""文件系统监听服务（规格 §10 实时扫描）。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from core.config import ConfigManager
from core.logger import get_logger

NewFileCallback = Callable[[Path], None]


class PhotoEventHandler:
    """照片目录事件处理器，把新文件回调给上层。"""

    def __init__(
        self,
        callback: NewFileCallback,
        extensions: set[str],
        delete_callback: NewFileCallback | None = None,
        logger=None,
    ) -> None:
        self._callback = callback
        self._delete_callback = delete_callback
        self._extensions = {e.lower() for e in extensions}
        self._logger = logger or get_logger("watcher.handler")

    def _is_photo(self, path: str) -> bool:
        return Path(path).suffix.lower() in self._extensions

    def _handle(self, path: str) -> None:
        if not path or not self._is_photo(path):
            return
        self._logger.debug("文件变化: %s", path)
        try:
            self._callback(Path(path))
        except Exception:
            self._logger.exception("回调处理失败: %s", path)

    def _handle_delete(self, path: str) -> None:
        if not path or not self._is_photo(path) or self._delete_callback is None:
            return
        self._logger.debug("文件删除: %s", path)
        try:
            self._delete_callback(Path(path))
        except Exception:
            self._logger.exception("删除回调处理失败: %s", path)

    # watchdog 事件接口
    def on_created(self, event) -> None:
        if not event.is_directory:
            self._handle(getattr(event, "src_path", ""))

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._handle(getattr(event, "src_path", ""))

    def on_moved(self, event) -> None:
        if not event.is_directory:
            dest = getattr(event, "dest_path", "")
            src = getattr(event, "src_path", "")
            self._handle_delete(src)  # 旧路径视为删除
            self._handle(dest)        # 新路径视为新增

    def on_deleted(self, event) -> None:
        if not event.is_directory:
            self._handle_delete(getattr(event, "src_path", ""))


class WatcherService:
    """基于 watchdog 的实时监听。

    启动后监听照片目录（含子目录），新照片立即回调，
    文件删除时回调 on_file_deleted（清理索引）。
    """

    def __init__(
        self,
        config: ConfigManager,
        on_new_file: NewFileCallback,
        on_file_deleted: NewFileCallback | None = None,
        logger=None,
    ) -> None:
        self._config = config
        self._callback = on_new_file
        self._delete_callback = on_file_deleted
        self._logger = logger or get_logger("watcher")
        self._observer = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def _extensions(self) -> set[str]:
        exts = self._config.get("photo.extensions")
        return {str(e).lower() if str(e).startswith(".") else f".{str(e).lower()}" for e in exts}

    def start(self, directory: str | Path | None = None) -> Path:
        """启动监听。返回被监听的目录。"""
        raw = directory or self._config.get("photo.directory")
        if not raw:
            raise ValueError("尚未配置照片目录")
        target = Path(raw).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(f"目录不存在: {target}")

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
            from watchdog.observers.polling import PollingObserver
        except ImportError as exc:
            raise RuntimeError("缺少 watchdog 依赖，无法启用实时监听") from exc

        class _Handler(FileSystemEventHandler):
            def __init__(self, inner):
                self._inner = inner

            def on_created(self, event):
                self._inner.on_created(event)

            def on_modified(self, event):
                self._inner.on_modified(event)

            def on_moved(self, event):
                self._inner.on_moved(event)

            def on_deleted(self, event):
                self._inner.on_deleted(event)

        handler = _Handler(
            PhotoEventHandler(
                self._callback,
                self._extensions(),
                delete_callback=self._delete_callback,
                logger=self._logger,
            )
        )
        observer_cls = PollingObserver if sys.platform == "darwin" else Observer
        observer = observer_cls()
        observer.schedule(handler, str(target), recursive=True)
        observer.start()
        self._observer = observer
        self._logger.info("已开始监听目录: %s", target)
        return target

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._logger.info("监听已停止")
