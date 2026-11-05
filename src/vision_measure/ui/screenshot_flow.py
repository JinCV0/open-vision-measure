from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QWidget

from vision_measure.workspace.preferences import AppPreferences
from vision_measure.workspace.screenshot import next_capture_path


def choose_capture_path(
    parent: QWidget,
    preferences: AppPreferences,
) -> tuple[Path, AppPreferences] | None:
    if preferences.screenshot_directory is None:
        pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        suggested = Path(pictures) / "OpenVisionMeasure" / "capture_0001.png"
        selected, _ = QFileDialog.getSaveFileName(
            parent,
            "保存截图",
            str(suggested),
            "图片 (*.png *.jpg *.jpeg)",
        )
        if not selected:
            return None
        selected_path = Path(selected)
        if not selected_path.suffix:
            selected_path = selected_path.with_suffix(".png")
        updated = replace(
            preferences,
            screenshot_directory=selected_path.parent,
            screenshot_extension=selected_path.suffix or ".png",
        )
        return selected_path, updated
    return (
        next_capture_path(
            preferences.screenshot_directory,
            preferences.screenshot_extension,
        ),
        preferences,
    )
