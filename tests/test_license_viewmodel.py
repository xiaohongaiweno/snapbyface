"""授权 ViewModel 单元测试。"""
from __future__ import annotations

import pytest

from core.license import create_license
from services.license_service import LicenseService
from viewmodels.license_viewmodel import LicenseViewModel


@pytest.fixture
def vm(qapp, ctx, tmp_path) -> LicenseViewModel:
    svc = LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=tmp_path / "home")
    return LicenseViewModel(svc)


class TestLicenseViewModel:
    def test_machine_code(self, vm):
        assert vm.machine_code()

    def test_initial_status_is_trial(self, vm):
        st = vm.status()
        assert st["trial"] is True

    def test_activate_valid_key(self, vm):
        key = create_license(vm.machine_code(), "month", 30)
        ok, msg = vm.activate(key)
        assert ok is True
        st = vm.status()
        assert st["licensed"] is True

    def test_activate_invalid_key(self, vm):
        ok, _ = vm.activate("invalid-key")
        assert ok is False
