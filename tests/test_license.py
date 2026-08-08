"""授权核心单元测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.license import (
    DATETIME_FMT,
    LICENSE_SECRET,
    LicenseInfo,
    create_license,
    decode_license,
    generate_machine_code,
)


class TestMachineCode:
    def test_deterministic(self):
        assert generate_machine_code() == generate_machine_code()

    def test_format(self):
        code = generate_machine_code()
        parts = code.split("-")
        assert len(parts) == 4
        assert all(len(p) == 8 for p in parts)


class TestLicenseCodec:
    def test_roundtrip(self):
        machine = generate_machine_code()
        key = create_license(machine, "month", 30)
        info = decode_license(key)
        assert info is not None
        assert info.machine_code == machine
        assert info.license_type == "month"

    def test_tampered_signature_rejected(self):
        machine = generate_machine_code()
        key = create_license(machine, "month", 30)
        # 篡改一个字符
        tampered = key[:-1] + ("A" if key[-1] != "A" else "B")
        assert decode_license(tampered) is None

    def test_garbage_key_rejected(self):
        assert decode_license("garbage") is None
        assert decode_license("") is None
        assert decode_license("SBF-abc") is None

    def test_different_secret_rejected(self):
        key = create_license("M1", "month", 30, secret="secret-a")
        assert decode_license(key, secret="secret-b") is None

    def test_expires_at(self):
        machine = generate_machine_code()
        key = create_license(machine, "month", 30)
        info = decode_license(key)
        assert info is not None
        expected = datetime.now() + timedelta(days=30)
        expires = datetime.strptime(info.expires_at, DATETIME_FMT)
        assert abs((expires - expected).total_seconds()) < 60

    def test_is_expired(self):
        info = LicenseInfo("M1", "month", "2020-01-01 00:00:00", "2020-02-01 00:00:00")
        assert info.is_expired()
        future = (datetime.now() + timedelta(days=30)).strftime(DATETIME_FMT)
        assert not LicenseInfo("M1", "month", "2020-01-01 00:00:00", future).is_expired()
