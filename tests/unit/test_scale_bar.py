import pytest

from vision_measure.inspection.annotations import (
    ScaleBarTooLong,
    build_scale_bar,
    build_scale_bar_fixed,
)
from vision_measure.inspection.models import Calibration, Unit


def test_fixed_length_geometry_matches_unit_to_pixels() -> None:
    calibration = Calibration(units_per_pixel=0.1, unit=Unit.MM)
    geometry = build_scale_bar_fixed(2000, 1000, calibration, length=10.0)
    assert geometry.pixel_length == pytest.approx(100.0)
    assert geometry.label == "10 mm"


def test_fixed_length_too_large_is_rejected() -> None:
    calibration = Calibration(units_per_pixel=0.1, unit=Unit.MM)
    with pytest.raises(ScaleBarTooLong):
        build_scale_bar_fixed(500, 1000, calibration, length=100.0)


def test_auto_scale_bar_reports_pixel_length() -> None:
    calibration = Calibration(units_per_pixel=0.1, unit=Unit.MM)
    geometry = build_scale_bar(2000, 1000, calibration)
    assert geometry.pixel_length == pytest.approx(geometry.end.x - geometry.start.x)
