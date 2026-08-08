"""UI 打印组件：调用系统打印对话框实际出纸（规格 §20 打印）。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from utils.image import read_image


class PhotoPrinter:
    """用 QPrinter + QPrintDialog 打印照片。"""

    def print_image(self, path: str, parent: Any | None = None) -> bool:
        """打开系统打印对话框打印图片。

        返回:
            True 表示用户确认打印；False 表示取消或图片无效。
        """
        pix = _image_to_pixmap(read_image(path))
        if pix.isNull():
            return False

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, parent)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        scaled = pix.scaled(
            page_rect.size(),
            aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
            transformMode=Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(printer)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        return True


def _image_to_pixmap(image) -> QPixmap:
    """Convert a BGR OpenCV image into a Qt pixmap."""
    if image is None:
        return QPixmap()
    import numpy as np

    rgb = np.ascontiguousarray(image[:, :, ::-1])
    height, width, channels = rgb.shape
    qimage = QImage(
        rgb.data,
        width,
        height,
        channels * width,
        QImage.Format.Format_RGB888,
    ).copy()
    return QPixmap.fromImage(qimage)
