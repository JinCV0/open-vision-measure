from __future__ import annotations

import importlib
import os
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import QApplication

from vision_measure.ui.main_window import MainWindow
from vision_measure.ui.theme import MaterialThemeManager


def is_smoke_test(arguments: Sequence[str]) -> bool:
    return "--smoke-test" in arguments


def is_ai_smoke_test(arguments: Sequence[str]) -> bool:
    return "--ai-smoke-test" in arguments


def is_ai_model_smoke_test(arguments: Sequence[str]) -> bool:
    return "--ai-model-smoke-test" in arguments


def _write_ai_smoke_log() -> None:
    log_path = os.environ.get("OVM_AI_SMOKE_LOG")
    if log_path:
        Path(log_path).write_text(traceback.format_exc(), encoding="utf-8")


def _can_import_ai_runtime() -> bool:
    try:
        importlib.import_module("rembg")
        importlib.import_module("onnxruntime")
    except Exception:
        _write_ai_smoke_log()
        return False
    return True


def _can_run_ai_model() -> bool:
    try:
        import numpy as np

        from vision_measure.subject_extraction.rembg_extractor import RemBgExtractor

        image = np.zeros((64, 64, 3), dtype=np.uint8)
        mask = RemBgExtractor().extract(image)
        return mask.shape == image.shape[:2]
    except Exception:
        _write_ai_smoke_log()
        return False


def main(arguments: Sequence[str] | None = None) -> int:
    cli_arguments = list(sys.argv if arguments is None else arguments)
    if is_ai_smoke_test(cli_arguments):
        return 0 if _can_import_ai_runtime() else 1
    if is_ai_model_smoke_test(cli_arguments):
        return 0 if _can_run_ai_model() else 1
    app = QApplication(cli_arguments)
    app.setApplicationName("Open Vision Measure")
    MaterialThemeManager(app)
    window = MainWindow()
    if is_smoke_test(cli_arguments):
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
