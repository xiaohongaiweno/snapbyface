"""授权核心：机器码、授权码签名与解析（规格 §22-24）。

授权码格式: SBF-<base64(payload)>-<signature>
payload 内含: 机器码 / 授权类型 / 签发时间 / 到期时间
签名: HMAC-SHA256(payload, SECRET)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

LICENSE_SECRET = "SnapByFace-Offline-License-V1-2026"
KEY_PREFIX = "SBF"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


# ----------------------------------------------------------------------
# 机器码
# ----------------------------------------------------------------------
def generate_machine_code() -> str:
    """基于硬件特征生成机器码（MAC + 主机名 + 平台）。"""
    import platform
    import uuid

    mac = uuid.getnode()
    raw = f"{mac:x}|{platform.node()}|{platform.machine()}|{platform.system()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    return "-".join(digest[i:i + 8] for i in range(0, 32, 8))


# ----------------------------------------------------------------------
# 授权信息
# ----------------------------------------------------------------------
@dataclass
class LicenseInfo:
    machine_code: str
    license_type: str
    issued_at: str
    expires_at: str

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        return now > datetime.strptime(self.expires_at, DATETIME_FMT)


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_license(
    machine_code: str,
    license_type: str,
    days: int,
    secret: str = LICENSE_SECRET,
    issued_at: datetime | None = None,
) -> str:
    """厂商签发授权码。"""
    issued = issued_at or datetime.now()
    expires = issued + timedelta(days=days)
    info = LicenseInfo(
        machine_code=machine_code,
        license_type=license_type,
        issued_at=issued.strftime(DATETIME_FMT),
        expires_at=expires.strftime(DATETIME_FMT),
    )
    payload = base64.urlsafe_b64encode(
        json.dumps(info.__dict__).encode("utf-8")
    ).decode("ascii")
    signature = _sign(payload, secret)[:32]
    return f"{KEY_PREFIX}-{payload}-{signature}"


def decode_license(key: str, secret: str = LICENSE_SECRET) -> LicenseInfo | None:
    """解析并验证授权码，失败返回 None。"""
    try:
        parts = key.strip().split("-")
        if len(parts) != 3 or parts[0] != KEY_PREFIX:
            return None
        _, payload, signature = parts
        expected = _sign(payload, secret)[:32]
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        return LicenseInfo(**data)
    except Exception:  # noqa: BLE001 - 任何解析失败视为无效
        return None
