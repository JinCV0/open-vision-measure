from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from vision_measure.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Open Vision Measure")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
