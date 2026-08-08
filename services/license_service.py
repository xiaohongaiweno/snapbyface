"""授权服务：试用、激活、到期检查、防删除绕过（规格 §22-24）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math

from core.config import ConfigManager
from core.license import (
    DATETIME_FMT,
    LICENSE_SECRET,
    LicenseInfo,
    decode_license,
    generate_machine_code,
)
from core.logger import get_logger
from database.connection import Database
from repositories.license_repository import LicenseRepository

logger = get_logger("service.license")

TRIAL_CONFIG_KEY = "trial_start"


class LicenseService:
    """负责授权生命周期。

    激活信息同时写入多个位置（规格 §24 防删除绕过）：
    - 数据库 license 表
    - 应用目录 license.dat
    - 用户主目录 .snapbyface_license.dat
    - 数据目录隐藏文件 .lic
    """

    def __init__(
        self,
        db: Database,
        config: ConfigManager,
        app_dir: Path | str,
        secret: str = LICENSE_SECRET,
        home_dir: Path | str | None = None,
        logger=None,
    ) -> None:
        self._db = db
        self._config = config
        self._app_dir = Path(app_dir)
        self._home_dir = Path(home_dir) if home_dir is not None else Path.home()
        self._secret = secret
        self._repo = LicenseRepository(db)
        self._logger = logger or get_logger("service.license")
        self._machine = generate_machine_code()

    @property
    def machine_code(self) -> str:
        return self._machine

    @property
    def trial_days(self) -> int:
        return int(self._config.get("license.trial_days", 15))

    # ------------------------------------------------------------------
    # 多位置存储
    # ------------------------------------------------------------------
    def _license_paths(self) -> list[Path]:
        return [
            self._app_dir / "license.dat",
            self._home_dir / ".snapbyface_license.dat",
            self._app_dir / "data" / ".lic",
        ]

    def _write_license_files(self, key: str) -> None:
        for path in self._license_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(key, encoding="utf-8")
            except OSError as exc:
                self._logger.warning("写入授权文件失败 %s: %s", path, exc)

    def _read_license_from_files(self) -> str | None:
        for path in self._license_paths():
            try:
                if path.exists():
                    key = path.read_text(encoding="utf-8").strip()
                    if key and decode_license(key, self._secret) is not None:
                        return key
            except OSError:
                continue
        return None

    def _purge_license_files(self) -> None:
        for path in self._license_paths():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    def status(self) -> dict:
        """返回授权状态。

        字段: valid / licensed / trial / reason / expires_at / days_left / machine_code
        """
        licensed = self._get_activated_info()
        if licensed is not None:
            base = self._base_status()
            if licensed.is_expired():
                base.update(
                    valid=False, licensed=True, trial=False,
                    reason="expired", expires_at=licensed.expires_at,
                )
            else:
                base.update(
                    valid=True, licensed=True, trial=False,
                    reason="ok", expires_at=licensed.expires_at,
                )
            return base

        trial_start = self._get_trial_start()
        if trial_start is None:
            # 首次运行：开始试用
            self._start_trial()
            trial_start = self._get_trial_start()

        expires = self._trial_expires(trial_start)
        remaining_seconds = (expires - datetime.now()).total_seconds()
        days_left = max(0, int(math.ceil(remaining_seconds / 86400)))
        base = self._base_status()
        if days_left <= 0:
            base.update(valid=False, licensed=False, trial=True, reason="trial_expired",
                        expires_at=expires.strftime(DATETIME_FMT), days_left=0)
        else:
            base.update(valid=True, licensed=False, trial=True, reason="trial",
                        expires_at=expires.strftime(DATETIME_FMT), days_left=days_left)
        return base

    def _base_status(self) -> dict:
        return {
            "valid": False,
            "licensed": False,
            "trial": False,
            "reason": "none",
            "expires_at": None,
            "days_left": None,
            "machine_code": self._machine,
            "trial_days": self.trial_days,
        }

    def is_valid(self) -> bool:
        return bool(self.status()["valid"])

    # ------------------------------------------------------------------
    # 激活
    # ------------------------------------------------------------------
    def activate(self, key: str) -> tuple[bool, str]:
        """使用授权码激活。

        返回: (是否成功, 提示信息)。
        """
        key = key.strip()
        info = decode_license(key, self._secret)
        if info is None:
            return False, "授权码无效"
        if info.machine_code != self._machine:
            return False, "授权码与当前机器码不匹配"
        if info.is_expired():
            return False, f"授权码已过期（{info.expires_at}）"

        with self._db.transaction():
            self._repo.save_activated(
                machine_code=info.machine_code,
                license_key=key,
                license_type=info.license_type,
                issued_at=info.issued_at,
                expires_at=info.expires_at,
            )
        self._write_license_files(key)
        self._logger.info("激活成功: %s 有效期至 %s", info.license_type, info.expires_at)
        return True, f"激活成功，有效期至 {info.expires_at}"

    def deactivate(self) -> None:
        self._repo.deactivate()
        self._purge_license_files()
        self._logger.info("已注销激活")

    def _get_activated_info(self) -> LicenseInfo | None:
        """从数据库或文件恢复激活信息。"""
        row = self._repo.get_active()
        if row is not None and row.get("license_key"):
            info = decode_license(row["license_key"], self._secret)
            if info is not None:
                return info
        key = self._read_license_from_files()
        if key is not None:
            return decode_license(key, self._secret)
        return None

    # ------------------------------------------------------------------
    # 试用
    # ------------------------------------------------------------------
    def _trial_expires(self, start: datetime) -> datetime:
        from datetime import timedelta

        return start + timedelta(days=self.trial_days)

    def _trial_paths(self) -> list[Path]:
        return [
            self._app_dir / "trial.dat",
            self._home_dir / ".snapbyface_trial.dat",
        ]

    def _start_trial(self) -> None:
        now = datetime.now().strftime(DATETIME_FMT)
        self._repo.set_config(TRIAL_CONFIG_KEY, now)
        for path in self._trial_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(now, encoding="utf-8")
            except OSError:
                continue
        self._logger.info("开始 15 天试用")

    def _get_trial_start(self) -> datetime | None:
        raw = self._repo.get_config(TRIAL_CONFIG_KEY)
        if raw is None:
            for path in self._trial_paths():
                try:
                    if path.exists():
                        raw = path.read_text(encoding="utf-8").strip()
                        if raw:
                            break
                except OSError:
                    continue
        if raw is None:
            return None
        try:
            return datetime.strptime(raw, DATETIME_FMT)
        except ValueError:
            return None
