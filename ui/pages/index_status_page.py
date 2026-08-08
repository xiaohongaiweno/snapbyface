"""索引状态页（规格 §13）。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.theme import page_header, panel
from viewmodels.index_status_viewmodel import IndexStatusViewModel

FIELDS = [
    ("total", "照片总数"),
    ("done", "已扫描"),
    ("indexing", "处理中"),
    ("pending", "未完成"),
    ("failed", "失败"),
    ("queue_size", "待处理队列"),
    ("last_updated", "最后更新时间"),
]


class IndexStatusPage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._vm = IndexStatusViewModel(
            application.photo_service, application.index_service
        )
        self._labels: dict[str, QLabel] = {}

        title, subtitle = page_header("索引状态", "查看照片索引进度与后台任务状态")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        status_panel, status_layout = panel("当前状态")
        for key, label in FIELDS:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            value = QLabel("-")
            value.setStyleSheet("font-weight: bold;")
            row.addWidget(value, 1)
            status_layout.addLayout(row)
            self._labels[key] = value
        layout.addWidget(status_panel)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)
        layout.addStretch(1)

        # 自动刷新
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.refresh)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def refresh(self) -> None:
        stats = self._vm.refresh()
        for key, _ in FIELDS:
            self._labels[key].setText(str(stats.get(key, "-")))
