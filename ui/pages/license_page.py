"""授权页（规格 §22 授权系统）。Phase 7 接入完整逻辑。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import page_header, panel

OFFICIAL_SITE_URL = "https://snapbyface.com"


class LicensePage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._app = application
        # Phase 7 注入 LicenseViewModel
        self._vm = getattr(application, "license_viewmodel", None)

        title, subtitle = page_header("授权", "查看当前授权状态并激活本机")

        self.machine_label = QLabel("机器码: -")
        btn_copy_machine = QPushButton("复制")
        btn_copy_machine.clicked.connect(self._copy_machine_code)
        self.status_label = QLabel("激活状态: 未激活")
        self.expiry_label = QLabel("有效期: -")
        self.trial_label = QLabel("试用状态: -")

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 PHX-... 授权码")
        btn_activate = QPushButton("激活")
        btn_activate.clicked.connect(self._activate)
        btn_open_site = QPushButton("打开官网")
        btn_open_site.clicked.connect(self._open_official_site)

        machine_row = QHBoxLayout()
        machine_row.addWidget(self.machine_label, 1)
        machine_row.addWidget(btn_copy_machine)

        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(btn_activate)
        key_row.addWidget(btn_open_site)

        license_panel, license_layout = panel("本机授权")
        license_layout.addLayout(machine_row)
        license_layout.addWidget(self.status_label)
        license_layout.addWidget(self.expiry_label)
        license_layout.addWidget(self.trial_label)
        license_layout.addSpacing(8)
        license_layout.addWidget(QLabel("授权码"))
        license_layout.addLayout(key_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(license_panel)
        layout.addStretch(1)

        if self._vm is not None:
            self.refresh()

    def refresh(self) -> None:
        if self._vm is None:
            return
        self.machine_label.setText(f"机器码: {self._vm.machine_code()}")
        status = self._vm.status()
        status_text, expiry_text, trial_text = self._format_status(status)
        self.status_label.setText(status_text)
        self.expiry_label.setText(expiry_text)
        self.trial_label.setText(trial_text)

    def _format_status(self, status: dict) -> tuple[str, str, str]:
        expires_at = status.get("expires_at") or "-"
        days_left = status.get("days_left")

        if status.get("licensed"):
            if status.get("valid"):
                return "激活状态: 已激活", f"有效期: {expires_at}", "试用状态: 已转为正式授权"
            return "激活状态: 授权已过期", f"有效期: {expires_at}", "试用状态: -"

        if status.get("trial"):
            if status.get("valid"):
                return (
                    "激活状态: 试用中",
                    f"试用到期: {expires_at}",
                    f"试用剩余: {days_left} 天",
                )
            return "激活状态: 试用已结束", f"试用到期: {expires_at}", "试用剩余: 0 天"

        return "激活状态: 未激活", "有效期: -", "试用状态: -"

    def _activate(self) -> None:
        if self._vm is None:
            QMessageBox.information(self, "授权", "授权模块尚未接入")
            return
        key = self.key_edit.text().strip()
        ok, msg = self._vm.activate(key)
        QMessageBox.information(self, "授权", msg)
        self.refresh()

    def _copy_machine_code(self) -> None:
        if self._vm is None:
            return
        QApplication.clipboard().setText(self._vm.machine_code())
        QMessageBox.information(self, "授权", "机器码已复制")

    def _open_official_site(self) -> None:
        QDesktopServices.openUrl(QUrl(OFFICIAL_SITE_URL))
