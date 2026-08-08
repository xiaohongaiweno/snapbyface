"""照片服务：目录管理、扫描、hash 去重、增量扫描（规格 §12）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from core.config import ConfigManager
from core.logger import get_logger
from database.connection import Database
from models.photo import Photo, PhotoStatus
from repositories.photo_repository import PhotoRepository
from utils.hash import hash_file
from utils.image import read_captured_at

ProgressCallback = Callable[[int, int], None]


@dataclass
class ScanResult:
    """一次扫描的结果。"""

    total_files: int = 0      # 目录下匹配扩展名的文件数
    new_photos: int = 0       # 新增入库
    skipped: int = 0          # hash 已存在，跳过
    updated: int = 0          # 文件内容变化，更新
    failed: int = 0           # 读取失败
    errors: list[str] = field(default_factory=list)


class PhotoService:
    """负责照片目录管理与扫描。"""

    def __init__(
        self,
        db: Database,
        config: ConfigManager,
        logger=None,
    ) -> None:
        self._db = db
        self._config = config
        self._repo = PhotoRepository(db)
        self._logger = logger or get_logger("service.photo")

    # ------------------------------------------------------------------
    # 目录管理
    # ------------------------------------------------------------------
    def get_photo_directory(self) -> Path | None:
        """返回配置的照片目录。"""
        raw = self._config.get("photo.directory")
        return Path(raw) if raw else None

    def set_photo_directory(self, directory: str | Path) -> Path:
        """设置照片目录并持久化。

        参数:
            directory: 目录路径。
        返回:
            规范化后的目录。
        异常:
            NotADirectoryError: 目录不存在或不是目录。
        """
        p = Path(directory).expanduser().resolve()
        if not p.exists():
            raise NotADirectoryError(f"目录不存在: {p}")
        if not p.is_dir():
            raise NotADirectoryError(f"不是目录: {p}")
        self._config.set("photo.directory", str(p))
        self._config.save()
        self._logger.info("照片目录已设置: %s", p)
        return p

    # ------------------------------------------------------------------
    # 扫描
    # ------------------------------------------------------------------
    def _extensions(self) -> set[str]:
        exts = self._config.get("photo.extensions")
        return {str(e).lower() if str(e).startswith(".") else f".{str(e).lower()}" for e in exts}

    def _walk_images(self, root: Path) -> list[Path]:
        exts = self._extensions()
        found: list[Path] = []
        for entry in sorted(root.rglob("*")):
            if entry.is_file() and entry.suffix.lower() in exts:
                found.append(entry)
        return found

    def scan(self, directory: Path | str | None = None, progress: ProgressCallback | None = None) -> ScanResult:
        """增量扫描照片目录。

        流程（规格 §12）:
            1. 遍历目录
            2. 计算 hash，与数据库比对
            3. hash 已存在 → 跳过；路径存在但 hash 变 → 更新；否则插入新照片
        """
        root = Path(directory) if directory else self.get_photo_directory()
        if root is None:
            raise ValueError("尚未配置照片目录")
        root = Path(root).resolve()

        result = ScanResult()
        images = self._walk_images(root)
        result.total_files = len(images)
        task_id = self._begin_scan_task(root)

        for idx, file_path in enumerate(images):
            try:
                self._process_file(file_path, result)
            except OSError as exc:
                result.failed += 1
                result.errors.append(f"{file_path}: {exc}")
                self._logger.warning("扫描文件失败 %s: %s", file_path, exc)
            if progress:
                progress(idx + 1, len(images))

        self._finish_scan_task(task_id, result)
        self._logger.info(
            "扫描完成: 目录=%s 文件=%d 新增=%d 跳过=%d 更新=%d 失败=%d",
            root, result.total_files, result.new_photos,
            result.skipped, result.updated, result.failed,
        )
        return result

    def import_file(self, file_path: Path | str) -> Photo | None:
        """把单个照片文件入库或更新，供实时监听回调使用。

        返回入库后的 Photo；非支持格式、文件不存在或读取文件信息失败时返回 None。
        """
        path = Path(file_path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in self._extensions():
            return None

        result = ScanResult(total_files=1)
        try:
            self._process_file(path, result)
        except OSError as exc:
            self._logger.warning("实时导入照片失败 %s: %s", path, exc)
            return None
        photo = self._repo.get_by_path(str(path))
        if photo is not None:
            self._logger.info(
                "实时导入照片完成: %s 新增=%d 更新=%d 跳过=%d",
                path,
                result.new_photos,
                result.updated,
                result.skipped,
            )
        return photo

    def _process_file(self, file_path: Path, result: ScanResult) -> None:
        """处理单个文件：去重判断并入库。"""
        p = str(file_path)
        file_hash = hash_file(file_path)

        existing = self._repo.get_by_hash(file_hash)
        if existing is not None:
            # hash 已存在：路径不同则更新为当前路径（去重）
            if existing.path != p:
                self._update_path(existing.id, p, file_path)
            result.skipped += 1
            return

        current = self._repo.get_by_path(p)
        if current is not None:
            # 路径存在但内容变了 → 更新
            self._update_file(current.id, file_path, file_hash)
            result.updated += 1
            return

        self._insert_new(file_path, file_hash)
        result.new_photos += 1

    def _insert_new(self, file_path: Path, file_hash: str) -> None:
        stat = file_path.stat()
        photo = Photo(
            path=str(file_path),
            file_name=file_path.name,
            hash=file_hash,
            file_size=stat.st_size,
            captured_at=read_captured_at(file_path),
            status=PhotoStatus.PENDING.value,
        )
        self._repo.insert(photo)

    def _update_path(self, photo_id: int, new_path: str, file_path: Path) -> None:
        """同一张照片换个路径，更新路径信息。"""
        self._db.execute(
            "UPDATE photo SET path=?, file_name=?, updated_at=? WHERE id=?",
            (new_path, file_path.name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), photo_id),
        )

    def _update_file(self, photo_id: int, file_path: Path, file_hash: str) -> None:
        """文件内容变化，更新 hash/大小/时间。"""
        stat = file_path.stat()
        self._db.execute(
            "UPDATE photo SET hash=?, file_size=?, captured_at=?, status=?, updated_at=? WHERE id=?",
            (
                file_hash,
                stat.st_size,
                read_captured_at(file_path),
                PhotoStatus.PENDING.value,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                photo_id,
            ),
        )

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        """索引状态统计（规格 §13）。"""
        return self._repo.stats()

    # ------------------------------------------------------------------
    # 扫描任务记录
    # ------------------------------------------------------------------
    def _begin_scan_task(self, root: Path) -> int:
        with self._db.transaction():
            cur = self._db.execute(
                "INSERT INTO scan_task (task_type, target_path, status, created_at) VALUES ('scan', ?, 'running', ?)",
                (str(root), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            return cur.lastrowid

    def _finish_scan_task(self, task_id: int, result: ScanResult) -> None:
        summary = (
            f"文件={result.total_files} 新增={result.new_photos} "
            f"跳过={result.skipped} 更新={result.updated} 失败={result.failed}"
        )
        self._db.execute(
            "UPDATE scan_task SET status='done', result=?, finished_at=? WHERE id=?",
            (summary, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id),
        )
