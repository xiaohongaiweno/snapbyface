"""照片数据访问层。所有 SQL 集中在此，供 Service 调用。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core.logger import get_logger
from database.connection import Database
from models.photo import Photo, PhotoStatus

logger = get_logger("repository.photo")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PhotoRepository:
    """photo 表操作。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def insert(self, photo: Photo) -> int:
        """插入照片，返回自增 id。"""
        now = _now()
        with self._db.transaction():
            cur = self._db.execute(
                """
                INSERT INTO photo (path, file_name, hash, file_size, captured_at,
                                   status, face_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    photo.path,
                    photo.file_name,
                    photo.hash,
                    photo.file_size,
                    photo.captured_at,
                    photo.status,
                    photo.face_count,
                    now,
                    now,
                ),
            )
            return cur.lastrowid

    def update_status(self, photo_id: int, status: str) -> None:
        """更新索引状态。"""
        self._db.execute(
            "UPDATE photo SET status=?, updated_at=? WHERE id=?",
            (status, _now(), photo_id),
        )

    def increment_face_count(self, photo_id: int) -> None:
        """人脸数量 +1。"""
        self._db.execute(
            "UPDATE photo SET face_count=face_count+1, updated_at=? WHERE id=?",
            (_now(), photo_id),
        )

    def touch(self, photo_id: int) -> None:
        """刷新 updated_at。"""
        self._db.execute(
            "UPDATE photo SET updated_at=? WHERE id=?",
            (_now(), photo_id),
        )

    def delete(self, photo_id: int) -> None:
        """删除照片（级联删除 face/embedding）。"""
        self._db.execute("DELETE FROM photo WHERE id=?", (photo_id,))

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_by_id(self, photo_id: int) -> Photo | None:
        row = self._db.fetchone("SELECT * FROM photo WHERE id=?", (photo_id,))
        return Photo.from_row(row) if row else None

    def get_by_path(self, path: str) -> Photo | None:
        row = self._db.fetchone("SELECT * FROM photo WHERE path=?", (self._norm(path),))
        return Photo.from_row(row) if row else None

    def get_by_hash(self, file_hash: str) -> Photo | None:
        row = self._db.fetchone("SELECT * FROM photo WHERE hash=?", (file_hash,))
        return Photo.from_row(row) if row else None

    def exists_by_hash(self, file_hash: str) -> bool:
        return self.get_by_hash(file_hash) is not None

    def exists_by_path(self, path: str) -> bool:
        return self.get_by_path(path) is not None

    @staticmethod
    def _norm(path: str) -> str:
        """路径归一化：解决 /var -> /private/var 等符号链接差异。"""
        import os

        return os.path.realpath(os.path.normpath(path))

    def count(self, status: str | None = None) -> int:
        if status is None:
            return int(self._db.scalar("SELECT COUNT(*) FROM photo"))
        return int(self._db.scalar("SELECT COUNT(*) FROM photo WHERE status=?", (status,)))

    def list_by_status(self, status: str, limit: int = 500) -> list[Photo]:
        rows = self._db.fetchall(
            "SELECT * FROM photo WHERE status=? ORDER BY id LIMIT ?",
            (status, limit),
        )
        return [Photo.from_row(r) for r in rows]

    def pending_photos(self, limit: int = 500) -> list[Photo]:
        """返回等待 AI 索引的照片。"""
        return self.list_by_status(PhotoStatus.PENDING.value, limit=limit)

    def stats(self) -> dict[str, Any]:
        """索引状态统计（规格 §13）。"""
        total = self.count()
        done = self.count(PhotoStatus.DONE.value)
        indexing = self.count(PhotoStatus.INDEXING.value)
        pending = self.count(PhotoStatus.PENDING.value)
        failed = self.count(PhotoStatus.FAILED.value)
        last = self._db.fetchone("SELECT MAX(updated_at) AS t FROM photo")
        return {
            "total": total,
            "done": done,
            "indexing": indexing,
            "pending": pending,
            "failed": failed,
            "last_updated": last["t"] if last else None,
        }
