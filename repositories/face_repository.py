"""人脸数据访问层。"""
from __future__ import annotations

from typing import Any

from core.logger import get_logger
from database.connection import Database

logger = get_logger("repository.face")


class FaceRepository:
    """face 与 face_embedding 表操作。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # face
    # ------------------------------------------------------------------
    def insert_face(self, photo_id: int, bbox: str, quality_score: float, vector_id: str | None = None) -> int:
        """插入人脸，返回 face id。bbox 为 JSON 数组字符串。"""
        with self._db.transaction():
            cur = self._db.execute(
                """
                INSERT INTO face (photo_id, bbox, quality_score, vector_id)
                VALUES (?, ?, ?, ?)
                """,
                (photo_id, bbox, quality_score, vector_id),
            )
            return cur.lastrowid

    def get_by_photo(self, photo_id: int) -> list[dict[str, Any]]:
        return self._db.fetchall("SELECT * FROM face WHERE photo_id=? ORDER BY id", (photo_id,))

    def get(self, face_id: int) -> dict[str, Any] | None:
        return self._db.fetchone("SELECT * FROM face WHERE id=?", (face_id,))

    def set_vector_id(self, face_id: int, vector_id: str) -> None:
        self._db.execute("UPDATE face SET vector_id=? WHERE id=?", (vector_id, face_id))

    def delete_by_photo(self, photo_id: int) -> None:
        self._db.execute("DELETE FROM face WHERE photo_id=?", (photo_id,))

    # ------------------------------------------------------------------
    # face_embedding
    # ------------------------------------------------------------------
    def insert_face_with_embedding(
        self,
        photo_id: int,
        bbox: str,
        quality_score: float,
        vector_id: str,
        dim: int = 512,
    ) -> int:
        """在一个事务中插入人脸与向量映射，返回 face id。"""
        with self._db.transaction():
            cur = self._db.execute(
                """
                INSERT INTO face (photo_id, bbox, quality_score, vector_id)
                VALUES (?, ?, ?, ?)
                """,
                (photo_id, bbox, quality_score, vector_id),
            )
            face_id = cur.lastrowid
            self._db.execute(
                "INSERT INTO face_embedding (face_id, vector_id, dim) VALUES (?, ?, ?)",
                (face_id, vector_id, dim),
            )
            return face_id

    def insert_embedding(self, face_id: int, vector_id: str, dim: int = 512) -> int:
        with self._db.transaction():
            cur = self._db.execute(
                "INSERT INTO face_embedding (face_id, vector_id, dim) VALUES (?, ?, ?)",
                (face_id, vector_id, dim),
            )
            return cur.lastrowid

    def get_by_vector_id(self, vector_id: str) -> dict[str, Any] | None:
        return self._db.fetchone(
            "SELECT * FROM face_embedding WHERE vector_id=?", (vector_id,)
        )

    def get_face_by_vector_id(self, vector_id: str) -> dict[str, Any] | None:
        """通过 vector_id 反查人脸。"""
        return self._db.fetchone(
            """
            SELECT f.* FROM face f
            JOIN face_embedding e ON e.face_id = f.id
            WHERE e.vector_id=?
            """,
            (vector_id,),
        )

    def delete_embedding_by_face(self, face_id: int) -> None:
        self._db.execute("DELETE FROM face_embedding WHERE face_id=?", (face_id,))
