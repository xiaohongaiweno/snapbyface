"""SQLite 连接封装。

- 每线程一个独立连接（threading.local），线程安全
- 开启 WAL 与外键约束
- 提供 execute/executemany/fetch 与事务上下文管理器
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from core.logger import get_logger

logger = get_logger("database")


class Database:
    """SQLite 数据库封装。"""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._local = threading.local()

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        """创建新连接并应用基础配置。

        使用 autocommit 模式（isolation_level=None），
        每个 execute 立即生效；只有显式进入 transaction() 才开启事务。
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @property
    def connection(self) -> sqlite3.Connection:
        """返回当前线程的连接（懒创建）。"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """关闭当前线程的连接。"""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> sqlite3.Cursor:
        return self.connection.executemany(sql, seq_of_params)

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        row = self.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        rows = self.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.execute(sql, params).fetchone()
        return row[0] if row is not None else None

    def last_insert_id(self) -> int:
        return int(self.connection.execute("SELECT last_insert_rowid()").fetchone()[0])

    # ------------------------------------------------------------------
    # 事务
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[None]:
        """事务上下文（可重入），异常时回滚，正常时提交。

        支持嵌套调用：只有最外层事务真正提交/回滚。
        """
        conn = self.connection
        depth = getattr(self._local, "tx_depth", 0)
        is_outer = depth == 0
        self._local.tx_depth = depth + 1
        try:
            if is_outer:
                conn.execute("BEGIN")
            yield
            if is_outer:
                conn.commit()
        except Exception:
            if is_outer:
                conn.rollback()
            raise
        finally:
            self._local.tx_depth = depth
