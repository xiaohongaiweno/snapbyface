"""应用组合根：装配全部服务与后台任务。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bootstrap import AppContext, create_application
from core.ai.factory import create_face_engine
from core.logger import get_logger
from core.paths import get_default_faiss_path
from core.vector.faiss_index import FaissIndex
from repositories.operation_log_repository import OperationLogRepository
from repositories.photo_repository import PhotoRepository
from services.camera_service import CameraService
from services.index_service import IndexService
from services.license_service import LicenseService
from services.photo_service import PhotoService
from services.search_service import SearchService
from services.telemetry_service import TelemetryService
from services.watcher_service import WatcherService
from viewmodels.license_viewmodel import LicenseViewModel
from workers.scanner_worker import ScannerWorker


class Application:
    """桌面应用组合根。"""

    def __init__(self, app_dir: Path | str | None = None) -> None:
        self.ctx: AppContext = create_application(app_dir)
        self.logger = get_logger("app")

        # 核心引擎
        self.face_engine = create_face_engine(self.ctx.config)
        faiss_path = self.ctx.config.get("faiss.index_path") or str(
            get_default_faiss_path(self.ctx.app_dir)
        )
        self.vector_index: Any = FaissIndex(
            dim=int(self.ctx.config.get("faiss.dim", 512)),
            index_path=faiss_path,
        )

        # 服务
        self.photo_service = PhotoService(self.ctx.db, self.ctx.config)
        self.index_service = IndexService(
            self.ctx.db, self.ctx.config, self.face_engine, self.vector_index
        )
        self.search_service = SearchService(
            self.face_engine, self.vector_index, self.ctx.db, self.ctx.config
        )
        self.camera_service = CameraService()
        self.op_log_repo = OperationLogRepository(self.ctx.db)

        # 授权
        self.license_service = LicenseService(
            self.ctx.db, self.ctx.config, self.ctx.app_dir
        )
        self.license_viewmodel = LicenseViewModel(self.license_service)
        self.telemetry_service = TelemetryService(self.ctx.config, self.license_service)

        # 后台任务（延迟到 start_background）
        self.scanner_worker: ScannerWorker | None = None
        self.watcher_service: WatcherService | None = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def report_startup_telemetry(self) -> None:
        """尝试异步上报启动遥测，不影响主流程。"""
        self.telemetry_service.report_startup_async()

    def start_background(self, watch: bool = True) -> None:
        """启动索引 Worker、启动扫描、目录监听。"""
        self.index_service.start()

        interval = self.ctx.config.get("photo.scan_interval")
        self.scanner_worker = ScannerWorker(
            self.photo_service,
            self.index_service,
            interval=float(interval) if interval else None,
        )
        self.scanner_worker.start()

        if watch and self.ctx.config.get("photo.watch_enabled", True):
            self._restart_watcher()

    def refresh_photo_directory(self, watch: bool = True) -> dict[str, int]:
        """配置照片目录变更后立即扫描，并切换实时监听目录。"""
        result = self.photo_service.scan()
        pending = PhotoRepository(self.ctx.db).pending_photos(limit=5000)
        enqueued = 0
        for photo in pending:
            if self.index_service.submit_photo(photo):
                enqueued += 1

        if watch and self.ctx.config.get("photo.watch_enabled", True):
            self._restart_watcher()

        self.logger.info(
            "照片目录已刷新: 文件=%d 新增=%d 更新=%d 入队=%d",
            result.total_files,
            result.new_photos,
            result.updated,
            enqueued,
        )
        return {
            "total_files": result.total_files,
            "new_photos": result.new_photos,
            "updated": result.updated,
            "enqueued": enqueued,
        }

    def _restart_watcher(self) -> None:
        """重启目录监听，使其绑定到最新照片目录。"""
        if self.watcher_service is not None:
            self.watcher_service.stop()
            self.watcher_service = None
        try:
            self.watcher_service = WatcherService(
                self.ctx.config,
                self._on_photo_file_changed,
                on_file_deleted=self.index_service.remove_photo_by_path,
            )
            self.watcher_service.start()
        except (ValueError, NotADirectoryError) as exc:
            self.logger.warning("未启动目录监听: %s", exc)

    def _on_photo_file_changed(self, path: Path) -> None:
        """实时监听到照片后，先入库，再立即提交索引。"""
        photo = self.photo_service.import_file(path)
        if photo is None:
            self.logger.warning("监听到照片但未能入库: %s", path)
            return
        if self.index_service.submit_photo(photo):
            self.logger.info("实时照片已提交索引: %s", path)
        else:
            self.logger.info("实时照片无需重复提交索引: %s", path)

    def shutdown(self) -> None:
        """停止所有后台任务并关闭资源。"""
        if self.watcher_service is not None:
            self.watcher_service.stop()
        if self.scanner_worker is not None:
            self.scanner_worker.stop()
        self.index_service.stop()
        self.camera_service.stop()
        self.ctx.db.close()
        self.logger.info("应用已关闭")
