"""授权服务单元测试。"""
from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.license import create_license
from repositories.license_repository import LicenseRepository
from services.license_service import LicenseService


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
def service(ctx, tmp_path, keypair) -> LicenseService:
    _, public_key = keypair
    return LicenseService(
        ctx.db,
        ctx.config,
        ctx.app_dir,
        public_key_path=public_key,
        home_dir=tmp_path / "home",
    )


def _make_key(service, keypair, days=30, machine=None):
    private_key, _ = keypair
    machine = machine or service.machine_code
    return create_license(machine, "duration", days, private_key_path=private_key)


class TestTrial:
    def test_first_status_starts_trial(self, service):
        st = service.status()
        assert st["trial"] is True
        assert st["licensed"] is False
        assert st["valid"] is True
        assert st["days_left"] == service.trial_days

    def test_trial_start_persisted(self, service):
        service.status()
        assert LicenseRepository(service._db).get_config("trial_start") is not None

    def test_trial_days_left(self, service):
        service.status()
        st = service.status()
        assert st["days_left"] == pytest.approx(service.trial_days)

    def test_trial_respected_across_instances(self, ctx, tmp_path):
        home = tmp_path / "home"
        s1 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        s1.status()
        s2 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        st = s2.status()
        assert st["trial"] is True
        assert st["days_left"] == s2.trial_days


class TestActivation:
    def test_activate_valid_key(self, service, keypair):
        ok, msg = service.activate(_make_key(service, keypair))
        assert ok is True
        st = service.status()
        assert st["licensed"] is True
        assert st["valid"] is True
        assert st["reason"] == "ok"

    def test_activate_wrong_machine_rejected(self, service, keypair):
        key = _make_key(service, keypair, machine="PX-AAAA-BBBB-CCCC")
        ok, msg = service.activate(key)
        assert ok is False
        assert "不属于当前设备" in msg

    def test_activate_invalid_key(self, service):
        ok, msg = service.activate("PHX-not-a-valid-key")
        assert ok is False

    def test_activate_expired_key(self, service, keypair):
        from datetime import datetime, timedelta

        from core.license import create_license

        issued = datetime.now() - timedelta(days=60)
        private_key, _ = keypair
        key = create_license(
            service.machine_code,
            "duration",
            30,
            private_key_path=private_key,
            issued_at=issued,
        )
        ok, msg = service.activate(key)
        assert ok is False
        assert "过期" in msg

    def test_activation_stored_in_multiple_locations(self, service, keypair):
        service.activate(_make_key(service, keypair))
        for path in service._license_paths():
            assert path.exists(), f"缺少授权文件: {path}"

    def test_anti_deletion_bypass(self, ctx, tmp_path, keypair):
        """删除数据库与部分授权文件后，激活仍可从其他位置恢复。"""
        home = tmp_path / "home"
        _, public_key = keypair
        service = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        service.activate(_make_key(service, keypair))

        # 攻击：删掉数据库激活记录 + 前两个授权文件
        LicenseRepository(ctx.db).deactivate()
        for path in service._license_paths()[:2]:
            path.unlink(missing_ok=True)

        # 重新创建服务实例，应仍能恢复激活
        service2 = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        st = service2.status()
        assert st["licensed"] is True
        assert st["valid"] is True

    def test_delete_all_forces_reactivation(self, ctx, tmp_path, keypair):
        home = tmp_path / "home"
        _, public_key = keypair
        service = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        service.activate(_make_key(service, keypair))
        LicenseRepository(ctx.db).deactivate()
        for path in service._license_paths():
            path.unlink(missing_ok=True)

        service2 = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        st = service2.status()
        assert st["licensed"] is False  # 授权丢失，不再处于已激活状态

    def test_deactivate(self, service, keypair):
        service.activate(_make_key(service, keypair))
        service.deactivate()
        st = service.status()
        assert st["licensed"] is False
        assert st["trial"] is True  # 回到试用

    def test_activate_supersedes_old(self, ctx, tmp_path, keypair):
        home = tmp_path / "home"
        _, public_key = keypair
        s1 = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        s1.activate(_make_key(s1, keypair, days=30))
        s2 = LicenseService(
            ctx.db,
            ctx.config,
            ctx.app_dir,
            public_key_path=public_key,
            home_dir=home,
        )
        s2.activate(_make_key(s2, keypair, days=90))
        st = s2.status()
        expires2 = s2._get_activated_info()
        assert st["licensed"] is True


class TestMachineBinding:
    def test_machine_code_exposed(self, service):
        assert service.machine_code
