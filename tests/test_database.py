"""数据库初始化与连接单元测试。"""
from __future__ import annotations

import sqlite3

import pytest

from database import ALL_TABLE_NAMES, SCHEMA_VERSION, Database, init_db


@pytest.fixture
def db(tmp_path) -> Database:
    database = Database(tmp_path / "data" / "test.db")
    init_db(database)
    return database


class TestSchema:
    def test_all_tables_created(self, db):
        rows = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        names = {r["name"] for r in rows}
        for table in ALL_TABLE_NAMES:
            assert table in names, f"缺少表 {table}"

    def test_schema_version(self, db):
        assert db.scalar("PRAGMA user_version") == SCHEMA_VERSION

    def test_photo_unique_path_constraint(self, db):
        db.execute(
            "INSERT INTO photo (path, file_name, hash, file_size) VALUES (?,?,?,?)",
            ("/a.jpg", "a.jpg", "h1", 100),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO photo (path, file_name, hash, file_size) VALUES (?,?,?,?)",
                ("/a.jpg", "a.jpg", "h2", 200),
            )


class TestConnection:
    def test_insert_select_roundtrip(self, db):
        db.execute(
            "INSERT INTO photo (path, file_name, hash, file_size) VALUES (?,?,?,?)",
            ("/b.jpg", "b.jpg", "h3", 300),
        )
        photo_id = db.last_insert_id()
        row = db.fetchone("SELECT * FROM photo WHERE id=?", (photo_id,))
        assert row is not None
        assert row["file_name"] == "b.jpg"
        assert row["status"] == "pending"  # 默认状态
        assert row["face_count"] == 0

    def test_foreign_keys_enforced(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO face (photo_id, bbox) VALUES (?,?)",
                (99999, "[0,0,10,10]"),
            )

    def test_cascade_delete(self, db):
        db.execute(
            "INSERT INTO photo (path, file_name, hash) VALUES (?,?,?)",
            ("/c.jpg", "c.jpg", "h4"),
        )
        pid = db.last_insert_id()
        db.execute("INSERT INTO face (photo_id, bbox) VALUES (?,?)", (pid, "[0,0,10,10]"))
        fid = db.last_insert_id()
        db.execute("DELETE FROM photo WHERE id=?", (pid,))
        assert db.fetchone("SELECT * FROM face WHERE id=?", (fid,)) is None

    def test_wal_mode_enabled(self, db):
        mode = db.scalar("PRAGMA journal_mode")
        assert mode.lower() == "wal"

    def test_row_factory_returns_dict(self, db):
        db.execute("INSERT INTO photo (path, file_name, hash) VALUES (?,?,?)", ("/d.jpg", "d.jpg", "h5"))
        row = db.fetchone("SELECT * FROM photo WHERE path=?", ("/d.jpg",))
        assert isinstance(row, dict)


class TestTransaction:
    def test_commit_on_success(self, db):
        with db.transaction():
            db.execute(
                "INSERT INTO photo (path, file_name, hash) VALUES (?,?,?)",
                ("/e.jpg", "e.jpg", "h6"),
            )
        assert db.scalar("SELECT COUNT(*) FROM photo WHERE path='/e.jpg'") == 1

    def test_rollback_on_error(self, db):
        with pytest.raises(RuntimeError):
            with db.transaction():
                db.execute(
                    "INSERT INTO photo (path, file_name, hash) VALUES (?,?,?)",
                    ("/f.jpg", "f.jpg", "h7"),
                )
                raise RuntimeError("boom")
        assert db.scalar("SELECT COUNT(*) FROM photo WHERE path='/f.jpg'") == 0

    def test_thread_local_connections(self, db):
        """不同线程使用独立连接，互不影响。"""
        import threading

        results: list[bool] = []

        def worker():
            results.append(db.scalar("SELECT 1") == 1)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results == [True] * 4
