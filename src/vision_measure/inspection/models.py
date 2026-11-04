from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class Unit(StrEnum):
    PX = "px"
    MM = "mm"
    CM = "cm"
    IN = "in"


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
    def from_reference(
        cls, line: Line, physical_length: float, unit: Unit
    ) -> Calibration:
        from vision_measure.inspection.calibration import (
            InvalidCalibration,
            line_length_pixels,
        )

        try:
            pixel_length = line_length_pixels(line)
        except ValueError as exc:
            raise InvalidCalibration(str(exc)) from exc
        if (
            not math.isfinite(physical_length)
            or physical_length <= 0
            or pixel_length <= 0
        ):
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
