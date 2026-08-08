"""Modal dialogs for the two photo-search entry points."""
from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import COLORS, panel
from utils.image import read_image
from viewmodels.search_viewmodel import SearchViewModel

PHOTO_FILTER = (
    "照片 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp "
    "*.cr2 *.cr3 *.nef *.nrw *.arw *.dng *.orf *.rw2 *.raf *.pef *.srw)"
)


class CameraSearchDialog(QDialog):
    """Capture a face from the USB camera and start a search."""

    def __init__(self, viewmodel: SearchViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel
        self._searched = False
        self.setWindowTitle("拍照找片")
        self.setMinimumSize(760, 620)

        self.preview = QLabel("摄像头未启动")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(640, 420)
        self.preview.setStyleSheet(
            "border: 1px solid #344b5b; background: #1c2b36; color: #b8c8d2; "
            "border-radius: 6px; font-size: 15px;"
        )
        self.status = QLabel("启动摄像头后，确认人脸完整进入画面")
        self.status.setStyleSheet(f"color: {COLORS['muted']};")

        start = QPushButton("▶  启动摄像头")
        stop = QPushButton("■  停止")
        search = QPushButton("⌕  拍照并搜索")
        search.setProperty("primary", True)
        close = QPushButton("关闭")
        start.clicked.connect(self._start_camera)
        stop.clicked.connect(self._stop_camera)
        search.clicked.connect(self._search)
        close.clicked.connect(self.reject)

        actions = QHBoxLayout()
        actions.addWidget(start)
        actions.addWidget(stop)
        actions.addStretch(1)
        actions.addWidget(search)
        actions.addWidget(close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.status)
        layout.addLayout(actions)

        self._timer = QTimer(self)
        self._timer.setInterval(66)
        self._timer.timeout.connect(self._refresh_preview)
        self._vm.search_error.connect(self._show_error)
        self._vm.status_message.connect(self._show_status)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()
        if not self._vm.is_camera_running():
            self._start_camera()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        self._stop_camera()
        super().hideEvent(event)

    def _start_camera(self) -> None:
        if not self._vm.start_camera():
            self.status.setText("无法打开摄像头，请检查设备权限")

    def _stop_camera(self) -> None:
        if self._vm.is_camera_running():
            self._vm.stop_camera()
        self.preview.clear()
        self.preview.setText("摄像头未启动")

    def _refresh_preview(self) -> None:
        frame = self._vm.get_latest_frame()
        if frame is not None:
            h, w = frame.shape[:2]
            self.preview.setPixmap(_frame_to_pixmap(frame, max(w, 640), max(h, 420)))

    def _search(self) -> None:
        frame = self._vm.get_latest_frame()
        if frame is None:
            frame = self._vm.capture_frame()
        if frame is None:
            self.status.setText("没有可用画面，请先启动摄像头")
            return
        height, width = frame.shape[:2]
        self.preview.setPixmap(_frame_to_pixmap(frame, max(width, 640), max(height, 420)))
        self.status.setText("照片已拍摄，正在搜索...")
        self._searched = self._vm.start_image_search(frame)
        if not self._searched:
            self.status.setText("无法发起搜索")
            return
        self.accept()

    def _show_status(self, message: str) -> None:
        self.status.setText(message)

    def _show_error(self, message: str) -> None:
        self.status.setText(message)


class UploadSearchDialog(QDialog):
    """Preview a local still image before searching."""

    def __init__(self, viewmodel: SearchViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel
        self.image: np.ndarray | None = None
        self.path = ""
        self._preview_pixmap = QPixmap()
        self.setWindowTitle("本地上传找片")
        self.setMinimumSize(760, 620)

        self.preview = QLabel("尚未选择照片")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self.preview.setStyleSheet(
            "border: 1px dashed #b9c5cc; background: #f7f9fa; color: #6b7785; "
            "border-radius: 6px; font-size: 15px;"
        )
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidget(self.preview)
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_scroll.setMinimumSize(640, 420)
        self.preview_scroll.setStyleSheet(
            "QScrollArea { background: #f7f9fa; border: none; border-radius: 6px; }"
        )
        self.file_label = QLabel("选择照片后会在这里完整预览")
        self.file_label.setStyleSheet(f"color: {COLORS['muted']};")
        self.file_label.setWordWrap(True)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {COLORS['muted']};")

        choose = QPushButton("▧  选择照片")
        search = QPushButton("⌕  搜索照片")
        search.setProperty("primary", True)
        close = QPushButton("关闭")
        choose.clicked.connect(self._choose)
        search.clicked.connect(self._search)
        close.clicked.connect(self.reject)

        actions = QHBoxLayout()
        actions.addWidget(choose)
        actions.addStretch(1)
        actions.addWidget(search)
        actions.addWidget(close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.addWidget(self.preview_scroll, 1)
        layout.addWidget(self.file_label)
        layout.addWidget(self.status)
        layout.addLayout(actions)

        self._vm.search_error.connect(self._show_error)
        self._vm.status_message.connect(self._show_status)
        self._choose()

    def _choose(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择人脸照片", "", PHOTO_FILTER)
        if not path:
            return
        image = read_image(path)
        if image is None:
            self.image = None
            self._preview_pixmap = QPixmap()
            self.file_label.setText("照片无法读取，请重新选择有效的静态照片")
            self.preview.clear()
            self.preview.setText("照片无法读取")
            return
        self.image = image
        self.path = path
        h, w = image.shape[:2]
        self._preview_pixmap = _frame_to_pixmap(image, w, h)
        self.file_label.setText(path)
        self._resize_for_image(w, h)
        QTimer.singleShot(0, self._fit_preview)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_preview()

    def _resize_for_image(self, width: int, height: int) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None or width <= 0 or height <= 0:
            return
        available = screen.availableGeometry()
        max_w = int(available.width() * 0.82)
        max_h = int(available.height() * 0.84)
        controls_w = 70
        controls_h = 190
        scale = min(
            1.0,
            max(0.1, (max_w - controls_w) / width),
            max(0.1, (max_h - controls_h) / height),
        )
        preview_w = max(640, round(width * scale))
        preview_h = max(420, round(height * scale))
        self.resize(
            min(max_w, preview_w + controls_w),
            min(max_h, preview_h + controls_h),
        )

    def _fit_preview(self) -> None:
        if self._preview_pixmap.isNull():
            return
        viewport = self.preview_scroll.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        fitted = self._preview_pixmap.scaled(
            viewport,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(fitted)
        self.preview.resize(fitted.size())

    def _search(self) -> None:
        if self.image is None:
            self.file_label.setText("请先选择一张人脸照片")
            return
        self.status.setText("正在搜索，请稍候...")
        if self._vm.start_image_search(self.image):
            self.accept()
        else:
            self.status.setText("无法发起搜索")

    def _show_status(self, message: str) -> None:
        self.status.setText(message)

    def _show_error(self, message: str) -> None:
        self.status.setText(f"搜索失败：{message}")


class PhotoPreviewDialog(QDialog):
    """Show a matched photo with fit-to-window and zoom controls."""

    def __init__(
        self,
        path: str,
        file_name: str,
        similarity: float,
        captured_at: str | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"照片预览 · {file_name}")
        self.resize(980, 760)
        self._zoom = 1.0
        self._fit_mode = True

        image = read_image(path)
        self._original_pixmap = _frame_to_pixmap(
            image, image.shape[1], image.shape[0]
        ) if image is not None else QPixmap()

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self.preview.setStyleSheet("background: #172a3a;")
        if image is None:
            self.preview.setText("照片无法读取")
            self.preview.setStyleSheet(
                "background: #172a3a; color: white; border-radius: 6px;"
            )

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.preview)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet(
            "QScrollArea { background: #172a3a; border: none; border-radius: 6px; }"
        )

        zoom_out = QPushButton("−")
        zoom_out.setToolTip("缩小照片")
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("放大照片")
        fit = QPushButton("适应窗口")
        fit.setToolTip("让照片完整显示在窗口内")
        self.zoom_label = QLabel("适应窗口")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setMinimumWidth(70)
        zoom_out.clicked.connect(lambda: self._change_zoom(-0.1))
        zoom_in.clicked.connect(lambda: self._change_zoom(0.1))
        fit.clicked.connect(self._fit_to_window)

        controls = QHBoxLayout()
        controls.addStretch(1)
        controls.addWidget(zoom_out)
        controls.addWidget(self.zoom_label)
        controls.addWidget(zoom_in)
        controls.addWidget(fit)
        controls.addStretch(1)

        info = QLabel(
            f"{file_name}    相似度 {similarity * 100:.1f}%    "
            f"拍摄时间 {captured_at or '-'}"
        )
        info.setStyleSheet("font-weight: 700; padding: 4px 0;")

        path_edit = QLineEdit(path)
        path_edit.setReadOnly(True)
        copy_path = QPushButton("复制路径")
        copy_path.clicked.connect(lambda: self._copy_path(path_edit.text()))
        path_row = QHBoxLayout()
        path_row.addWidget(path_edit, 1)
        path_row.addWidget(copy_path)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.addWidget(self.scroll, 1)
        layout.addLayout(controls)
        layout.addWidget(info)
        layout.addLayout(path_row)
        layout.addWidget(close)
        self._fit_to_window()

    @staticmethod
    def _copy_path(path: str) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(path)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_mode:
            self._fit_to_window()

    def _fit_to_window(self) -> None:
        if self._original_pixmap.isNull():
            return
        viewport = self.scroll.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        fitted = self._original_pixmap.scaled(
            viewport,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(fitted)
        self.preview.resize(fitted.size())
        self._fit_mode = True
        self._zoom = fitted.width() / self._original_pixmap.width()
        self.zoom_label.setText("适应窗口")

    def _change_zoom(self, delta: float) -> None:
        if self._original_pixmap.isNull():
            return
        if self._fit_mode:
            self._zoom = max(self._zoom, 0.1)
        self._zoom = min(4.0, max(0.1, self._zoom + delta))
        size = self._original_pixmap.size()
        size.setWidth(max(1, round(size.width() * self._zoom)))
        size.setHeight(max(1, round(size.height() * self._zoom)))
        scaled = self._original_pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)
        self.preview.resize(scaled.size())
        self._fit_mode = False
        self.zoom_label.setText(f"{self._zoom * 100:.0f}%")


def _frame_to_pixmap(frame: np.ndarray, max_w: int, max_h: int) -> QPixmap:
    """Convert a BGR numpy frame to a scaled QPixmap."""
    from PyQt6.QtGui import QImage

    rgb = np.ascontiguousarray(frame[:, :, ::-1])
    height, width, channels = rgb.shape
    image = QImage(
        rgb.data,
        width,
        height,
        channels * width,
        QImage.Format.Format_RGB888,
    ).copy()
    return QPixmap.fromImage(image).scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
