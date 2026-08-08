"""照片数据模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PhotoStatus(str, Enum):
    """照片索引状态（规格 §13 需区分无照片/未处理）。"""

    PENDING = "pending"    # 已扫描入库，等待 AI 索引
    INDEXING = "indexing"  # AI 处理中
    DONE = "done"          # 已索引（特征已入 FAISS）
    FAILED = "failed"      # 处理失败

    @classmethod
    def has_value(cls, value: Any) -> bool:
        return any(value == item.value for item in cls)


@dataclass
class Photo:
    """照片记录，对应 photo 表（规格 §15）。"""

    path: str
    file_name: str
    hash: str
    file_size: int = 0
    captured_at: str | None = None
    status: str = PhotoStatus.PENDING.value
    face_count: int = 0
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Photo":
        return cls(
            id=row.get("id"),
            path=row["path"],
            file_name=row["file_name"],
            hash=row["hash"],
            file_size=row.get("file_size") or 0,
            captured_at=row.get("captured_at"),
            status=row.get("status") or PhotoStatus.PENDING.value,
            face_count=row.get("face_count") or 0,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
