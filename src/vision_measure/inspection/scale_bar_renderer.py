from __future__ import annotations

from typing import cast

import cv2
import numpy as np

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Calibration
from vision_measure.inspection.scale_bar import (
    ScaleBarBackground,
    ScaleBarLabelPosition,
    ScaleBarOrientation,
    ScaleBarShape,
    ScaleBarStyle,
    build_scale_bar_layout,
)


def _color_bgr(value: str) -> tuple[int, int, int]:
    return (int(value[5:7], 16), int(value[3:5], 16), int(value[1:3], 16))


def _rounded_rect_mask(
    height: int,
    width: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    radius = max(0, min(radius, (right - left) // 2, (bottom - top) // 2))
    if radius == 0:
        cv2.rectangle(mask, (left, top), (right, bottom), 255, -1)
        return mask
    cv2.rectangle(
        mask,
        (left + radius, top),
        (right - radius, bottom),
        255,
        -1,
    )
    cv2.rectangle(
        mask,
        (left, top + radius),
        (right, bottom - radius),
        255,
        -1,
    )
    for center in (
        (left + radius, top + radius),
        (right - radius, top + radius),
        (left + radius, bottom - radius),
        (right - radius, bottom - radius),
    ):
        cv2.circle(mask, center, radius, 255, -1)
    return mask


def _composite_mask(
    image: np.ndarray,
    color: tuple[int, int, int],
    mask: np.ndarray,
    opacity: float,
) -> np.ndarray:
    alpha = (mask.astype(np.float32) / 255.0 * opacity)[:, :, np.newaxis]
    color_array = np.asarray(color, dtype=np.float32).reshape(1, 1, 3)
    result = image.astype(np.float32) * (1.0 - alpha) + color_array * alpha
    return cast(np.ndarray, np.clip(result, 0, 255).astype(np.uint8))


def render_scale_bar(
    image: np.ndarray,
    calibration: Calibration,
    length: float,
    position: NormalizedPoint,
    style: ScaleBarStyle,
) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
        raise ValueError("image must be a non-empty HxWx3 BGR image")
    height, width = image.shape[:2]
    layout = build_scale_bar_layout(
        width,
        height,
        calibration,
        length,
        position,
        style,
    )
    geometry = layout.geometry
    start = (round(geometry.start.x), round(geometry.start.y))
    end = (round(geometry.end.x), round(geometry.end.y))
    vertical = style.orientation is ScaleBarOrientation.VERTICAL
    line_width = max(1, round(style.line_width))
    tick = max(0, round(style.tick_length))
    label_scale = style.label_size / 30.0
    label_thickness = max(1, round(style.label_size / 16.0))
    (label_width, label_height), baseline = cv2.getTextSize(
        geometry.label,
        cv2.FONT_HERSHEY_SIMPLEX,
        label_scale,
        label_thickness,
    )
    if vertical:
        label_x = start[0] + max(8, line_width * 2)
        if style.label_position is ScaleBarLabelPosition.ABOVE:
            label_y = max(label_height + 8, start[1] - 8)
        else:
            label_y = min(height - baseline - 8, end[1] + label_height + 8)
    else:
        label_x = start[0]
        if style.label_position is ScaleBarLabelPosition.ABOVE:
            label_y = max(label_height + 8, start[1] - tick - 8)
        else:
            label_y = min(height - baseline - 8, start[1] + tick + label_height + 8)

    left = min(start[0], end[0]) - tick - line_width
    right = max(start[0], end[0]) + tick + line_width
    top = min(start[1], end[1]) - tick - line_width
    bottom = max(start[1], end[1]) + tick + line_width
    if style.show_label:
        left = min(left, label_x)
        right = max(right, label_x + label_width)
        top = min(top, label_y - label_height - baseline)
        bottom = max(bottom, label_y)
    padding = max(4, round(style.line_width * 1.5))
    background_bounds = (
        max(0, left - padding),
        max(0, top - padding),
        min(width - 1, right + padding),
        min(height - 1, bottom + padding),
    )

    base = image.copy()
    if style.background is not ScaleBarBackground.NONE:
        bounds = background_bounds
        mask = _rounded_rect_mask(
            height,
            width,
            bounds[0],
            bounds[1],
            bounds[2],
            bounds[3],
            max(4, round(style.line_width * 2)),
        )
        opacity = 1.0 if style.background is ScaleBarBackground.SOLID else style.background_opacity
        base = _composite_mask(
            base,
            _color_bgr(style.background_color),
            mask,
            opacity,
        )

    rendered = base.copy()
    line_color = _color_bgr(style.line_color)
    outline_color = _color_bgr(style.outline_color)
    segment_length = geometry.pixel_length / style.segments
    if style.shape is ScaleBarShape.SEGMENTED:
        block_width = max(2, line_width * 2)
        for index in range(style.segments):
            segment_start = index * segment_length
            segment_end = (index + 1) * segment_length
            color = line_color if index % 2 == 0 else outline_color
            if vertical:
                top_left = (
                    start[0] - block_width // 2,
                    round(start[1] + segment_start),
                )
                bottom_right = (
                    start[0] + block_width // 2,
                    round(start[1] + segment_end),
                )
            else:
                top_left = (
                    round(start[0] + segment_start),
                    start[1] - block_width // 2,
                )
                bottom_right = (
                    round(start[0] + segment_end),
                    start[1] + block_width // 2,
                )
            cv2.rectangle(rendered, top_left, bottom_right, color, -1, cv2.LINE_AA)
    else:
        if style.show_outline:
            cv2.line(
                rendered,
                start,
                end,
                outline_color,
                line_width + 4,
                cv2.LINE_AA,
            )
        cv2.line(rendered, start, end, line_color, line_width, cv2.LINE_AA)
        if style.shape is ScaleBarShape.TICKS:
            if vertical:
                for x, y in (start, end):
                    cv2.line(
                        rendered,
                        (x - tick, y),
                        (x + tick, y),
                        outline_color if style.show_outline else line_color,
                        line_width + (4 if style.show_outline else 0),
                        cv2.LINE_AA,
                    )
                    cv2.line(
                        rendered, (x - tick, y), (x + tick, y), line_color, line_width, cv2.LINE_AA
                    )
            else:
                for x, y in (start, end):
                    if style.show_outline:
                        cv2.line(
                            rendered,
                            (x, y - tick),
                            (x, y + tick),
                            outline_color,
                            line_width + 4,
                            cv2.LINE_AA,
                        )
                    cv2.line(
                        rendered,
                        (x, y - tick),
                        (x, y + tick),
                        line_color,
                        line_width,
                        cv2.LINE_AA,
                    )
        elif style.shape is ScaleBarShape.BRACKET:
            if vertical:
                points = (
                    ((start[0], start[1]), (start[0] + tick, start[1])),
                    ((end[0], end[1]), (end[0] + tick, end[1])),
                )
            else:
                points = (
                    ((start[0], start[1]), (start[0], start[1] + tick)),
                    ((end[0], end[1]), (end[0], end[1] + tick)),
                )
            for first, second in points:
                cv2.line(rendered, first, second, line_color, line_width, cv2.LINE_AA)
    if style.show_label:
        for color, thickness in (
            (outline_color, label_thickness + 2),
            (_color_bgr(style.label_color), label_thickness),
        ):
            cv2.putText(
                rendered,
                geometry.label,
                (label_x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                label_scale,
                color,
                thickness,
                cv2.LINE_AA,
            )
    return cv2.addWeighted(
        base,
        1.0 - style.opacity,
        rendered,
        style.opacity,
        0,
    )
