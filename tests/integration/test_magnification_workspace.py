import pytest

from vision_measure.inspection.models import Calibration, Line, Point, Unit
from vision_measure.workspace.controller import Workspace


def test_switching_magnification_switches_calibration() -> None:
    workspace = Workspace()
    workspace.set_magnification("4x")
    workspace.set_calibration("4x", Calibration(0.2, Unit.MM))
    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))

    workspace.set_magnification("4x")
    assert workspace.current_calibration is not None
    assert workspace.current_calibration.units_per_pixel == pytest.approx(0.2)
    workspace.set_magnification("10x")
    assert workspace.current_calibration is not None
    assert workspace.current_calibration.units_per_pixel == pytest.approx(0.05)


def test_records_keep_source_magnification() -> None:
    workspace = Workspace()
    workspace.set_magnification("4x")
    workspace.set_calibration("4x", Calibration(0.2, Unit.MM))
    workspace.add_line(Line(Point(0, 0), Point(10, 0)))

    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))
    workspace.add_line(Line(Point(0, 0), Point(20, 0)))

    assert workspace.records[0].magnification == "4x"
    assert workspace.records[1].magnification == "10x"
    assert workspace.measurements[0].physical_length == pytest.approx(2.0)
    assert workspace.measurements[1].physical_length == pytest.approx(1.0)


def test_scale_bar_length_is_stored_per_magnification() -> None:
    workspace = Workspace()
    workspace.set_magnification("4x")
    workspace.set_scale_bar_length(10.0)
    workspace.set_magnification("10x")
    workspace.set_scale_bar_length(2.0)

    assert workspace.current_scale_bar_length == pytest.approx(2.0)
    workspace.set_magnification("4x")
    assert workspace.current_scale_bar_length == pytest.approx(10.0)
