from __future__ import annotations

import math

from vision_measure.inspection.models import Calibration, Line, LineMeasurement


class InvalidCalibration(ValueError):
    pass


class InvalidMeasurement(ValueError):
    pass


def line_length_pixels(line: Line) -> float:
    coordinates = (
        line.start.x,
        line.start.y,
        line.end.x,
        line.end.y,
    )
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("line coordinates must be finite")
    return math.hypot(line.end.x - line.start.x, line.end.y - line.start.y)


def measure_line(line: Line, calibration: Calibration) -> LineMeasurement:
    try:
        pixel_length = line_length_pixels(line)
        physical_length = calibration.pixels_to_unit(pixel_length)
    except (TypeError, ValueError) as exc:
        raise InvalidMeasurement(str(exc)) from exc
    return LineMeasurement(
        source=line,
        pixel_length=pixel_length,
        physical_length=physical_length,
        unit=calibration.unit,
    )
