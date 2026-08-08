"""授权页（规格 §22 授权系统）。Phase 7 接入完整逻辑。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import page_header, panel


class LicensePage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._app = application
        # Phase 7 注入 LicenseViewModel
        self._vm = getattr(application, "license_viewmodel", None)

        title, subtitle = page_header("授权", "查看当前授权状态并激活本机")

        self.machine_label = QLabel("机器码: -")
        self.status_label = QLabel("状态: 未激活")

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入授权码")
        btn_activate = QPushButton("激活")
        btn_activate.clicked.connect(self._activate)

        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(btn_activate)

        license_panel, license_layout = panel("本机授权")
        license_layout.addWidget(self.machine_label)
        license_layout.addWidget(self.status_label)
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
        self.status_label.setText(f"状态: {status}")

    def _activate(self) -> None:
        if self._vm is None:
            QMessageBox.information(self, "授权", "授权模块尚未接入")
            return
        key = self.key_edit.text().strip()
        ok, msg = self._vm.activate(key)
        QMessageBox.information(self, "授权", msg)
        self.refresh()
