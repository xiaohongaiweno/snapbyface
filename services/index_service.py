"""索引服务：编排照片→AI→向量入库的流水线（规格 §10）。"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

from core.ai.base import DetectedFace
from core.config import ConfigManager
from core.logger import get_logger
from core.task_queue import TaskQueue
from core.vector.base import VectorIndex
from database.connection import Database
from models.photo import Photo, PhotoStatus
from repositories.face_repository import FaceRepository
from repositories.photo_repository import PhotoRepository
from utils.image import read_image
from workers.base_worker import BaseWorker

logger = get_logger("service.index")


class IndexService:
    """照片 AI 索引编排。

    流程:
        submit_path() → 任务队列 → IndexWorker 消费 → process_photo()
        process_photo(): 检测人脸 → 特征提取 → 向量入库 → 更新状态
    """

    def __init__(
        self,
        db: Database,
        config: ConfigManager,
        face_engine: Any,
        vector_index: VectorIndex | None = None,
        num_workers: int = 1,
        logger=None,
    ) -> None:
        self._db = db
        self._config = config
        self._engine = face_engine
        self._vector_index = vector_index
        self._photo_repo = PhotoRepository(db)
        self._face_repo = FaceRepository(db)
        self._logger = logger or get_logger("service.index")

        self._queue: TaskQueue[int] = TaskQueue()
        self._in_flight: set[int] = set()
        self._lock = threading.Lock()
        self._workers: list[BaseWorker[int]] = []
        for i in range(num_workers):
            self._workers.append(BaseWorker(self._queue, name=f"index-{i}", handler=self._consume))

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self) -> None:
        for w in self._workers:
            w.start()
        self._logger.info("索引 Worker 已启动 (%d)", len(self._workers))

    def stop(self, timeout: float = 5.0) -> None:
        for w in self._workers:
            w.stop(timeout=timeout)

    def queue_size(self) -> int:
        return self._queue.qsize()

    # ------------------------------------------------------------------
    # 入队
    # ------------------------------------------------------------------
    def submit_path(self, path: str | Path) -> bool:
        """将照片加入索引队列（已 done 或已在处理中则跳过）。

        返回:
            True 表示已入队。
        """
        photo = self._photo_repo.get_by_path(str(path))
        if photo is None:
            self._logger.warning("照片不存在于数据库，跳过入队: %s", path)
            return False
        return self.submit_photo(photo)

    def submit_photo(self, photo: Photo) -> bool:
        """将照片对象加入索引队列。

        以数据库最新状态为准：已 done 或已在处理中的照片跳过。
        """
        if photo.id is None:
            return False
        fresh = self._photo_repo.get_by_id(photo.id)
        if fresh is None or fresh.status == PhotoStatus.DONE.value:
            return False
        with self._lock:
            if photo.id in self._in_flight:
                return False
            self._in_flight.add(photo.id)
        self._queue.put(photo.id)
        return True

    def _consume(self, photo_id: int) -> None:
        try:
            self.process_photo(photo_id)
        finally:
            with self._lock:
                self._in_flight.discard(photo_id)

    # ------------------------------------------------------------------
    # 处理管线
    # ------------------------------------------------------------------
    def process_photo(self, photo_id: int) -> bool:
        """对单张照片执行索引：检测 → 特征 → 向量入库。

        返回:
            True 表示成功（含无可检测人脸的情况）。
        """
        photo = self._photo_repo.get_by_id(photo_id)
        if photo is None:
            self._logger.warning("照片不存在: id=%s", photo_id)
            return False
        if photo.status == PhotoStatus.DONE.value:
            return True

        self._photo_repo.update_status(photo.id, PhotoStatus.INDEXING.value)
        self._logger.info("开始索引: %s", photo.path)

        try:
            image = self._load_image(photo.path)
            faces = self._engine.process(image) if image is not None else []
            self._store_faces(photo.id, faces)
            self._photo_repo.update_status(photo.id, PhotoStatus.DONE.value)
            self._logger.info("索引完成: %s (人脸=%d)", photo.path, len(faces))
            return True
        except Exception as exc:
            self._photo_repo.update_status(photo.id, PhotoStatus.FAILED.value)
            self._logger.exception("索引失败: %s (%s)", photo.path, exc)
            return False

    def _load_image(self, path: str) -> np.ndarray | None:
        """读取照片为 numpy 数组（BGR），包括相机 RAW 格式。"""
        image = read_image(path)
        if image is None:
            self._logger.warning("照片无法读取: %s", path)
        return image

    def _store_faces(self, photo_id: int, faces: list[DetectedFace]) -> None:
        """将检测结果写入 face 表，并将特征写入向量索引。"""
        # 先清空旧结果（重索引场景）
        self._face_repo.delete_by_photo(photo_id)

        for face in faces:
            bbox_json = json.dumps(list(face.bbox))
            embedding = face.embedding
            vector_id: str | None = None

            if embedding is not None and self._vector_index is not None:
                vector_id = self._make_vector_id(photo_id)
                self._vector_index.add_vector(vector_id, embedding)
                self._face_repo.insert_face_with_embedding(
                    photo_id, bbox_json, face.quality, vector_id
                )
            else:
                self._face_repo.insert_face(photo_id, bbox_json, face.quality, vector_id)

        # 更新照片人脸数量
        count = self._db.scalar("SELECT COUNT(*) FROM face WHERE photo_id=?", (photo_id,))
        if count:
            self._db.execute(
                "UPDATE photo SET face_count=? WHERE id=?",
                (int(count), photo_id),
            )

    def _make_vector_id(self, photo_id: int) -> str:
        """生成全局唯一的向量 id。"""
        import uuid

        return f"p{photo_id}_{uuid.uuid4().hex[:12]}"

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------
    def remove_photo_by_path(self, path: str | Path) -> bool:
        """根据文件路径删除照片及其索引（文件被删除时调用）。"""
        photo = self._photo_repo.get_by_path(str(path))
        if photo is None or photo.id is None:
            return False
        return self.remove_photo(photo.id)

    def remove_photo(self, photo_id: int) -> bool:
        """删除照片：清理向量索引、人脸数据、照片记录。

        返回:
            True 表示照片存在并已删除。
        """
        photo = self._photo_repo.get_by_id(photo_id)
        if photo is None:
            return False

        faces = self._face_repo.get_by_photo(photo_id)
        if self._vector_index is not None:
            for face in faces:
                vid = face.get("vector_id")
                if vid:
                    self._vector_index.delete(vid)

        self._face_repo.delete_by_photo(photo_id)  # 级联清理 face_embedding
        self._photo_repo.delete(photo_id)
        self._logger.info("已删除照片及索引: %s", photo.path)
        return True
