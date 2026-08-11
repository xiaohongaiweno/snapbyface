"""Startup telemetry reporting."""
from __future__ import annotations

import json
import locale
import os
import platform
import threading
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlparse
from typing import Any, Callable

from core.config import ConfigManager
from core.logger import get_logger
from core.version import APP_NAME, app_version
from services.license_service import LicenseService

UrlOpen = Callable[..., Any]

ENV_TELEMETRY_URL = "SNAPBYFACE_TELEMETRY_URL"


def _trim(value: Any, limit: int, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return text[:limit]


def _language_country() -> tuple[str, str]:
    raw = ""
    try:
        raw = locale.getlocale()[0] or ""
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get("LANG", "")
    raw = raw.split(".", 1)[0].replace("-", "_")
    if "_" in raw:
        language, country = raw.split("_", 1)
    else:
        language, country = raw, ""
    return _trim(language, 16, "unknown"), _trim(country, 8, "unknown").upper()


def _timezone_name() -> str:
    try:
        now = datetime.now().astimezone()
        name = now.tzname() or now.strftime("%z")
        if name:
            return _trim(name, 64)
    except Exception:
        pass
    return "unknown"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", ""}
    return bool(value)


def _is_loopback_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "::1"} or host.startswith("127.")


class TelemetryService:
    """Build and submit one startup report without affecting app startup."""

    def __init__(
        self,
        config: ConfigManager,
        license_service: LicenseService,
        *,
        urlopen: UrlOpen | None = None,
        logger=None,
    ) -> None:
        self._config = config
        self._license_service = license_service
        self._urlopen = urlopen or urllib.request.urlopen
        self._logger = logger or get_logger("service.telemetry")

    @property
    def enabled(self) -> bool:
        return _as_bool(self._config.get("telemetry.enabled", True))

    @property
    def endpoint(self) -> str:
        return str(
            os.environ.get(ENV_TELEMETRY_URL)
            or self._config.get("telemetry.endpoint", "")
            or ""
        ).strip()

    @property
    def timeout_seconds(self) -> float:
        try:
            return max(0.1, float(self._config.get("telemetry.timeout_seconds", 3)))
        except (TypeError, ValueError):
            return 3.0

    def build_payload(self) -> dict[str, Any]:
        language, country = _language_country()
        total_quota, remaining_quota = self._license_service.quota_summary()
        return {
            "app_version": app_version(),
            "os": _trim(platform.system(), 32),
            "os_version": _trim(platform.platform(), 64),
            "cpu_arch": _trim(platform.machine() or platform.processor(), 32),
            "language": language,
            "country": country,
            "timezone": _timezone_name(),
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            "machine_id": _trim(self._license_service.machine_code, 64),
            "license_total_quota": total_quota,
            "license_remaining_quota": remaining_quota,
        }

    def report_startup(self) -> bool:
        """Submit startup telemetry once. Returns False for disabled/failures."""
        endpoint = self.endpoint
        if not self.enabled:
            self._logger.info("启动遥测已禁用")
            return False
        if not endpoint:
            self._logger.info("启动遥测未配置接口地址")
            return False

        try:
            payload = self.build_payload()
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": (
                    f"{APP_NAME}/{payload['app_version']} "
                    f"({payload['os']}; {payload['cpu_arch']})"
                ),
                "X-Client-Version": payload["app_version"],
                "X-Platform": payload["os"],
                "X-CPU-Arch": payload["cpu_arch"],
            }
            if urlparse(endpoint).scheme == "http" and _is_loopback_url(endpoint):
                headers["X-Forwarded-Proto"] = "https"
            request = urllib.request.Request(
                endpoint, data=body, headers=headers, method="POST"
            )
            with self._urlopen(request, timeout=self.timeout_seconds) as response:
                status = int(getattr(response, "status", 0) or response.getcode())
                response.read()
            ok = 200 <= status < 300
            if ok:
                self._logger.info("启动遥测已上报: %s", endpoint)
            else:
                self._logger.warning("启动遥测上报失败: %s HTTP %s", endpoint, status)
            return ok
        except Exception as exc:
            self._logger.warning("启动遥测上报失败: %s %s", endpoint, exc)
            return False

    def report_startup_async(self) -> threading.Thread | None:
        """Start telemetry reporting in a daemon thread."""
        endpoint = self.endpoint
        if not self.enabled:
            self._logger.info("启动遥测已禁用")
            return None
        if not endpoint:
            self._logger.info("启动遥测未配置接口地址")
            return None
        self._logger.info("启动遥测已调度: %s", endpoint)
        thread = threading.Thread(
            target=self.report_startup,
            name="SnapByFaceTelemetry",
            daemon=True,
        )
        thread.start()
        return thread
