"""授权 ViewModel 单元测试。"""
from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.license import create_license
from services.license_service import LicenseService
from viewmodels.license_viewmodel import LicenseViewModel


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


@pytest.fixture
def vm(qapp, ctx, tmp_path, keypair) -> LicenseViewModel:
    _, public_key = keypair
    svc = LicenseService(
        ctx.db,
        ctx.config,
        ctx.app_dir,
        public_key_path=public_key,
        home_dir=tmp_path / "home",
    )
    return LicenseViewModel(svc)


class TestLicenseViewModel:
    def test_machine_code(self, vm):
        assert vm.machine_code()

    def test_initial_status_is_trial(self, vm):
        st = vm.status()
        assert st["trial"] is True

    def test_activate_valid_key(self, vm, keypair):
        private_key, _ = keypair
        key = create_license(vm.machine_code(), "duration", 30, private_key_path=private_key)
        ok, msg = vm.activate(key)
        assert ok is True
        st = vm.status()
        assert st["licensed"] is True

    def test_activate_invalid_key(self, vm):
        ok, _ = vm.activate("invalid-key")
        assert ok is False
