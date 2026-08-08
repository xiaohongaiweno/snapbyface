"""数据库层：建表语句与版本管理。"""
from __future__ import annotations

SCHEMA_VERSION = 1

# 与规格 §14 对应的 9 张表
SCHEMA_STATEMENTS: list[str] = [
    # 照片表（§15）：路径/文件名/hash/大小/时间/状态/人脸数量
    """
    CREATE TABLE IF NOT EXISTS photo (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        path        TEXT    NOT NULL UNIQUE,
        file_name   TEXT    NOT NULL,
        hash        TEXT    NOT NULL,
        file_size   INTEGER NOT NULL DEFAULT 0,
        captured_at TEXT,
        status      TEXT    NOT NULL DEFAULT 'pending',
        face_count  INTEGER NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 人脸表（§16）：photo_id/人脸框/质量评分
    """
    CREATE TABLE IF NOT EXISTS face (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        photo_id      INTEGER NOT NULL REFERENCES photo(id) ON DELETE CASCADE,
        bbox          TEXT    NOT NULL,
        quality_score REAL    NOT NULL DEFAULT 0,
        vector_id     TEXT,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 向量索引映射（§17：向量本体在 FAISS，SQLite 只存 vector_id）
    """
    CREATE TABLE IF NOT EXISTS face_embedding (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        face_id    INTEGER NOT NULL REFERENCES face(id) ON DELETE CASCADE,
        vector_id  TEXT    NOT NULL UNIQUE,
        dim        INTEGER NOT NULL DEFAULT 512,
        created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 扫描任务
    """
    CREATE TABLE IF NOT EXISTS scan_task (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type   TEXT NOT NULL,
        target_path TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'pending',
        result      TEXT,
        error       TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        finished_at TEXT
    )
    """,
    # 索引任务
    """
    CREATE TABLE IF NOT EXISTS index_task (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        photo_id    INTEGER NOT NULL REFERENCES photo(id) ON DELETE CASCADE,
        status      TEXT    NOT NULL DEFAULT 'pending',
        error       TEXT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        finished_at TEXT
    )
    """,
    # 系统配置表
    """
    CREATE TABLE IF NOT EXISTS system_config (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 授权表
    """
    CREATE TABLE IF NOT EXISTS license (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_code TEXT NOT NULL,
        license_key  TEXT,
        license_type TEXT NOT NULL DEFAULT 'trial',
        issued_at    TEXT,
        expires_at   TEXT,
        is_active    INTEGER NOT NULL DEFAULT 0,
        updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 打印记录
    """
    CREATE TABLE IF NOT EXISTS print_record (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        photo_id   INTEGER REFERENCES photo(id) ON DELETE SET NULL,
        face_id    INTEGER REFERENCES face(id) ON DELETE SET NULL,
        similarity REAL,
        operator   TEXT,
        printed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    # 操作日志
    """
    CREATE TABLE IF NOT EXISTS operation_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        category   TEXT NOT NULL DEFAULT 'general',
        message    TEXT NOT NULL,
        level      TEXT NOT NULL DEFAULT 'INFO',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
]

# 便于测试与调试：列出所有表名
ALL_TABLE_NAMES: list[str] = [
    "photo",
    "face",
    "face_embedding",
    "scan_task",
    "index_task",
    "system_config",
    "license",
    "print_record",
    "operation_log",
]
