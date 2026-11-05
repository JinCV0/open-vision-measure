from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QWidget

from vision_measure.inspection.annotations import (
    DEFAULT_SCALE_BAR_POSITION,
    NormalizedPoint,
    ScaleBarGeometry,
    ScaleBarTooLong,
)
from vision_measure.inspection.models import Calibration, Line, Point
from vision_measure.inspection.scale_bar import (
    DEFAULT_SCALE_BAR_STYLE,
    ScaleBarStyle,
    build_scale_bar_layout,
)
from vision_measure.ui.scale_bar_painter import (
    hit_canvas_scale_bar,
    layout_canvas_scale_bar,
    paint_canvas_scale_bar,
)
from vision_measure.ui.theme import viewport_background


class ImageViewport(QWidget):
    line_finished = Signal(object)
    measurement_mode_changed = Signal(bool)
    calibration_finished = Signal(object)
    scale_bar_moved = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._lines: tuple[Line, ...] = ()
        self._draw_start: Point | None = None
        self._draw_current: Point | None = None
        self._scale_bar_calibration: Calibration | None = None
        self._scale_bar_length: float | None = None
        self._scale_bar_style = DEFAULT_SCALE_BAR_STYLE
        self._scale_bar_visible = False
        self._scale_bar_position = DEFAULT_SCALE_BAR_POSITION
        self._dragging_scale_bar = False
        self._calibration_mode = False
        self._measurement_mode = False
        self._drag_image_origin: Point | None = None
        self._drag_position_origin = DEFAULT_SCALE_BAR_POSITION
        self.setMinimumSize(480, 320)
        self.setMouseTracking(True)

    def set_frame(self, frame: np.ndarray | None) -> None:
        if frame is None:
            self._image = None
            self.update()
            return
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("frame must be an HxWx3 BGR image")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        height, width = rgb.shape[:2]
        self._image = QImage(
            rgb.data,
            width,
            height,
            int(rgb.strides[0]),
            QImage.Format.Format_RGB888,
        ).copy()
        self.update()

    def set_lines(self, lines: tuple[Line, ...]) -> None:
        self._lines = lines
        self.update()

    @property
    def calibration_mode(self) -> bool:
        return self._calibration_mode

    def set_calibration_mode(self, active: bool) -> None:
        self._calibration_mode = active
        self._draw_start = None
        self._draw_current = None
        self.update()

    @property
    def measurement_mode(self) -> bool:
        return self._measurement_mode

    def set_measurement_mode(self, active: bool) -> None:
        self._measurement_mode = active
        self._draw_start = None
        self._draw_current = None
        self.update()

    @property
    def scale_bar_position(self) -> NormalizedPoint:
        return self._scale_bar_position

    @property
    def scale_bar_style(self) -> ScaleBarStyle:
        return self._scale_bar_style

    def set_scale_bar(
        self,
        calibration: Calibration | None,
        visible: bool,
        position: NormalizedPoint | None = None,
        length: float | None = None,
        style: ScaleBarStyle | None = None,
    ) -> None:
        self._scale_bar_calibration = calibration
        self._scale_bar_length = length
        if style is not None:
            self._scale_bar_style = style
        self._scale_bar_visible = visible and calibration is not None
        if position is not None:
            self._scale_bar_position = position
        self.update()

    def _target_rect(self) -> QRectF:
        if self._image is None:
            return QRectF()
        image_width = self._image.width()
        image_height = self._image.height()
        scale = min(self.width() / image_width, self.height() / image_height)
        width = image_width * scale
        height = image_height * scale
        return QRectF(
            (self.width() - width) / 2,
            (self.height() - height) / 2,
            width,
            height,
        )

    def widget_to_image(self, x: float, y: float) -> tuple[float, float] | None:
        if self._image is None:
            return None
        target = self._target_rect()
        if not target.contains(QPointF(x, y)):
            return None
        scale = target.width() / self._image.width()
        image_x = (x - target.left()) / scale
        image_y = (y - target.top()) / scale
        return (image_x, image_y)

    def _image_to_widget(self, point: Point) -> QPointF:
        target = self._target_rect()
        if self._image is None:
            return QPointF()
        scale = target.width() / self._image.width()
        return QPointF(target.left() + point.x * scale, target.top() + point.y * scale)

    def paintEvent(self, event: object) -> None:
        del event
        painter = QPainter(self)
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 22, 22)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(viewport_background(dark)))
        if self._image is None:
            return
        target = self._target_rect()
        painter.drawImage(target, self._image)
        painter.setPen(QPen(QColor("#ff5d5d"), 2))
        for line in self._lines:
            painter.drawLine(
                self._image_to_widget(line.start),
                self._image_to_widget(line.end),
            )
        self._draw_scale_bar(painter)
        if self._draw_start is not None and self._draw_current is not None:
            painter.setPen(QPen(QColor("#ffd166"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(
                self._image_to_widget(self._draw_start),
                self._image_to_widget(self._draw_current),
            )

    def _draw_scale_bar(self, painter: QPainter) -> None:
        geometry = self._scale_bar_geometry()
        if geometry is None or self._image is None:
            return
        image_scale = self._target_rect().width() / self._image.width()
        start = self._image_to_widget(geometry.start)
        end = self._image_to_widget(geometry.end)
        layout = layout_canvas_scale_bar(
            start,
            end,
            geometry.label,
            self._scale_bar_style,
            image_scale,
            self.height(),
            self.font(),
        )
        paint_canvas_scale_bar(painter, layout, self._scale_bar_style)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.position()
        mapped = self.widget_to_image(position.x(), position.y())
        if mapped is None:
            return
        if not self._calibration_mode and self._hit_scale_bar(position.x(), position.y()):
            self._dragging_scale_bar = True
            self._drag_image_origin = Point(*mapped)
            self._drag_position_origin = self._scale_bar_position
            return
        if not self._calibration_mode and not self._measurement_mode:
            return
        point = Point(*mapped)
        if self._draw_start is None:
            self._draw_start = point
            self._draw_current = point
            self.update()
            return
        line = Line(self._draw_start, point)
        self._draw_start = None
        self._draw_current = None
        self.update()
        if self._calibration_mode:
            self._calibration_mode = False
            self.calibration_finished.emit(line)
        else:
            self._measurement_mode = False
            self.measurement_mode_changed.emit(False)
            self.line_finished.emit(line)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_scale_bar:
            position = event.position()
            mapped = self.widget_to_image(position.x(), position.y())
            if mapped is None or self._image is None or self._drag_image_origin is None:
                return
            x = (
                self._drag_position_origin.x
                + (mapped[0] - self._drag_image_origin.x) / self._image.width()
            )
            y = (
                self._drag_position_origin.y
                + (mapped[1] - self._drag_image_origin.y) / self._image.height()
            )
            self._scale_bar_position = NormalizedPoint(
                min(max(x, 0.0), 1.0),
                min(max(y, 0.0), 1.0),
            )
            self.update()
            return
        if self._draw_start is None:
            return
        position = event.position()
        mapped = self.widget_to_image(position.x(), position.y())
        if mapped is not None:
            self._draw_current = Point(*mapped)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_scale_bar:
            self._dragging_scale_bar = False
            self._drag_image_origin = None
            self.scale_bar_moved.emit(self._scale_bar_position)

    def _hit_scale_bar(self, x: float, y: float) -> bool:
        geometry = self._scale_bar_geometry()
        if geometry is None:
            return False
        start = self._image_to_widget(geometry.start)
        end = self._image_to_widget(geometry.end)
        image_scale = self._target_rect().width() / self._image.width() if self._image else 1.0
        layout = layout_canvas_scale_bar(
            start,
            end,
            geometry.label,
            self._scale_bar_style,
            image_scale,
            self.height(),
            self.font(),
        )
        return hit_canvas_scale_bar(layout, x, y)

    def _scale_bar_geometry(self) -> ScaleBarGeometry | None:
        if (
            not self._scale_bar_visible
            or self._scale_bar_calibration is None
            or self._image is None
            or self._scale_bar_length is None
        ):
            return None
        try:
            return build_scale_bar_layout(
                self._image.width(),
                self._image.height(),
                self._scale_bar_calibration,
                self._scale_bar_length,
                self._scale_bar_position,
                self._scale_bar_style,
            ).geometry
        except ScaleBarTooLong:
            return None
