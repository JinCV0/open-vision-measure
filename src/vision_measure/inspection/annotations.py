from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from vision_measure.inspection.models import Calibration, Point


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.x) and math.isfinite(self.y)):
            raise ValueError("normalized position must be finite")
        if not (0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0):
            raise ValueError("normalized position must be between 0 and 1")


DEFAULT_SCALE_BAR_POSITION = NormalizedPoint(0.04, 0.92)


@dataclass(frozen=True, slots=True)
class ScaleBarGeometry:
    start: Point
    end: Point
    label: str
    tick_pixels: int = 12


def _nice_length(maximum: float) -> float:
    if not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("maximum scale length must be finite and positive")
    exponent = math.floor(math.log10(maximum))
    scale = 10.0**exponent
    for multiplier in (5.0, 2.0, 1.0):
        value = multiplier * scale
        if value <= maximum:
            return value
    return scale


def _format_length(value: float, unit: str) -> str:
    return f"{value:.4g} {unit}"


def build_scale_bar(
    image_width: int,
    image_height: int,
    calibration: Calibration,
    position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION,
    target_fraction: float = 0.18,
) -> ScaleBarGeometry:
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image dimensions must be positive")
    if not 0 < target_fraction < 1:
        raise ValueError("target_fraction must be between 0 and 1")
    target_pixels = image_width * target_fraction
    maximum_length = calibration.pixels_to_unit(target_pixels)
    length = _nice_length(maximum_length)
    bar_pixels = calibration.unit_to_pixels(length)
    margin = max(8, round(image_width * 0.01))
    x = min(max(position.x * image_width, margin), image_width - bar_pixels - margin)
    y = min(max(position.y * image_height, margin * 4), image_height - margin)
    return ScaleBarGeometry(
        start=Point(x, y),
        end=Point(x + bar_pixels, y),
        label=_format_length(length, calibration.unit.value),
    )


def draw_scale_bar(
    image: np.ndarray,
    calibration: Calibration,
    position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION,
) -> np.ndarray:
    height, width = image.shape[:2]
    geometry = build_scale_bar(width, height, calibration, position)
    rendered = image.copy()
    start = (round(geometry.start.x), round(geometry.start.y))
    end = (round(geometry.end.x), round(geometry.end.y))
    for color, thickness in (((0, 0, 0), 7), ((255, 255, 255), 3)):
        cv2.line(rendered, start, end, color, thickness, cv2.LINE_AA)
        cv2.line(
            rendered,
            (start[0], start[1] - geometry.tick_pixels),
            (start[0], start[1] + geometry.tick_pixels),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.line(
            rendered,
            (end[0], end[1] - geometry.tick_pixels),
            (end[0], end[1] + geometry.tick_pixels),
            color,
            thickness,
            cv2.LINE_AA,
        )
    text_origin = (start[0], max(24, start[1] - 20))
    for color, thickness in (((0, 0, 0), 3), ((255, 255, 255), 1)):
        cv2.putText(
            rendered,
            geometry.label,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            thickness,
            cv2.LINE_AA,
        )
    return rendered
