from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class Unit(StrEnum):
    PX = "px"
    MM = "mm"
    CM = "cm"
    UM = "um"
    IN = "in"

    @property
    def display_name(self) -> str:
        return {
            Unit.PX: "像素",
            Unit.MM: "毫米",
            Unit.CM: "厘米",
            Unit.UM: "微米",
            Unit.IN: "英寸",
        }[self]


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Line:
    start: Point
    end: Point


@dataclass(frozen=True, slots=True)
class Calibration:
    units_per_pixel: float
    unit: Unit

    def __post_init__(self) -> None:
        if not isinstance(self.unit, Unit):
            raise TypeError("unit must be a Unit")
        if not math.isfinite(self.units_per_pixel) or self.units_per_pixel <= 0:
            raise ValueError("units_per_pixel must be finite and positive")

    @classmethod
    def from_reference(cls, line: Line, physical_length: float, unit: Unit) -> Calibration:
        from vision_measure.inspection.calibration import (
            InvalidCalibration,
            line_length_pixels,
        )

        try:
            pixel_length = line_length_pixels(line)
        except ValueError as exc:
            raise InvalidCalibration(str(exc)) from exc
        if not math.isfinite(physical_length) or physical_length <= 0 or pixel_length <= 0:
            raise InvalidCalibration(
                "reference length and physical length must be finite and positive"
            )
        return cls(units_per_pixel=physical_length / pixel_length, unit=unit)

    def pixels_to_unit(self, pixels: float) -> float:
        if not math.isfinite(pixels):
            raise ValueError("pixel length must be finite")
        return pixels * self.units_per_pixel

    def unit_to_pixels(self, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("physical length must be finite")
        return value / self.units_per_pixel


@dataclass(frozen=True, slots=True)
class LineMeasurement:
    source: Line
    pixel_length: float
    physical_length: float
    unit: Unit


DEFAULT_MAGNIFICATION_NAME = "default"


@dataclass(frozen=True, slots=True)
class MagnificationProfile:
    name: str
    calibration: Calibration | None = None
    calibrated_at: str | None = None
    reference_length: float | None = None
    scale_bar_length: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("magnification name must not be empty")
        for label, value in (
            ("reference_length", self.reference_length),
            ("scale_bar_length", self.scale_bar_length),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{label} must be finite and positive")
