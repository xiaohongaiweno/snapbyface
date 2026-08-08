"""搜索服务：游客人脸 → 特征 → 检索 → 照片结果（规格 §6.3/§20）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from core.ai.base import FaceEngine
from core.config import ConfigManager
from core.logger import get_logger
from core.vector.base import VectorIndex
from database.connection import Database
from models.photo import Photo
from repositories.face_repository import FaceRepository
from repositories.photo_repository import PhotoRepository


@dataclass
class SearchResult:
    """一次检索命中。"""

    photo_id: int
    path: str
    file_name: str
    similarity: float
    captured_at: str | None
    face_id: int
    vector_id: str


class SearchService:
    """人脸检索服务。"""

    def __init__(
        self,
        face_engine: Any,
        vector_index: VectorIndex,
        db: Database,
        config: ConfigManager,
        logger=None,
    ) -> None:
        self._engine = face_engine
        self._vector_index = vector_index
        self._face_repo = FaceRepository(db)
        self._photo_repo = PhotoRepository(db)
        self._config = config
        self._logger = logger or get_logger("service.search")

    @property
    def threshold(self) -> float:
        return float(self._config.get("face.threshold", 0.80))

    def search_image(self, image: np.ndarray, top_k: int = 20) -> list[SearchResult]:
        """对一张图像中的人脸逐一检索，按照片去重（保留最高相似度）。"""
        if image is None:
            return []
        faces = self._engine.process(image)
        hits: list[SearchResult] = []
        for face in faces:
            if face.embedding is None:
                continue
            hits.extend(self.search_embedding(face.embedding, top_k=top_k))
        return self._dedup_by_photo(hits)

    def search_embedding(self, embedding: np.ndarray, top_k: int = 20) -> list[SearchResult]:
        """用单个人脸特征检索（按照片去重，保留最高相似度）。"""
        matches = self._vector_index.search(embedding, top_k=top_k)
        threshold = self.threshold
        results: list[SearchResult] = []
        for vector_id, similarity in matches:
            if similarity < threshold:
                continue
            face = self._face_repo.get_face_by_vector_id(vector_id)
            if face is None:
                continue
            photo = self._photo_repo.get_by_id(face["photo_id"])
            if photo is None:
                continue
            results.append(
                SearchResult(
                    photo_id=photo.id or 0,
                    path=photo.path,
                    file_name=photo.file_name,
                    similarity=similarity,
                    captured_at=photo.captured_at,
                    face_id=face["id"],
                    vector_id=vector_id,
                )
            )
        return self._dedup_by_photo(results)

    @staticmethod
    def _dedup_by_photo(hits: list[SearchResult]) -> list[SearchResult]:
        """同一张照片只保留相似度最高的人脸。"""
        best: dict[int, SearchResult] = {}
        for hit in hits:
            prev = best.get(hit.photo_id)
            if prev is None or hit.similarity > prev.similarity:
                best[hit.photo_id] = hit
        return sorted(best.values(), key=lambda r: r.similarity, reverse=True)

    def get_photo(self, photo_id: int) -> Photo | None:
        return self._photo_repo.get_by_id(photo_id)
