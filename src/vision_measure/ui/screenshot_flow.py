from __future__ import annotations

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
            "Save screenshot",
            str(suggested),
            "Images (*.png *.jpg *.jpeg)",
        )
        if not selected:
            return None
        selected_path = Path(selected)
        if not selected_path.suffix:
            selected_path = selected_path.with_suffix(".png")
        updated = AppPreferences(
            screenshot_directory=selected_path.parent,
            screenshot_extension=selected_path.suffix or ".png",
            scale_bar_enabled=preferences.scale_bar_enabled,
            scale_bar_position=preferences.scale_bar_position,
        )
        return selected_path, updated
    return (
        next_capture_path(
            preferences.screenshot_directory,
            preferences.screenshot_extension,
        ),
        preferences,
    )
