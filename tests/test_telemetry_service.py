"""Telemetry service tests."""
from __future__ import annotations

import json

from services.license_service import LicenseService
from services.telemetry_service import TelemetryService


class FakeResponse:
    def __init__(self, status=200):
        self.status = status
        self.body_read = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        self.body_read = True
        return b'{"code":0}'


def _license_service(ctx, tmp_path):
    return LicenseService(ctx.db, ctx.config, ctx.app_dir, home_dir=tmp_path / "home")


def test_build_payload_matches_server_schema(ctx, tmp_path):
    service = TelemetryService(ctx.config, _license_service(ctx, tmp_path))
    payload = service.build_payload()

    assert payload["app_version"]
    assert payload["os"]
    assert payload["os_version"]
    assert payload["cpu_arch"]
    assert payload["language"]
    assert payload["country"]
    assert payload["timezone"]
    assert payload["timestamp"].endswith("Z")
    assert payload["machine_id"].startswith("PX-")
    assert payload["license_total_quota"] == 0
    assert payload["license_remaining_quota"] == 0


def test_report_startup_posts_json(ctx, tmp_path):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    ctx.config.set("telemetry.endpoint", "http://127.0.0.1:8000/api/v1/telemetry")
    ctx.config.set("telemetry.timeout_seconds", 1.5)
    service = TelemetryService(ctx.config, _license_service(ctx, tmp_path), urlopen=fake_urlopen)

    assert service.report_startup() is True
    request, timeout = calls[0]
    payload = json.loads(request.data.decode("utf-8"))

    assert request.full_url == "http://127.0.0.1:8000/api/v1/telemetry"
    assert request.get_method() == "POST"
    assert request.headers["Content-type"] == "application/json"
    assert request.headers["X-client-version"] == payload["app_version"]
    assert request.headers["X-platform"] == payload["os"]
    assert request.headers["X-cpu-arch"] == payload["cpu_arch"]
    assert request.headers["X-forwarded-proto"] == "https"
    assert timeout == 1.5


def test_report_startup_disabled_does_not_post(ctx, tmp_path):
    calls = []
    ctx.config.set("telemetry.enabled", False)
    service = TelemetryService(
        ctx.config,
        _license_service(ctx, tmp_path),
        urlopen=lambda request, timeout: calls.append((request, timeout)),
    )

    assert service.report_startup() is False
    assert calls == []


def test_report_startup_string_false_does_not_post(ctx, tmp_path):
    calls = []
    ctx.config.set("telemetry.enabled", "false")
    service = TelemetryService(
        ctx.config,
        _license_service(ctx, tmp_path),
        urlopen=lambda request, timeout: calls.append((request, timeout)),
    )

    assert service.report_startup() is False
    assert calls == []


def test_report_startup_failure_is_non_fatal(ctx, tmp_path):
    def fail_urlopen(request, timeout):
        raise RuntimeError("offline")

    service = TelemetryService(ctx.config, _license_service(ctx, tmp_path), urlopen=fail_urlopen)

    assert service.report_startup() is False
