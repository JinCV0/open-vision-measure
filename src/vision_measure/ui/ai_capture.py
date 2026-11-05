from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vision_measure.subject_extraction import SubjectExtractor
from vision_measure.subject_extraction.rembg_extractor import RemBgExtractor
from vision_measure.ui.panels import ImagePanel
from vision_measure.ui.screenshot_flow import choose_capture_path
from vision_measure.workspace.controller import Workspace
from vision_measure.workspace.models import SubjectCaptureResult
from vision_measure.workspace.preferences import AppPreferences


class _FailingExtractor:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def extract(self, image: np.ndarray) -> np.ndarray:
        del image
        raise RuntimeError(self._reason)


class AiCaptureThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        workspace: Workspace,
        image: np.ndarray | None = None,
        extractor_factory: Callable[[], SubjectExtractor] | None = None,
    ) -> None:
        super().__init__()
        self._workspace = workspace
        self._image = image
        self._extractor_factory = extractor_factory or RemBgExtractor

    def run(self) -> None:
        try:
            extractor = self._extractor_factory()
        except Exception as exc:
            extractor = _FailingExtractor(str(exc) or exc.__class__.__name__)
        try:
            result = self._workspace.prepare_subject_capture(extractor, self._image)
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.completed.emit(result)


class AiScreenshotDialog(QDialog):
    def __init__(
        self,
        result: SubjectCaptureResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI screenshot")
        self.selected_source: str | None = None
        root = QVBoxLayout(self)
        previews = QHBoxLayout()
        mask = (
            np.zeros(result.original.shape[:2], dtype=np.uint8)
            if result.mask is None
            else result.mask
        )
        for title, image in (
            ("Original", result.original),
            ("Mask", mask),
            ("Cleaned", result.composite),
        ):
            preview = QVBoxLayout()
            preview.addWidget(QLabel(title))
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumSize(260, 200)
            image_label.setPixmap(self._pixmap(image))
            preview.addWidget(image_label, 1)
            previews.addLayout(preview, 1)
        root.addLayout(previews, 1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.save_original_button = QPushButton("Save original")
        self.save_cleaned_button = QPushButton("Save cleaned")
        self.save_cleaned_button.setEnabled(result.mask is not None)
        actions.addWidget(self.save_original_button)
        actions.addWidget(self.save_cleaned_button)
        root.addLayout(actions)
        self.save_original_button.clicked.connect(lambda: self._select("original"))
        self.save_cleaned_button.clicked.connect(lambda: self._select("cleaned"))

    def _select(self, source: str) -> None:
        self.selected_source = source
        self.accept()

    @staticmethod
    def _pixmap(image: np.ndarray) -> QPixmap:
        if image.ndim == 2:
            rgb = np.repeat(image[:, :, np.newaxis], 3, axis=2)
        else:
            rgb = image[:, :, ::-1]
        rgb = np.ascontiguousarray(rgb)
        height, width = rgb.shape[:2]
        qimage = QImage(
            rgb.data,
            width,
            height,
            int(rgb.strides[0]),
            QImage.Format.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(qimage).scaled(
            320,
            240,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )


class AiScreenshotController(QObject):
    def __init__(
        self,
        workspace: Workspace,
        image_panel: ImagePanel,
        parent: QWidget,
        preferences: Callable[[], AppPreferences],
        set_preferences: Callable[[AppPreferences], None],
        show_error: Callable[[str], None],
        set_status: Callable[[str], None],
    ) -> None:
        super().__init__()
        self._workspace = workspace
        self._image_panel = image_panel
        self._parent = parent
        self._preferences = preferences
        self._set_preferences = set_preferences
        self._show_error = show_error
        self._set_status = set_status
        self._thread: AiCaptureThread | None = None
        image_panel.ai_screenshot_requested.connect(self.start)

    def start(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        frame = self._workspace.display_frame
        if frame is None:
            self._show_error("No frame is available")
            return
        self._image_panel.ai_screenshot_button.setEnabled(False)
        self._thread = AiCaptureThread(self._workspace, frame.copy())
        self._thread.completed.connect(self._show_preview)
        self._thread.failed.connect(self._show_error)
        self._thread.finished.connect(self._finished)
        self._thread.start()

    def _finished(self) -> None:
        self._image_panel.ai_screenshot_button.setEnabled(True)
        self._thread = None

    def _show_preview(self, result: object) -> None:
        if not isinstance(result, SubjectCaptureResult):
            return
        dialog = AiScreenshotDialog(result, self._parent)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        if dialog.selected_source not in {"original", "cleaned"}:
            return
        source: Literal["original", "cleaned"] = (
            "original" if dialog.selected_source == "original" else "cleaned"
        )
        selected = choose_capture_path(self._parent, self._preferences())
        if selected is None:
            return
        path, updated = selected
        try:
            self._workspace.save_subject_capture(
                result,
                path,
                source,
                scale_bar_enabled=(
                    updated.scale_bar_enabled and self._workspace.current_calibration is not None
                ),
                scale_bar_position=updated.scale_bar_position,
                scale_bar_length=self._workspace.current_scale_bar_length,
            )
            self._set_preferences(updated)
            self._set_status(f"Saved {path}")
        except Exception as exc:
            self._show_error(str(exc))
