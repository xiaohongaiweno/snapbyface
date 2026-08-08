"""SnapByFace desktop theme and small UI helpers."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


COLORS = {
    "ink": "#17202a",
    "muted": "#6b7785",
    "line": "#dfe5eb",
    "surface": "#ffffff",
    "canvas": "#f3f6f8",
    "nav": "#172a3a",
    "nav_muted": "#a9bac7",
    "accent": "#e56b3f",
    "accent_dark": "#c6532c",
}


def app_stylesheet() -> str:
    """Return a platform-neutral QSS theme."""
    return f"""
    QWidget {{
        color: {COLORS["ink"]};
        font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QWidget#appCanvas {{
        background: {COLORS["canvas"]};
    }}
    QLabel#pageTitle {{
        font-size: 24px;
        font-weight: 700;
        color: {COLORS["ink"]};
    }}
    QLabel#pageKicker {{
        color: {COLORS["muted"]};
        font-size: 12px;
    }}
    QLabel#sectionTitle {{
        font-size: 15px;
        font-weight: 700;
    }}
    QFrame[panel="true"] {{
        background: {COLORS["surface"]};
        border: 1px solid {COLORS["line"]};
        border-radius: 8px;
    }}
    QListWidget#sidebar {{
        background: {COLORS["nav"]};
        border: none;
        color: {COLORS["nav_muted"]};
        padding: 12px 8px;
        outline: none;
    }}
    QListWidget#sidebar::item {{
        min-height: 42px;
        padding: 0 14px;
        border-radius: 6px;
        margin: 3px 0;
    }}
    QListWidget#sidebar::item:hover {{
        background: #244155;
        color: white;
    }}
    QListWidget#sidebar::item:selected {{
        background: {COLORS["accent"]};
        color: white;
        font-weight: 700;
    }}
    QPushButton {{
        min-height: 34px;
        padding: 0 16px;
        border: 1px solid #cbd5dc;
        border-radius: 5px;
        background: white;
        color: {COLORS["ink"]};
    }}
    QPushButton:hover {{
        border-color: {COLORS["accent"]};
        color: {COLORS["accent_dark"]};
    }}
    QPushButton:disabled {{
        color: #9ca8b1;
        background: #edf1f3;
    }}
    QPushButton[primary="true"] {{
        background: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
        color: white;
        font-weight: 700;
    }}
    QPushButton[primary="true"]:hover {{
        background: {COLORS["accent_dark"]};
        border-color: {COLORS["accent_dark"]};
    }}
    QPushButton[mode="true"] {{
        min-height: 64px;
        text-align: left;
        font-size: 15px;
        font-weight: 700;
        padding: 0 18px;
    }}
    QPushButton[mode="true"]:checked {{
        background: #fff0ea;
        border: 2px solid {COLORS["accent"]};
        color: {COLORS["accent_dark"]};
    }}
    QLineEdit, QDoubleSpinBox {{
        min-height: 34px;
        border: 1px solid #cbd5dc;
        border-radius: 5px;
        padding: 0 10px;
        background: white;
    }}
    QLineEdit:focus, QDoubleSpinBox:focus {{
        border: 1px solid {COLORS["accent"]};
    }}
    QListWidget#results {{
        background: white;
        border: 1px solid {COLORS["line"]};
        border-radius: 6px;
        outline: none;
    }}
    QListWidget#results::item {{
        padding: 8px;
        border-bottom: 1px solid #edf0f2;
    }}
    QListWidget#results::item:selected {{
        background: #fff0ea;
        color: {COLORS["ink"]};
        border-left: 3px solid {COLORS["accent"]};
    }}
    QProgressBar {{
        min-height: 8px;
        max-height: 8px;
        border: none;
        border-radius: 4px;
        background: #e8edf0;
        text-align: center;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background: {COLORS["accent"]};
    }}
    QStatusBar {{
        background: white;
        border-top: 1px solid {COLORS["line"]};
        color: {COLORS["muted"]};
    }}
    """


def panel(title: str | None = None, parent: QWidget | None = None) -> tuple[QFrame, QVBoxLayout]:
    """Create a consistently padded surface panel."""
    frame = QFrame(parent)
    frame.setProperty("panel", True)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    if title:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
    return frame, layout


def page_header(title: str, kicker: str) -> tuple[QLabel, QLabel]:
    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    kicker_label = QLabel(kicker)
    kicker_label.setObjectName("pageKicker")
    return title_label, kicker_label
