import numpy as np
import pytest

from vision_measure.inspection.annotations import (
    NormalizedPoint,
    build_scale_bar,
    draw_scale_bar,
)
from vision_measure.inspection.models import Calibration, Unit


def test_scale_bar_defaults_to_lower_left() -> None:
    geometry = build_scale_bar(
        image_width=1000,
        image_height=800,
        calibration=Calibration(0.1, Unit.MM),
    )
    assert geometry.start.x == pytest.approx(40.0)
    assert geometry.start.y == pytest.approx(736.0)
    assert geometry.end.x - geometry.start.x == pytest.approx(100.0)
    assert geometry.label == "10 mm"


def test_scale_bar_uses_requested_normalized_position() -> None:
    geometry = build_scale_bar(
        image_width=1000,
        image_height=800,
        calibration=Calibration(0.1, Unit.MM),
        position=NormalizedPoint(0.25, 0.7),
    )
    assert geometry.start.x == pytest.approx(250.0)
    assert geometry.start.y == pytest.approx(560.0)


def test_scale_bar_rendering_changes_only_overlay_region() -> None:
    image = np.full((800, 1000, 3), 255, dtype=np.uint8)
    rendered = draw_scale_bar(image, Calibration(0.1, Unit.MM))
    assert np.array_equal(rendered[0:100, 0:100], image[0:100, 0:100])
    assert not np.array_equal(rendered[700:800, 0:200], image[700:800, 0:200])
