"""SnapByFace 桌面程序入口。

用法:
    python -m app.main
"""
from __future__ import annotations

import sys

from core.logger import get_logger


def main() -> int:
    logger = get_logger()
    try:
        from PyQt6.QtWidgets import QApplication

        from app.application import Application
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("SnapByFace")
        app.setOrganizationName("SnapByFace")

        application = Application()
        application.report_startup_telemetry()
        application.start_background()

        window = MainWindow(application)
        window.show()

        exit_code = app.exec()
        application.shutdown()
        return exit_code
    except Exception:
        logger.exception("程序启动失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
