from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import cast

import cv2
import numpy as np

from vision_measure.inspection.annotations import (
    NormalizedPoint,
    ScaleBarGeometry,
    ScaleBarTooLong,
)
from vision_measure.inspection.models import Calibration, Point


class ScaleBarShape(StrEnum):
    LINE = "line"
    TICKS = "ticks"
    SEGMENTED = "segmented"
    BRACKET = "bracket"


class ScaleBarOrientation(StrEnum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ScaleBarLabelPosition(StrEnum):
    ABOVE = "above"
    BELOW = "below"


class ScaleBarBackground(StrEnum):
    NONE = "none"
    TRANSLUCENT = "translucent"
    SOLID = "solid"


class ScaleBarPreset(StrEnum):
    MINIMAL = "minimal"
    SCIENTIFIC = "scientific"
    SEGMENTED = "segmented"
    MATERIAL = "material"
    COMPACT = "compact"


_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_color(label: str, value: str) -> str:
    if not isinstance(value, str) or _COLOR_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must use #RRGGBB")
    return value.lower()


def _validate_range(label: str, value: float, minimum: float, maximum: float) -> float:
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return float(value)


@dataclass(frozen=True, slots=True)
class ScaleBarStyle:
    shape: ScaleBarShape = ScaleBarShape.TICKS
    orientation: ScaleBarOrientation = ScaleBarOrientation.HORIZONTAL
    label_position: ScaleBarLabelPosition = ScaleBarLabelPosition.ABOVE
    background: ScaleBarBackground = ScaleBarBackground.NONE
    line_color: str = "#ffffff"
    outline_color: str = "#000000"
    label_color: str = "#ffffff"
    background_color: str = "#000000"
    opacity: float = 1.0
    background_opacity: float = 0.72
    line_width: float = 3.0
    tick_length: float = 12.0
    label_size: float = 22.0
    show_outline: bool = True
    show_label: bool = True
    segments: int = 5

    def __post_init__(self) -> None:
        if not isinstance(self.shape, ScaleBarShape):
            raise TypeError("shape must be a ScaleBarShape")
        if not isinstance(self.orientation, ScaleBarOrientation):
            raise TypeError("orientation must be a ScaleBarOrientation")
        if not isinstance(self.label_position, ScaleBarLabelPosition):
            raise TypeError("label_position must be a ScaleBarLabelPosition")
        if not isinstance(self.background, ScaleBarBackground):
            raise TypeError("background must be a ScaleBarBackground")
        for label in ("line_color", "outline_color", "label_color", "background_color"):
            object.__setattr__(
                self,
                label,
                _validate_color(label, getattr(self, label)),
            )
        for label, minimum, maximum in (
            ("opacity", 0.0, 1.0),
            ("background_opacity", 0.0, 1.0),
            ("line_width", 1.0, 20.0),
            ("tick_length", 0.0, 80.0),
            ("label_size", 8.0, 96.0),
        ):
            object.__setattr__(
                self,
                label,
                _validate_range(label, getattr(self, label), minimum, maximum),
            )
        if not isinstance(self.segments, int) or not 2 <= self.segments <= 12:
            raise ValueError("segments must be an integer between 2 and 12")


DEFAULT_SCALE_BAR_STYLE = ScaleBarStyle()


@dataclass(frozen=True, slots=True)
class ScaleBarLayout:
    geometry: ScaleBarGeometry
    style: ScaleBarStyle


def scale_bar_preset(preset: ScaleBarPreset) -> ScaleBarStyle:
    presets = {
        ScaleBarPreset.MINIMAL: ScaleBarStyle(
            shape=ScaleBarShape.LINE,
            show_outline=False,
            line_width=2.0,
            tick_length=0.0,
            label_size=18.0,
        ),
        ScaleBarPreset.SCIENTIFIC: DEFAULT_SCALE_BAR_STYLE,
        ScaleBarPreset.SEGMENTED: ScaleBarStyle(
            shape=ScaleBarShape.SEGMENTED,
            line_width=8.0,
            tick_length=0.0,
            label_size=20.0,
            segments=5,
        ),
        ScaleBarPreset.MATERIAL: ScaleBarStyle(
            shape=ScaleBarShape.BRACKET,
            label_position=ScaleBarLabelPosition.BELOW,
            background=ScaleBarBackground.SOLID,
            line_color="#356b53",
            outline_color="#fffbf5",
            label_color="#356b53",
            background_color="#fffbf5",
            line_width=4.0,
            tick_length=12.0,
            label_size=20.0,
        ),
        ScaleBarPreset.COMPACT: ScaleBarStyle(
            shape=ScaleBarShape.BRACKET,
            label_position=ScaleBarLabelPosition.BELOW,
            background=ScaleBarBackground.TRANSLUCENT,
            background_opacity=0.55,
            line_width=2.0,
            tick_length=8.0,
            label_size=16.0,
        ),
    }
    try:
        return presets[preset]
    except KeyError as exc:
        raise ValueError(f"unknown scale bar preset: {preset}") from exc


def scale_bar_style_to_json(style: ScaleBarStyle) -> dict[str, object]:
    result = asdict(style)
    for field in ("shape", "orientation", "label_position", "background"):
        result[field] = getattr(style, field).value
    return result


def scale_bar_style_from_json(raw: object) -> ScaleBarStyle:
    if raw is None:
        return DEFAULT_SCALE_BAR_STYLE
    if not isinstance(raw, dict):
        raise ValueError("scale bar style must be an object")
    try:
        return ScaleBarStyle(
            shape=ScaleBarShape(str(raw.get("shape", DEFAULT_SCALE_BAR_STYLE.shape.value))),
            orientation=ScaleBarOrientation(
                str(raw.get("orientation", DEFAULT_SCALE_BAR_STYLE.orientation.value))
            ),
            label_position=ScaleBarLabelPosition(
                str(
                    raw.get(
                        "label_position",
                        DEFAULT_SCALE_BAR_STYLE.label_position.value,
                    )
                )
            ),
            background=ScaleBarBackground(
                str(raw.get("background", DEFAULT_SCALE_BAR_STYLE.background.value))
            ),
            line_color=str(raw.get("line_color", DEFAULT_SCALE_BAR_STYLE.line_color)),
            outline_color=str(raw.get("outline_color", DEFAULT_SCALE_BAR_STYLE.outline_color)),
            label_color=str(raw.get("label_color", DEFAULT_SCALE_BAR_STYLE.label_color)),
            background_color=str(
                raw.get(
                    "background_color",
                    DEFAULT_SCALE_BAR_STYLE.background_color,
                )
            ),
            opacity=float(raw.get("opacity", DEFAULT_SCALE_BAR_STYLE.opacity)),
            background_opacity=float(
                raw.get(
                    "background_opacity",
                    DEFAULT_SCALE_BAR_STYLE.background_opacity,
                )
            ),
            line_width=float(raw.get("line_width", DEFAULT_SCALE_BAR_STYLE.line_width)),
            tick_length=float(raw.get("tick_length", DEFAULT_SCALE_BAR_STYLE.tick_length)),
            label_size=float(raw.get("label_size", DEFAULT_SCALE_BAR_STYLE.label_size)),
            show_outline=bool(raw.get("show_outline", DEFAULT_SCALE_BAR_STYLE.show_outline)),
            show_label=bool(raw.get("show_label", DEFAULT_SCALE_BAR_STYLE.show_label)),
            segments=int(raw.get("segments", DEFAULT_SCALE_BAR_STYLE.segments)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid scale bar style") from exc


def build_scale_bar_layout(
    image_width: int,
    image_height: int,
    calibration: Calibration,
    length: float,
    position: NormalizedPoint,
    style: ScaleBarStyle,
) -> ScaleBarLayout:
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image dimensions must be positive")
    if not math.isfinite(length) or length <= 0:
        raise ValueError("fixed scale bar length must be finite and positive")
    bar_pixels = calibration.unit_to_pixels(length)
    margin = max(8, round(min(image_width, image_height) * 0.01))
    if style.orientation is ScaleBarOrientation.HORIZONTAL:
        if bar_pixels > image_width - 2 * margin:
            raise ScaleBarTooLong("fixed scale bar length does not fit the image")
        x = min(
            max(position.x * image_width, margin),
            image_width - bar_pixels - margin,
        )
        y = min(max(position.y * image_height, margin * 4), image_height - margin)
        start = (x, y)
        end = (x + bar_pixels, y)
    else:
        if bar_pixels > image_height - 2 * margin:
            raise ScaleBarTooLong("fixed scale bar length does not fit the image")
        x = min(max(position.x * image_width, margin), image_width - margin)
        y = min(
            max(position.y * image_height, margin * 4),
            image_height - bar_pixels - margin,
        )
        start = (x, y)
        end = (x, y + bar_pixels)
    geometry = ScaleBarGeometry(
        start=Point(*start),
        end=Point(*end),
        label=f"{length:.4g} {calibration.unit.value}",
        pixel_length=bar_pixels,
        tick_pixels=round(style.tick_length),
    )
    return ScaleBarLayout(geometry, style)


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
