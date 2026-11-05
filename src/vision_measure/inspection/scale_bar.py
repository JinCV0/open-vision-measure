from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from enum import StrEnum


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
            outline_color=str(
                raw.get("outline_color", DEFAULT_SCALE_BAR_STYLE.outline_color)
            ),
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
            line_width=float(
                raw.get("line_width", DEFAULT_SCALE_BAR_STYLE.line_width)
            ),
            tick_length=float(
                raw.get("tick_length", DEFAULT_SCALE_BAR_STYLE.tick_length)
            ),
            label_size=float(
                raw.get("label_size", DEFAULT_SCALE_BAR_STYLE.label_size)
            ),
            show_outline=bool(
                raw.get("show_outline", DEFAULT_SCALE_BAR_STYLE.show_outline)
            ),
            show_label=bool(
                raw.get("show_label", DEFAULT_SCALE_BAR_STYLE.show_label)
            ),
            segments=int(raw.get("segments", DEFAULT_SCALE_BAR_STYLE.segments)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid scale bar style") from exc
