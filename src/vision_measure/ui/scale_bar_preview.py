from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QWidget

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.inspection.scale_bar import ScaleBarStyle
from vision_measure.inspection.scale_bar_renderer import render_scale_bar
from vision_measure.ui.theme import viewport_background


class ScaleBarPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source = self._sample_frame()
        self._rendered = self._source.copy()
        self._calibration = Calibration(0.1, Unit.MM)
        self._length = 10.0
        self._position = NormalizedPoint(0.04, 0.92)
        self._style: ScaleBarStyle | None = None
        self.setMinimumSize(560, 420)

    def set_state(
        self,
        image: np.ndarray | None,
        calibration: Calibration,
        length: float,
        position: NormalizedPoint,
        style: ScaleBarStyle,
    ) -> None:
        source = self._source
        if image is not None:
            if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
                raise ValueError("preview image must be a non-empty HxWx3 BGR image")
            source = image.copy()
        rendered = render_scale_bar(
            source,
            calibration,
            length,
            position,
            style,
        )
        self._source = source
        self._rendered = rendered
        self._calibration = calibration
        self._length = length
        self._position = position
        self._style = style
        self.update()

    def paintEvent(self, event: object) -> None:
        del event
        painter = QPainter(self)
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        painter.fillRect(self.rect(), QColor(viewport_background(dark)))
        rgb = np.ascontiguousarray(cv2.cvtColor(self._rendered, cv2.COLOR_BGR2RGB))
        height, width = rgb.shape[:2]
        image = QImage(
            rgb.data,
            width,
            height,
            int(rgb.strides[0]),
            QImage.Format.Format_RGB888,
        ).copy()
        target = self._target_rect(image.width(), image.height())
        clip = QPainterPath()
        clip.addRoundedRect(target, 18, 18)
        painter.setClipPath(clip)
        painter.drawImage(target, image)

    def _target_rect(self, image_width: int, image_height: int) -> QRectF:
        scale = min(self.width() / image_width, self.height() / image_height)
        width = image_width * scale
        height = image_height * scale
        return QRectF(
            (self.width() - width) / 2,
            (self.height() - height) / 2,
            width,
            height,
        )

    @staticmethod
    def _sample_frame() -> np.ndarray:
        height, width = 480, 760
        y, x = np.mgrid[0:height, 0:width]
        image = np.full((height, width, 3), (72, 74, 76), dtype=np.uint8)
        center_x = width * 0.52
        center_y = height * 0.5
        subject = ((x - center_x) / (width * 0.32)) ** 2 + (
            (y - center_y) / (height * 0.36)
        ) ** 2 < 1
        image[subject] = (108, 146, 108)
        tissue = ((x - center_x) / (width * 0.18)) ** 2 + (
            (y - center_y) / (height * 0.21)
        ) ** 2 < 1
        image[tissue] = (78, 116, 84)
        return image
