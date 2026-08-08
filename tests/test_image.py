"""图片信息工具测试。"""
from __future__ import annotations

import datetime

from utils.image import read_captured_at


class TestReadCapturedAt:
    def test_returns_time_for_valid_file(self, tmp_path):
        f = tmp_path / "a.jpg"
        f.write_bytes(b"fake-jpeg")
        result = read_captured_at(f)
        assert result is not None
        # 无 EXIF → 回退文件 mtime，仍能解析出合法时间
        datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S")

    def test_missing_file_returns_none(self, tmp_path):
        assert read_captured_at(tmp_path / "nope.jpg") is None
