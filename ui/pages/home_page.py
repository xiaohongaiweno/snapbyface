"""首页：应用概览与快捷入口。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import COLORS, page_header, panel
from viewmodels.index_status_viewmodel import IndexStatusViewModel


class HomePage(QWidget):
    def __init__(self, application: Any, main_window) -> None:
        super().__init__()
        self._app = application
        self._main_window = main_window
        self._vm = IndexStatusViewModel(
            application.photo_service, application.index_service
        )

        title, subtitle = page_header("工作台", "今天也让每一次找片都更快")

        self.stats_labels: dict[str, QLabel] = {}
        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(12)
        for index, (key, label) in enumerate([
            ("total", "照片总数"),
            ("done", "已完成索引"),
            ("indexing", "正在处理"),
            ("pending", "等待处理"),
        ]):
            card = QFrame()
            card.setProperty("panel", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            caption = QLabel(label)
            caption.setStyleSheet(f"color: {COLORS['muted']};")
            value = QLabel("-")
            value.setStyleSheet("font-size: 26px; font-weight: 800;")
            card_layout.addWidget(caption)
            card_layout.addWidget(value)
            stats_grid.addWidget(card, 0, index)
            self.stats_labels[key] = value

        index_frame, index_layout = panel("索引概览")
        index_layout.addLayout(stats_grid)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        index_layout.addWidget(self.progress)
        self.last_updated = QLabel("最后更新：-")
        self.last_updated.setStyleSheet(f"color: {COLORS['muted']};")
        index_layout.addWidget(self.last_updated)

        btn_search = QPushButton("⌕  开始找片")
        btn_search.setProperty("primary", True)
        btn_search.clicked.connect(lambda: self._main_window.navigate_to("search"))
        btn_settings = QPushButton("⚙  配置照片目录")
        btn_settings.clicked.connect(lambda: self._main_window.navigate_to("settings"))

        buttons = QGridLayout()
        buttons.addWidget(btn_search, 0, 0)
        buttons.addWidget(btn_settings, 0, 1)
        buttons.setColumnStretch(2, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(index_frame)
        layout.addSpacing(12)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def refresh_stats(self) -> None:
        stats = self._vm.refresh()
        self.stats_labels["total"].setText(str(stats["total"]))
        self.stats_labels["done"].setText(str(stats["done"]))
        self.stats_labels["indexing"].setText(str(stats["indexing"]))
        self.stats_labels["pending"].setText(str(stats["pending"]))
        done = int(stats["done"] or 0)
        total = int(stats["total"] or 0)
        self.progress.setValue(round(done / total * 100) if total else 0)
        self.last_updated.setText(f"最后更新：{stats['last_updated'] or '-'}")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_stats()
