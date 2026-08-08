"""打印服务单元测试。"""
from __future__ import annotations

import pytest

from repositories.photo_repository import PhotoRepository
from services.photo_service import PhotoService
from services.print_service import PrintService
from tests.fakes import make_test_image


@pytest.fixture
def photo(ctx, photo_dir):
    ps = PhotoService(ctx.db, ctx.config)
    ps.set_photo_directory(photo_dir)
    make_test_image(photo_dir / "a.jpg")
    ps.scan()
    repo = PhotoRepository(ctx.db)
    return repo.get_by_path(str(photo_dir / "a.jpg"))


class TestPrintService:
    def test_print_records_and_logs(self, ctx, photo):
        svc = PrintService(ctx.db)
        assert svc.print_photo(photo.id, similarity=0.92) is True
        records = svc.recent_records()
        assert len(records) == 1
        assert records[0]["photo_id"] == photo.id
        assert records[0]["similarity"] == pytest.approx(0.92)

        logs = ctx.db.fetchall("SELECT * FROM operation_log WHERE category='print'")
        assert len(logs) == 1

    def test_print_missing_photo_returns_false(self, ctx):
        svc = PrintService(ctx.db)
        assert svc.print_photo(99999) is False

    def test_recent_records_order(self, ctx, photo):
        svc = PrintService(ctx.db)
        svc.print_photo(photo.id, similarity=0.9)
        svc.print_photo(photo.id, similarity=0.8)
        records = svc.recent_records()
        assert len(records) == 2
        assert records[0]["similarity"] == pytest.approx(0.8)  # 新的在前
