"""日志页：最近操作日志。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.theme import page_header, panel
from viewmodels.log_viewmodel import LogViewModel


class LogPage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._vm = LogViewModel(application.op_log_repo)

        title, subtitle = page_header("日志", "查看最近的系统操作与后台任务记录")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["时间", "分类", "级别", "内容"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh)

        table_panel, table_layout = panel("最近记录")
        table_layout.addWidget(self.table)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(table_panel, 1)
        layout.addWidget(btn_refresh)
        self.refresh()

    def refresh(self) -> None:
        rows = self._vm.recent()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["created_at"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["category"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["level"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["message"]))
