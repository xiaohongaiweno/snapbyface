"""找片页：轻量入口 + 匹配结果预览。"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from services.print_service import PrintService
from ui.theme import COLORS, page_header, panel
from ui.widgets.print_helper import PhotoPrinter
from ui.widgets.search_dialogs import (
    CameraSearchDialog,
    PhotoPreviewDialog,
    UploadSearchDialog,
)
from viewmodels.search_viewmodel import SearchViewModel


class SearchPage(QWidget):
    def __init__(self, application: Any) -> None:
        super().__init__()
        self._app = application
        self._vm = SearchViewModel(
            application.camera_service, application.search_service
        )
        self._print_service = PrintService(application.ctx.db)
        self._results: list[Any] = []

        title, subtitle = page_header("找片", "选择照片来源，查看最相似的拍摄结果")

        upload_button = QPushButton("▧  本地上传找片")
        upload_button.setProperty("primary", True)
        upload_button.clicked.connect(self._open_upload_dialog)

        camera_button = QPushButton("◉  拍照找片")
        camera_button.clicked.connect(self._open_camera_dialog)
        self._entry_buttons = [upload_button, camera_button]

        entry_panel, entry_layout = panel("开始找片")
        entry_row = QHBoxLayout()
        entry_row.setSpacing(10)
        entry_row.addWidget(upload_button)
        entry_row.addWidget(camera_button)
        entry_row.addStretch(1)
        entry_layout.addLayout(entry_row)

        self.result_list = QListWidget()
        self.result_list.setObjectName("results")
        self.result_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.result_list.setIconSize(QSize(170, 126))
        self.result_list.setGridSize(QSize(214, 194))
        self.result_list.setSpacing(8)
        self.result_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.result_list.setWordWrap(True)
        self.result_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.result_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.result_list.itemDoubleClicked.connect(self._preview_result)
        self.result_list.itemActivated.connect(self._preview_result)
        self.result_list.currentItemChanged.connect(
            lambda current, _previous: self._show_result_details(current)
        )

        result_panel, result_layout = panel("匹配照片")
        self.result_hint = QLabel("请选择“本地上传找片”或“拍照找片”开始")
        self.result_hint.setStyleSheet(f"color: {COLORS['muted']};")
        result_layout.addWidget(self.result_hint)
        result_layout.addWidget(self.result_list, 1)

        self.photo_info = QLabel("未选择照片")
        self.photo_info.setStyleSheet("font-weight: 700;")
        self.photo_path = QLineEdit()
        self.photo_path.setReadOnly(True)
        self.photo_path.setPlaceholderText("选中照片后显示文件位置")
        copy_path = QPushButton("复制路径")
        copy_path.setEnabled(False)
        copy_path.clicked.connect(self._copy_selected_path)
        self._copy_path_button = copy_path

        path_row = QHBoxLayout()
        path_row.addWidget(self.photo_path, 1)
        path_row.addWidget(copy_path)
        result_layout.addWidget(self.photo_info)
        result_layout.addLayout(path_row)

        print_button = QPushButton("▣  打印选中照片")
        print_button.clicked.connect(self._on_print)
        print_button.setEnabled(False)
        self._print_button = print_button
        result_layout.addWidget(print_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)
        layout.addWidget(entry_panel)
        layout.addSpacing(12)
        layout.addWidget(result_panel, 1)

        self._vm.results_ready.connect(self._show_results)
        self._vm.search_error.connect(self._show_error)
        self._vm.search_started.connect(self._search_started)
        self._vm.status_message.connect(
            lambda message: self._app.logger.info("UI: %s", message)
        )

        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_upload_dialog)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self._on_print)
        QShortcut(QKeySequence("Return"), self, activated=self._preview_selected)
        self.setFocusProxy(self.result_list)

    def _open_camera_dialog(self) -> None:
        dialog = CameraSearchDialog(self._vm, self)
        dialog.exec()

    def _open_upload_dialog(self) -> None:
        dialog = UploadSearchDialog(self._vm, self)
        dialog.exec()

    def _show_results(self, results: list) -> None:
        self._results = results
        self._set_search_busy(False)
        self.result_list.clear()
        for result in results:
            item = QListWidgetItem(
                f"{result.file_name}\n"
                f"相似度 {result.similarity * 100:.1f}%\n"
                f"{result.captured_at or '-'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, result.photo_id)
            from utils.image import read_image

            image = read_image(result.path)
            if image is not None:
                from ui.widgets.search_dialogs import _frame_to_pixmap

                item.setIcon(QIcon(_frame_to_pixmap(image, 170, 126)))
            self.result_list.addItem(item)
        if results:
            self.result_hint.setText(
                f"找到 {len(results)} 张匹配照片，选择后可复制路径或打印，"
                "双击可查看大图"
            )
        else:
            self.result_hint.setText(
                "未找到匹配照片，请确认索引已完成，或换一张正面、清晰的人脸照片"
            )
        self.result_list.setCurrentRow(0 if results else -1)
        if not results:
            self._show_result_details(None)
        self._app.logger.info("搜索结果 %d 条", len(results))

    def _show_result_details(self, item: QListWidgetItem | None) -> None:
        if item is None:
            self.photo_info.setText("未选择照片")
            self.photo_path.clear()
            self._copy_path_button.setEnabled(False)
            self._print_button.setEnabled(False)
            return
        row = self.result_list.row(item)
        if row < 0 or row >= len(self._results):
            return
        result = self._results[row]
        self.photo_info.setText(
            f"{result.file_name}    相似度 {result.similarity * 100:.1f}%    "
            f"拍摄时间 {result.captured_at or '-'}"
        )
        self.photo_path.setText(result.path)
        self._copy_path_button.setEnabled(True)
        self._print_button.setEnabled(True)

    def _copy_selected_path(self) -> None:
        path = self.photo_path.text()
        if path:
            from PyQt6.QtWidgets import QApplication

            QApplication.clipboard().setText(path)
            self._app.logger.info("已复制照片路径: %s", path)

    def _preview_result(self, item: QListWidgetItem) -> None:
        row = self.result_list.row(item)
        if row < 0 or row >= len(self._results):
            return
        result = self._results[row]
        PhotoPreviewDialog(
            result.path,
            result.file_name,
            result.similarity,
            result.captured_at,
            self,
        ).exec()

    def _show_error(self, message: str) -> None:
        self._set_search_busy(False)
        self.result_list.clear()
        self._results = []
        self.result_hint.setText(f"搜索失败：{message}")
        self._show_result_details(None)
        QMessageBox.warning(self, "搜索", message)

    def _search_started(self) -> None:
        self._set_search_busy(True)
        self.result_list.clear()
        self._results = []
        self._show_result_details(None)
        self.result_hint.setText("正在搜索，请稍候...")

    def _set_search_busy(self, busy: bool) -> None:
        for button in self._entry_buttons:
            button.setEnabled(not busy)
        self._print_button.setEnabled(
            not busy and self.result_list.currentRow() >= 0
        )

    def _preview_selected(self) -> None:
        item = self.result_list.currentItem()
        if item is not None:
            self._preview_result(item)

    def _on_print(self) -> None:
        row = self.result_list.currentRow()
        if row < 0 or row >= len(self._results):
            QMessageBox.information(self, "打印", "请先选择一张照片")
            return
        result = self._results[row]
        if not PhotoPrinter().print_image(result.path, parent=self):
            return
        ok = self._print_service.print_photo(result.photo_id, result.similarity)
        QMessageBox.information(
            self,
            "打印",
            "打印成功，已记录" if ok else "打印成功，但记录写入失败",
        )
