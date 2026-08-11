"""License core compatible with the SnapByFace license center.

Machine codes follow the license-center format: ``PX-XXXX-XXXX-XXXX``.
License codes follow the PHX envelope used by photo-x-web:
Base32 grouped JSON payload + SECP256R1 ECDSA signature.
"""
from __future__ import annotations

import base64
import hashlib
import json
import platform
import secrets
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

LICENSE_SECRET = "SnapByFace-PHX-License-Center-V1"
KEY_PREFIX = "PHX"
CODE_PREFIX = KEY_PREFIX
SCHEMA_VERSION = 1
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
LICENSE_TYPE_COUNT = "count"
LICENSE_TYPE_DURATION = "duration"
LICENSE_TYPE_PERPETUAL = "perpetual"
LICENSE_TYPES = {LICENSE_TYPE_COUNT, LICENSE_TYPE_DURATION, LICENSE_TYPE_PERPETUAL}

DEFAULT_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAENI1oF1XiFurKBniG0oKOKUfhyocp
D9UZGedIwN8anxfHvsnuWfMkH4v5uJ3Mh/QNak11o2KREpE3Ia1+p0YCHQ==
-----END PUBLIC KEY-----
"""


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return ""
    return (result.stdout or result.stderr or "").strip()


def _windows_machine_guid() -> str:
    if platform.system() != "Windows":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except Exception:
        return ""


def _cpu_info() -> str:
    system = platform.system()
    if system == "Windows":
        value = _run(["wmic", "cpu", "get", "ProcessorId", "/value"])
        return value or platform.processor()
    if system == "Darwin":
        value = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        return value or platform.processor()
    try:
        return Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")[:500]
    except Exception:
        return platform.processor() or platform.machine()


def _disk_serial() -> str:
    system = platform.system()
    if system == "Windows":
        return _run(["wmic", "diskdrive", "get", "SerialNumber", "/value"])
    if system == "Darwin":
        serial = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
        for line in serial.splitlines():
            if "IOPlatformSerialNumber" in line:
                return line.strip()
        return _run(["diskutil", "info", "/"])
    return _run(["lsblk", "-ndo", "SERIAL"])


def get_machine_fingerprint() -> str:
    parts = [
        platform.system(),
        platform.machine(),
        platform.node(),
        _windows_machine_guid(),
        _cpu_info(),
        _disk_serial(),
    ]
    try:
        parts.append(str(uuid.getnode()))
    except Exception:
        pass
    return "|".join(part.strip() for part in parts if part and part.strip())


def format_machine_code(hex_digest: str) -> str:
    compact = hex_digest.upper()[:12].ljust(12, "0")
    return f"PX-{compact[0:4]}-{compact[4:8]}-{compact[8:12]}"


def generate_machine_code() -> str:
    digest = hashlib.sha256(get_machine_fingerprint().encode("utf-8", errors="replace")).hexdigest()
    return format_machine_code(digest)


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def grouped_code(prefix: str, payload: bytes, group_size: int = 5) -> str:
    encoded = base64.b32encode(payload).decode("ascii").rstrip("=")
    groups = [encoded[index:index + group_size] for index in range(0, len(encoded), group_size)]
    return f"{prefix}-" + "-".join(groups)


def ungrouped_code(code: str, prefix: str) -> bytes:
    compact = "".join(ch for ch in code.strip().upper() if ch.isalnum())
    expected = prefix.replace("-", "").upper()
    if not compact.startswith(expected):
        raise ValueError("授权码格式无效")
    body = compact[len(expected):]
    if not body:
        raise ValueError("授权码内容为空")
    padding = "=" * (-len(body) % 8)
    return base64.b32decode((body + padding).encode("ascii"))


def _public_key_data(public_key_path: str | Path | None = None) -> bytes:
    if public_key_path is not None:
        return Path(public_key_path).read_bytes()
    return DEFAULT_PUBLIC_KEY_PEM.encode("utf-8")


def load_public_key(public_key_path: str | Path | None = None):
    return serialization.load_pem_public_key(_public_key_data(public_key_path))


def load_private_key(private_key_path: str | Path):
    return serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)


def sign_payload(payload: dict[str, Any], private_key_path: str | Path) -> str:
    private_key = load_private_key(private_key_path)
    signature = private_key.sign(canonical_json(payload).encode("utf-8"), ec.ECDSA(hashes.SHA256()))
    return b64url_encode(signature)


def verify_payload(
    payload: dict[str, Any],
    signature: str,
    public_key_path: str | Path | None = None,
) -> bool:
    try:
        public_key = load_public_key(public_key_path)
        public_key.verify(
            b64url_decode(signature),
            canonical_json(payload).encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, Exception):
        return False


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_status_datetime(value: str) -> str:
    if not value:
        return ""
    return _parse_iso_datetime(value).astimezone().strftime(DATETIME_FMT)


def _license_hash(payload: dict[str, Any], signature: str) -> str:
    return hashlib.sha256(canonical_json({"payload": payload, "signature": signature}).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LicenseInfo:
    machine: str
    credits: int
    nonce: str
    issue_time: str
    payload: dict[str, Any]
    signature: str
    raw_code: str
    license_type: str = LICENSE_TYPE_COUNT
    expires_at: str = ""
    duration_days: int = 0

    @property
    def machine_code(self) -> str:
        return self.machine

    @property
    def issued_at(self) -> str:
        return self.issue_time

    @property
    def license_hash(self) -> str:
        return _license_hash(self.payload, self.signature)

    @property
    def is_unlimited(self) -> bool:
        return self.license_type in {LICENSE_TYPE_DURATION, LICENSE_TYPE_PERPETUAL}

    def is_expired(self, now: datetime | None = None) -> bool:
        if not self.expires_at:
            return False
        current = now
        if current is None:
            current = datetime.now(UTC)
        elif current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return _parse_iso_datetime(self.expires_at) <= current.astimezone(UTC)

    def display_expires_at(self) -> str:
        if self.license_type == LICENSE_TYPE_PERPETUAL:
            return "永久"
        return _format_status_datetime(self.expires_at)


def parse_license_code(code: str) -> tuple[dict[str, Any], str]:
    try:
        raw = ungrouped_code(code, CODE_PREFIX)
        envelope = json.loads(raw.decode("utf-8"))
        payload = envelope["payload"]
        signature = str(envelope["signature"])
    except Exception as exc:
        raise ValueError("授权码格式无效") from exc
    if not isinstance(payload, dict):
        raise ValueError("授权码载荷无效")
    return payload, signature


def validate_license_code(
    code: str,
    machine_code: str,
    public_key_path: str | Path | None = None,
) -> LicenseInfo:
    payload, signature = parse_license_code(code)
    if int(payload.get("schema", 0)) != SCHEMA_VERSION:
        raise ValueError("授权码版本不受支持")
    if not verify_payload(payload, signature, public_key_path):
        raise ValueError("授权码无效")
    if str(payload.get("machine", "")) != machine_code:
        raise ValueError("授权码不属于当前设备")

    license_type = str(payload.get("licenseType", LICENSE_TYPE_COUNT) or LICENSE_TYPE_COUNT).lower()
    if license_type not in LICENSE_TYPES:
        raise ValueError("授权码类型无效")
    try:
        credits = int(payload.get("credits", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("授权码额度无效") from exc
    if license_type == LICENSE_TYPE_COUNT and credits <= 0:
        raise ValueError("授权码额度无效")
    if license_type != LICENSE_TYPE_COUNT and credits < 0:
        raise ValueError("授权码额度无效")

    expires_at = str(payload.get("expiresAt", ""))
    if license_type == LICENSE_TYPE_DURATION and not expires_at:
        raise ValueError("时长授权缺少到期时间")
    if expires_at:
        try:
            _parse_iso_datetime(expires_at)
        except ValueError as exc:
            raise ValueError("授权码到期时间无效") from exc

    try:
        duration_days = int(payload.get("durationDays", 0) or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("授权码时长无效") from exc
    issue_time = str(payload.get("issueTime", ""))
    if issue_time:
        try:
            datetime.fromisoformat(issue_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("授权码签发时间无效") from exc

    return LicenseInfo(
        machine=machine_code,
        credits=credits,
        nonce=str(payload.get("nonce", "")),
        issue_time=issue_time,
        payload=payload,
        signature=signature,
        raw_code=code.strip(),
        license_type=license_type,
        expires_at=expires_at,
        duration_days=duration_days,
    )


def decode_license(
    key: str,
    public_key_path: str | Path | None = None,
    machine_code: str | None = None,
) -> LicenseInfo | None:
    try:
        payload, signature = parse_license_code(key)
        target_machine = machine_code or str(payload.get("machine", ""))
        return validate_license_code(key, target_machine, public_key_path)
    except Exception:
        return None


def create_license(
    machine_code: str,
    license_type: str,
    days: int,
    private_key_path: str | Path | None = None,
    issued_at: datetime | None = None,
    credits: int = 0,
    nonce: str | None = None,
) -> str:
    """Create a PHX license code with an ECC private key.

    This is intended for tests and offline vendor tools. Production codes are
    normally generated by photo-x-web.
    """
    if private_key_path is None:
        raise FileNotFoundError("必须提供 ECC 私钥路径，或使用 photo-x-web 授权中心签发")
    license_type = (license_type or LICENSE_TYPE_COUNT).strip().lower()
    if license_type == "month":
        license_type = LICENSE_TYPE_DURATION
    if license_type not in LICENSE_TYPES:
        raise ValueError("授权类型无效")

    issued = issued_at or datetime.now(UTC)
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=UTC)
    issue_time = issued.astimezone(UTC).date().isoformat()
    expires_at = ""
    duration_days = 0
    if license_type == LICENSE_TYPE_DURATION:
        duration_days = int(days)
        expires_at = (issued.astimezone(UTC) + timedelta(days=duration_days)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")

    payload = {
        "schema": SCHEMA_VERSION,
        "machine": machine_code,
        "credits": int(credits) if license_type == LICENSE_TYPE_COUNT else 0,
        "licenseType": license_type,
        "nonce": (nonce or secrets.token_urlsafe(12).replace("_", "").replace("-", "").upper()[:16]),
        "issueTime": issue_time,
    }
    if expires_at:
        payload["expiresAt"] = expires_at
    if duration_days > 0:
        payload["durationDays"] = duration_days
    signature = sign_payload(payload, private_key_path)
    envelope = {"payload": payload, "signature": signature}
    return grouped_code(CODE_PREFIX, json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
