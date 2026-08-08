"""PhotoRepository 单元测试。"""
from __future__ import annotations

import pytest

from models.photo import Photo, PhotoStatus
from repositories.photo_repository import PhotoRepository


@pytest.fixture
def repo(ctx) -> PhotoRepository:
    return PhotoRepository(ctx.db)


class TestInsertQuery:
    def test_insert_and_get_by_id(self, repo):
        pid = repo.insert(Photo(path="/a.jpg", file_name="a.jpg", hash="h1", file_size=10))
        photo = repo.get_by_id(pid)
        assert photo.path == "/a.jpg"
        assert photo.file_name == "a.jpg"
        assert photo.hash == "h1"
        assert photo.status == PhotoStatus.PENDING.value

    def test_get_by_path_and_hash(self, repo):
        repo.insert(Photo(path="/b.jpg", file_name="b.jpg", hash="hb"))
        assert repo.get_by_path("/b.jpg") is not None
        assert repo.get_by_hash("hb") is not None
        assert repo.get_by_path("/nope") is None
        assert repo.get_by_hash("nope") is None

    def test_exists_checks(self, repo):
        repo.insert(Photo(path="/c.jpg", file_name="c.jpg", hash="hc"))
        assert repo.exists_by_hash("hc")
        assert repo.exists_by_path("/c.jpg")
        assert not repo.exists_by_hash("x")
        assert not repo.exists_by_path("/x")


class TestStatusFlow:
    def test_status_update(self, repo):
        pid = repo.insert(Photo(path="/d.jpg", file_name="d.jpg", hash="hd"))
        repo.update_status(pid, PhotoStatus.DONE.value)
        assert repo.get_by_id(pid).status == PhotoStatus.DONE.value

    def test_face_count_increment(self, repo):
        pid = repo.insert(Photo(path="/e.jpg", file_name="e.jpg", hash="he"))
        repo.increment_face_count(pid)
        repo.increment_face_count(pid)
        assert repo.get_by_id(pid).face_count == 2

    def test_counts_by_status(self, repo):
        p1 = repo.insert(Photo(path="/1.jpg", file_name="1.jpg", hash="h1"))
        p2 = repo.insert(Photo(path="/2.jpg", file_name="2.jpg", hash="h2"))
        repo.update_status(p1, PhotoStatus.DONE.value)
        assert repo.count() == 2
        assert repo.count(PhotoStatus.DONE.value) == 1
        assert repo.count(PhotoStatus.PENDING.value) == 1

    def test_pending_photos(self, repo):
        p1 = repo.insert(Photo(path="/1.jpg", file_name="1.jpg", hash="h1"))
        p2 = repo.insert(Photo(path="/2.jpg", file_name="2.jpg", hash="h2"))
        repo.update_status(p2, PhotoStatus.DONE.value)
        pending = repo.pending_photos()
        assert [p.id for p in pending] == [p1]

    def test_stats(self, repo):
        p1 = repo.insert(Photo(path="/1.jpg", file_name="1.jpg", hash="h1"))
        p2 = repo.insert(Photo(path="/2.jpg", file_name="2.jpg", hash="h2"))
        p3 = repo.insert(Photo(path="/3.jpg", file_name="3.jpg", hash="h3"))
        repo.update_status(p1, PhotoStatus.DONE.value)
        repo.update_status(p2, PhotoStatus.INDEXING.value)
        repo.update_status(p3, PhotoStatus.FAILED.value)
        stats = repo.stats()
        assert stats["total"] == 3
        assert stats["done"] == 1
        assert stats["indexing"] == 1
        assert stats["pending"] == 0
        assert stats["failed"] == 1


class TestDelete:
    def test_delete_removes_photo(self, repo):
        pid = repo.insert(Photo(path="/x.jpg", file_name="x.jpg", hash="hx"))
        repo.delete(pid)
        assert repo.get_by_id(pid) is None
