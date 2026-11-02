from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from vision_measure.ui.main_window import MainWindow


def is_smoke_test(arguments: Sequence[str]) -> bool:
    return "--smoke-test" in arguments


def main(arguments: Sequence[str] | None = None) -> int:
    cli_arguments = list(sys.argv if arguments is None else arguments)
    app = QApplication(cli_arguments)
    app.setApplicationName("Open Vision Measure")
    window = MainWindow()
    if is_smoke_test(cli_arguments):
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
