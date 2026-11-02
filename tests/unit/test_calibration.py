import math

import pytest

from vision_measure.inspection.calibration import (
    InvalidCalibration,
    InvalidMeasurement,
    measure_line,
)
from vision_measure.inspection.models import Calibration, Line, Point, Unit


def test_calibrates_pixels_to_millimetres() -> None:
    calibration = Calibration.from_reference(
        Line(Point(0, 0), Point(100, 0)), physical_length=10.0, unit=Unit.MM
    )
    assert calibration.pixels_to_unit(250.0) == pytest.approx(25.0)
    assert calibration.unit_to_pixels(25.0) == pytest.approx(250.0)


def test_measures_line_in_pixels_and_physical_units() -> None:
    calibration = Calibration.from_reference(
        Line(Point(0, 0), Point(50, 0)), physical_length=5.0, unit=Unit.MM
    )
    result = measure_line(Line(Point(3, 4), Point(6, 8)), calibration)
    assert result.pixel_length == pytest.approx(5.0)
    assert result.physical_length == pytest.approx(0.5)
    assert result.unit is Unit.MM


def test_rejects_zero_length_reference() -> None:
    with pytest.raises(InvalidCalibration):
        Calibration.from_reference(
            Line(Point(1, 1), Point(1, 1)), physical_length=2.0, unit=Unit.MM
        )


def test_rejects_non_finite_measurement() -> None:
    calibration = Calibration.from_reference(
        Line(Point(0, 0), Point(10, 0)), physical_length=1.0, unit=Unit.MM
    )
    with pytest.raises(InvalidMeasurement):
        measure_line(Line(Point(0, 0), Point(math.inf, 0)), calibration)
