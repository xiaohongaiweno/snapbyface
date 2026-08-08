"""授权数据访问层。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from database.connection import Database


class LicenseRepository:
    """license 表操作。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def get_active(self) -> dict[str, Any] | None:
        return self._db.fetchone(
            "SELECT * FROM license WHERE is_active=1 ORDER BY id DESC LIMIT 1"
        )

    def save_activated(
        self,
        machine_code: str,
        license_key: str,
        license_type: str,
        issued_at: str,
        expires_at: str,
    ) -> None:
        """保存激活记录（先清空旧激活，再写入新记录）。"""
        with self._db.transaction():
            self._db.execute("UPDATE license SET is_active=0 WHERE is_active=1")
            self._db.execute(
                """
                INSERT INTO license (machine_code, license_key, license_type,
                                     issued_at, expires_at, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    machine_code,
                    license_key,
                    license_type,
                    issued_at,
                    expires_at,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

    def deactivate(self) -> None:
        self._db.execute("UPDATE license SET is_active=0 WHERE is_active=1")

    def get_config(self, key: str) -> str | None:
        row = self._db.fetchone(
            "SELECT value FROM system_config WHERE key=?", (key,)
        )
        return row["value"] if row else None

    def set_config(self, key: str, value: str) -> None:
        self._db.execute(
            """
            INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
