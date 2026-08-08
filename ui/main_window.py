"""主窗口：左侧导航 + 页面堆栈（规格 §19 六个页面）。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ui.pages.home_page import HomePage
from ui.pages.index_status_page import IndexStatusPage
from ui.pages.license_page import LicensePage
from ui.pages.log_page import LogPage
from ui.pages.search_page import SearchPage
from ui.pages.settings_page import SettingsPage
from ui.theme import app_stylesheet

PAGES = [
    ("⌂  首页", "home"),
    ("⌕  找片", "search"),
    ("▣  索引状态", "index"),
    ("⚙  设置", "settings"),
    ("▤  授权", "license"),
    ("≡  日志", "logs"),
]


class MainWindow(QMainWindow):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._application = application
        self.setWindowTitle("SnapByFace 景区人脸检索")
        self.resize(1240, 780)
        self.setMinimumSize(980, 640)
        self.setStyleSheet(app_stylesheet())

        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        self.nav.setMaximumWidth(220)
        self.nav.setMinimumWidth(196)
        for title, key in PAGES:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(self._nav_tooltip(key))
            self.nav.addItem(item)

        sidebar = QWidget()
        sidebar.setObjectName("sidebarShell")
        sidebar.setStyleSheet("QWidget#sidebarShell { background: #172a3a; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 14)
        sidebar_layout.setSpacing(10)
        brand = QLabel("SNAPBYFACE")
        brand.setStyleSheet("color: white; font-size: 18px; font-weight: 800;")
        brand_subtitle = QLabel("景区照片工作台")
        brand_subtitle.setStyleSheet("color: #a9bac7; font-size: 12px;")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(brand_subtitle)
        sidebar_layout.addSpacing(18)
        sidebar_layout.addWidget(self.nav, 1)
        sidebar_hint = QLabel("本地离线处理\n照片不会上传云端")
        sidebar_hint.setStyleSheet("color: #8fa4b2; font-size: 11px; padding: 8px 6px;")
        sidebar_layout.addWidget(sidebar_hint)

        self.stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        self._build_pages()

        central = QWidget()
        central.setObjectName("appCanvas")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.nav.currentRowChanged.connect(self._on_nav_changed)
        # The frontline workflow starts with search; dashboard remains one click away.
        self.nav.setCurrentRow(1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("就绪 · 本地处理模式")

    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        home = HomePage(self._application, self)
        search = SearchPage(self._application)
        index = IndexStatusPage(self._application)
        settings = SettingsPage(self._application)
        license_page = LicensePage(self._application)
        logs = LogPage(self._application)

        for key, page in [
            ("home", home),
            ("search", search),
            ("index", index),
            ("settings", settings),
            ("license", license_page),
            ("logs", logs),
        ]:
            self._pages[key] = page
            self.stack.addWidget(page)

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def navigate_to(self, key: str) -> None:
        for i, (title, k) in enumerate(PAGES):
            if k == key:
                self.nav.setCurrentRow(i)
                break

    def show_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    @staticmethod
    def _nav_tooltip(key: str) -> str:
        return {
            "home": "查看照片数量和索引进度",
            "search": "上传照片或使用摄像头找片",
            "index": "查看后台索引任务状态",
            "settings": "配置照片目录和匹配阈值",
            "license": "查看软件授权状态",
            "logs": "查看最近操作记录",
        }.get(key, "")
