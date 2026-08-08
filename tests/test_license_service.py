"""授权服务单元测试。"""
from __future__ import annotations

import pytest

from core.license import create_license
from repositories.license_repository import LicenseRepository
from services.license_service import LicenseService


@pytest.fixture
def service(ctx, tmp_path) -> LicenseService:
    return LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=tmp_path / "home")


def _make_key(service, days=30, machine=None):
    machine = machine or service.machine_code
    return create_license(machine, "month", days)


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
    def test_activate_valid_key(self, service):
        ok, msg = service.activate(_make_key(service))
        assert ok is True
        st = service.status()
        assert st["licensed"] is True
        assert st["valid"] is True
        assert st["reason"] == "ok"

    def test_activate_wrong_machine_rejected(self, service):
        key = _make_key(service, machine="OTHER-OTHER-OTHER-OTHER")
        ok, msg = service.activate(key)
        assert ok is False
        assert "不匹配" in msg

    def test_activate_invalid_key(self, service):
        ok, msg = service.activate("SBF-not-a-valid-key")
        assert ok is False

    def test_activate_expired_key(self, service):
        from datetime import datetime, timedelta

        from core.license import create_license

        issued = datetime.now() - timedelta(days=60)
        key = create_license(service.machine_code, "month", 30, issued_at=issued)
        ok, msg = service.activate(key)
        assert ok is False
        assert "过期" in msg

    def test_activation_stored_in_multiple_locations(self, service):
        service.activate(_make_key(service))
        for path in service._license_paths():
            assert path.exists(), f"缺少授权文件: {path}"

    def test_anti_deletion_bypass(self, ctx, tmp_path):
        """删除数据库与部分授权文件后，激活仍可从其他位置恢复。"""
        home = tmp_path / "home"
        service = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        service.activate(_make_key(service))

        # 攻击：删掉数据库激活记录 + 前两个授权文件
        LicenseRepository(ctx.db).deactivate()
        for path in service._license_paths()[:2]:
            path.unlink(missing_ok=True)

        # 重新创建服务实例，应仍能恢复激活
        service2 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        st = service2.status()
        assert st["licensed"] is True
        assert st["valid"] is True

    def test_delete_all_forces_reactivation(self, ctx, tmp_path):
        home = tmp_path / "home"
        service = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        service.activate(_make_key(service))
        LicenseRepository(ctx.db).deactivate()
        for path in service._license_paths():
            path.unlink(missing_ok=True)

        service2 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        st = service2.status()
        assert st["licensed"] is False  # 授权丢失，不再处于已激活状态

    def test_deactivate(self, service):
        service.activate(_make_key(service))
        service.deactivate()
        st = service.status()
        assert st["licensed"] is False
        assert st["trial"] is True  # 回到试用

    def test_activate_supersedes_old(self, ctx, tmp_path):
        home = tmp_path / "home"
        s1 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        s1.activate(_make_key(s1, days=30))
        s2 = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=home)
        s2.activate(_make_key(s2, days=90))
        st = s2.status()
        expires2 = s2._get_activated_info()
        assert st["licensed"] is True


class TestMachineBinding:
    def test_machine_code_exposed(self, service):
        assert service.machine_code
