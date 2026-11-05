from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from vision_measure.inspection.scale_bar import (
    ScaleBarBackground,
    ScaleBarLabelPosition,
    ScaleBarOrientation,
    ScaleBarShape,
    ScaleBarStyle,
)


@dataclass(frozen=True, slots=True)
class CanvasScaleBarLayout:
    start: QPointF
    end: QPointF
    label_origin: QPointF
    label_rect: QRectF
    bounds: QRectF
    font: QFont
    line_width: float
    tick: float
    label: str


def layout_canvas_scale_bar(
    start: QPointF,
    end: QPointF,
    label: str,
    style: ScaleBarStyle,
    image_scale: float,
    viewport_height: int,
    base_font: QFont,
) -> CanvasScaleBarLayout:
    tick = style.tick_length * image_scale
    line_width = max(1.0, style.line_width * image_scale)
    vertical = style.orientation is ScaleBarOrientation.VERTICAL
    font = QFont(base_font)
    font.setPixelSize(max(8, round(style.label_size * image_scale)))
    metrics = QFontMetricsF(font)
    label_width = metrics.horizontalAdvance(label) if style.show_label else 0.0
    label_height = metrics.height()
    if vertical:
        label_x = start.x() + max(8.0, line_width * 2)
        label_y = (
            max(label_height, start.y() - 8.0)
            if style.label_position is ScaleBarLabelPosition.ABOVE
            else min(viewport_height - 8.0, end.y() + label_height + 8.0)
        )
    else:
        label_x = start.x()
        label_y = (
            max(label_height, start.y() - tick - 8.0)
            if style.label_position is ScaleBarLabelPosition.ABOVE
            else min(viewport_height - 8.0, start.y() + tick + label_height + 8.0)
        )

    left = min(start.x(), end.x()) - tick - line_width
    right = max(start.x(), end.x()) + tick + line_width
    top = min(start.y(), end.y()) - tick - line_width
    bottom = max(start.y(), end.y()) + tick + line_width
    if style.show_label:
        left = min(left, label_x)
        right = max(right, label_x + label_width)
        top = min(top, label_y - label_height)
        bottom = max(bottom, label_y)
    padding = max(4.0, line_width * 2)
    bounds = QRectF(
        left - padding,
        top - padding,
        right - left + padding * 2,
        bottom - top + padding * 2,
    )
    return CanvasScaleBarLayout(
        start=start,
        end=end,
        label_origin=QPointF(label_x, label_y),
        label_rect=QRectF(label_x, label_y - label_height, label_width, label_height),
        bounds=bounds,
        font=font,
        line_width=line_width,
        tick=tick,
        label=label,
    )


def paint_canvas_scale_bar(
    painter: QPainter,
    layout: CanvasScaleBarLayout,
    style: ScaleBarStyle,
) -> None:
    line_color = _style_color(style.line_color, style.opacity)
    outline_color = _style_color(style.outline_color, style.opacity)
    label_color = _style_color(style.label_color, style.opacity)
    vertical = style.orientation is ScaleBarOrientation.VERTICAL

    if style.background is not ScaleBarBackground.NONE:
        background = QColor(style.background_color)
        background_opacity = (
            1.0 if style.background is ScaleBarBackground.SOLID else style.background_opacity
        )
        background.setAlphaF(style.opacity * background_opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        radius = max(4.0, layout.line_width * 2)
        painter.drawRoundedRect(layout.bounds, radius, radius)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    if style.shape is ScaleBarShape.SEGMENTED:
        segment_length = (
            (layout.end.x() - layout.start.x()) ** 2 + (layout.end.y() - layout.start.y()) ** 2
        ) ** 0.5 / style.segments
        block = max(2.0, layout.line_width * 2)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(style.segments):
            segment_start = index * segment_length
            segment_end = (index + 1) * segment_length
            painter.setBrush(line_color if index % 2 == 0 else outline_color)
            if vertical:
                rect = QRectF(
                    layout.start.x() - block / 2,
                    layout.start.y() + segment_start,
                    block,
                    segment_end - segment_start,
                )
            else:
                rect = QRectF(
                    layout.start.x() + segment_start,
                    layout.start.y() - block / 2,
                    segment_end - segment_start,
                    block,
                )
            painter.drawRect(rect)
    else:
        if style.show_outline:
            painter.setPen(QPen(outline_color, layout.line_width + 4))
            painter.drawLine(layout.start, layout.end)
        painter.setPen(QPen(line_color, layout.line_width))
        painter.drawLine(layout.start, layout.end)
        if style.shape is ScaleBarShape.TICKS:
            for point in (layout.start, layout.end):
                if vertical:
                    first = QPointF(point.x() - layout.tick, point.y())
                    second = QPointF(point.x() + layout.tick, point.y())
                else:
                    first = QPointF(point.x(), point.y() - layout.tick)
                    second = QPointF(point.x(), point.y() + layout.tick)
                if style.show_outline:
                    painter.setPen(QPen(outline_color, layout.line_width + 4))
                    painter.drawLine(first, second)
                painter.setPen(QPen(line_color, layout.line_width))
                painter.drawLine(first, second)
        elif style.shape is ScaleBarShape.BRACKET:
            for point in (layout.start, layout.end):
                second = (
                    QPointF(point.x() + layout.tick, point.y())
                    if vertical
                    else QPointF(point.x(), point.y() + layout.tick)
                )
                painter.setPen(QPen(line_color, layout.line_width))
                painter.drawLine(point, second)

    if style.show_label:
        painter.setFont(layout.font)
        if style.show_outline:
            painter.setPen(QPen(outline_color, max(2.0, layout.line_width)))
            painter.drawText(layout.label_origin, layout.label)
        painter.setPen(QPen(label_color, 1))
        painter.drawText(layout.label_origin, layout.label)


def hit_canvas_scale_bar(layout: CanvasScaleBarLayout, x: float, y: float) -> bool:
    if layout.bounds.adjusted(-8, -8, 8, 8).contains(QPointF(x, y)):
        return True
    dx = layout.end.x() - layout.start.x()
    dy = layout.end.y() - layout.start.y()
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return False
    position = ((x - layout.start.x()) * dx + (y - layout.start.y()) * dy) / length_sq
    position = max(0.0, min(1.0, position))
    nearest_x = layout.start.x() + position * dx
    nearest_y = layout.start.y() + position * dy
    hit_radius = max(18.0, layout.line_width * 2 + 10)
    return (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= hit_radius**2


def _style_color(value: str, opacity: float) -> QColor:
    color = QColor(value)
    color.setAlphaF(opacity)
    return color
