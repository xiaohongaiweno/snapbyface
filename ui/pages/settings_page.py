"""设置页：照片目录 + 人脸参数（规格 §21）。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import page_header, panel
from viewmodels.settings_viewmodel import SettingsViewModel


class SettingsPage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._app = application
        self._vm = SettingsViewModel(application.photo_service)

        title, subtitle = page_header("设置", "配置照片目录与人脸匹配参数")

        # 照片目录
        self.dir_edit = QLineEdit(self._vm.get_photo_directory())
        self.dir_edit.setPlaceholderText("例如 D:/SnapPhotos")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(btn_browse)

        # 相似度阈值
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(self._vm.get_threshold())

        btn_save = QPushButton("保存设置")
        btn_save.clicked.connect(self._save)

        directory_panel, directory_layout = panel("照片目录")
        directory_layout.addWidget(QLabel("照片目录"))
        directory_layout.addLayout(dir_row)

        model_panel, model_layout = panel("人脸参数")
        model_layout.addWidget(QLabel("相似度阈值"))
        model_layout.addWidget(self.threshold_spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(directory_panel)
        layout.addWidget(model_panel)
        layout.addSpacing(12)
        layout.addWidget(btn_save)
        layout.addStretch(1)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择照片目录")
        if path:
            self.dir_edit.setText(path)

    def _save(self) -> None:
        ok, err = self._vm.set_photo_directory(self.dir_edit.text())
        if not ok:
            QMessageBox.warning(self, "设置", f"照片目录无效: {err}")
            return
        self._vm.set_threshold(self.threshold_spin.value())
        try:
            summary = self._app.refresh_photo_directory()
        except Exception as exc:  # noqa: BLE001 - UI 需要把失败原因反馈给用户
            QMessageBox.warning(self, "设置", f"设置已保存，但自动扫描失败: {exc}")
            return
        QMessageBox.information(
            self,
            "设置",
            (
                "设置已保存，已开始扫描照片目录。\n"
                f"发现文件 {summary['total_files']} 个，"
                f"新增 {summary['new_photos']} 个，"
                f"提交索引 {summary['enqueued']} 个。"
            ),
        )
