"""照片服务单元测试。"""
from __future__ import annotations

import pytest

from models.photo import Photo, PhotoStatus
from repositories.photo_repository import PhotoRepository
from services.photo_service import PhotoService


@pytest.fixture
def service(ctx, photo_dir) -> PhotoService:
    svc = PhotoService(ctx.db, ctx.config)
    svc.set_photo_directory(photo_dir)
    return svc


def _make_photo(photo_dir, name: str, content: bytes = b"x") -> None:
    (photo_dir / name).write_bytes(content)


class TestDirectory:
    def test_set_photo_directory(self, ctx, photo_dir):
        svc = PhotoService(ctx.db, ctx.config)
        p = svc.set_photo_directory(photo_dir)
        assert p == photo_dir.resolve()
        assert ctx.config.get("photo.directory") == str(photo_dir.resolve())

    def test_set_nonexistent_raises(self, ctx, tmp_path):
        svc = PhotoService(ctx.db, ctx.config)
        with pytest.raises(NotADirectoryError):
            svc.set_photo_directory(tmp_path / "nope")

    def test_get_photo_directory_returns_none_initially(self, ctx):
        svc = PhotoService(ctx.db, ctx.config)
        assert svc.get_photo_directory() is None

    def test_scan_without_directory_raises(self, ctx):
        svc = PhotoService(ctx.db, ctx.config)
        with pytest.raises(ValueError):
            svc.scan()


class TestScanDedup:
    def test_initial_scan_finds_all(self, service, photo_dir):
        _make_photo(photo_dir, "a.jpg")
        _make_photo(photo_dir, "b.jpg", b"xyz")
        result = service.scan()
        assert result.total_files == 2
        assert result.new_photos == 2
        assert result.skipped == 0
        assert service.get_stats()["total"] == 2

    def test_rescan_is_incremental(self, service, photo_dir):
        _make_photo(photo_dir, "a.jpg", b"aaa")
        _make_photo(photo_dir, "b.jpg", b"bbb")
        service.scan()
        result = service.scan()
        assert result.new_photos == 0
        assert result.skipped == 2
        assert service.get_stats()["total"] == 2

    def test_hash_dedup_skips_duplicate_content(self, service, photo_dir, tmp_path):
        _make_photo(photo_dir, "a.jpg", b"same-content")
        _make_photo(photo_dir, "b.jpg", b"same-content")  # 内容相同 → 去重
        result = service.scan()
        assert result.new_photos == 1
        assert result.skipped == 1
        assert service.get_stats()["total"] == 1

    def test_updated_file_is_rediscovered(self, service, photo_dir):
        f = photo_dir / "a.jpg"
        f.write_bytes(b"v1")
        service.scan()
        f.write_bytes(b"v2-changed")
        result = service.scan()
        assert result.updated == 1
        assert service.get_stats()["total"] == 1
        assert service.get_stats()["pending"] == 1  # 内容变化后重置为待索引

    def test_only_supported_extensions(self, service, photo_dir):
        _make_photo(photo_dir, "photo.jpg")
        (photo_dir / "notes.txt").write_text("not an image")
        (photo_dir / "movie.gif").write_text("gif")
        (photo_dir / "clip.mp4").write_bytes(b"video")
        (photo_dir / "camera.cr2").write_bytes(b"raw")
        result = service.scan()
        assert result.total_files == 2
        assert result.new_photos == 2

    def test_recursive_subdirectories(self, service, photo_dir):
        sub = photo_dir / "2026-08-02"
        sub.mkdir()
        _make_photo(sub, "inside.png")
        result = service.scan()
        assert result.new_photos == 1

    def test_scan_creates_scan_task_record(self, service, photo_dir):
        _make_photo(photo_dir, "a.jpg")
        service.scan()
        rows = ctx_all_tasks(service)
        assert len(rows) == 1
        assert rows[0]["status"] == "done"

    def test_progress_callback(self, service, photo_dir):
        _make_photo(photo_dir, "a.jpg")
        _make_photo(photo_dir, "b.jpg")
        calls: list[tuple[int, int]] = []
        service.scan(progress=lambda done, total: calls.append((done, total)))
        assert calls == [(1, 2), (2, 2)]

    def test_photo_metadata_stored(self, service, photo_dir):
        _make_photo(photo_dir, "a.jpg", b"metadata")
        service.scan()
        repo = PhotoRepository(service._db)
        photo = repo.list_by_status(PhotoStatus.PENDING.value)[0]
        assert photo.file_name == "a.jpg"
        assert photo.file_size == len(b"metadata")
        assert photo.status == PhotoStatus.PENDING.value
        assert len(photo.hash) == 64  # sha256 hex

    def test_import_file_adds_single_photo(self, service, photo_dir):
        path = photo_dir / "live.jpg"
        _make_photo(photo_dir, "live.jpg", b"live")
        photo = service.import_file(path)
        assert photo is not None
        assert photo.file_name == "live.jpg"
        assert service.get_stats()["pending"] == 1

    def test_import_file_ignores_video(self, service, photo_dir):
        path = photo_dir / "clip.mp4"
        path.write_bytes(b"video")
        assert service.import_file(path) is None
        assert service.get_stats()["total"] == 0


def ctx_db(service):
    return service._db


def ctx_all_tasks(service):
    return service._db.fetchall("SELECT * FROM scan_task ORDER BY id")
