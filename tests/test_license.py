"""授权核心单元测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.license import (
    DATETIME_FMT,
    LicenseInfo,
    create_license,
    decode_license,
    generate_machine_code,
)


@pytest.fixture
def keypair(tmp_path):
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_path = tmp_path / "private_key.pem"
    public_path = tmp_path / "public_key.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


class TestMachineCode:
    def test_deterministic(self):
        assert generate_machine_code() == generate_machine_code()

    def test_format(self):
        code = generate_machine_code()
        parts = code.split("-")
        assert len(parts) == 4
        assert parts[0] == "PX"
        assert all(len(p) == 4 for p in parts[1:])


class TestLicenseCodec:
    def test_roundtrip(self, keypair):
        private_key, public_key = keypair
        machine = generate_machine_code()
        key = create_license(machine, "duration", 30, private_key_path=private_key)
        info = decode_license(key, public_key)
        assert info is not None
        assert info.machine_code == machine
        assert info.license_type == "duration"
        assert key.startswith("PHX-")

    def test_tampered_signature_rejected(self, keypair):
        private_key, public_key = keypair
        machine = generate_machine_code()
        key = create_license(machine, "duration", 30, private_key_path=private_key)
        # 篡改一个字符
        tampered = key[:-1] + ("A" if key[-1] != "A" else "B")
        assert decode_license(tampered, public_key) is None

    def test_garbage_key_rejected(self):
        assert decode_license("garbage") is None
        assert decode_license("") is None
        assert decode_license("PHX-abc") is None

    def test_different_public_key_rejected(self, keypair, tmp_path):
        private_key, _ = keypair
        other_private = ec.generate_private_key(ec.SECP256R1())
        other_public = tmp_path / "other_public_key.pem"
        other_public.write_bytes(
            other_private.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        key = create_license("PX-AAAA-BBBB-CCCC", "duration", 30, private_key_path=private_key)
        assert decode_license(key, other_public) is None

    def test_expires_at(self, keypair):
        private_key, public_key = keypair
        machine = generate_machine_code()
        key = create_license(machine, "duration", 30, private_key_path=private_key)
        info = decode_license(key, public_key)
        assert info is not None
        expected = datetime.now() + timedelta(days=30)
        expires = datetime.strptime(info.display_expires_at(), DATETIME_FMT)
        assert abs((expires - expected).total_seconds()) < 60

    def test_is_expired(self):
        info = LicenseInfo(
            machine="PX-AAAA-BBBB-CCCC",
            credits=0,
            nonce="N1",
            issue_time="2020-01-01",
            payload={},
            signature="",
            raw_code="",
            license_type="duration",
            expires_at="2020-02-01T00:00:00Z",
            duration_days=30,
        )
        assert info.is_expired()
        future = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
        assert not LicenseInfo(
            machine="PX-AAAA-BBBB-CCCC",
            credits=0,
            nonce="N1",
            issue_time="2020-01-01",
            payload={},
            signature="",
            raw_code="",
            license_type="duration",
            expires_at=future,
            duration_days=30,
        ).is_expired()
