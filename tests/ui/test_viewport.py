import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt

from vision_measure.inspection.models import Calibration, Unit
from vision_measure.ui.viewport import ImageViewport


def test_viewport_maps_widget_coordinates_to_image(qtbot) -> None:
    viewport = ImageViewport()
    qtbot.addWidget(viewport)
    viewport.resize(640, 480)
    viewport.set_frame(np.zeros((480, 640, 3), dtype=np.uint8))
    assert viewport.widget_to_image(320, 240) == (320.0, 240.0)


def test_scale_bar_can_be_dragged_on_canvas(qtbot) -> None:
    viewport = ImageViewport()
    qtbot.addWidget(viewport)
    viewport.resize(1000, 800)
    viewport.set_frame(np.zeros((800, 1000, 3), dtype=np.uint8))
    viewport.set_scale_bar(Calibration(0.1, Unit.MM), True)

    with qtbot.waitSignal(viewport.scale_bar_moved, timeout=1000):
        qtbot.mousePress(viewport, Qt.MouseButton.LeftButton, pos=QPoint(40, 736))
        qtbot.mouseMove(viewport, QPoint(240, 536))
        qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=QPoint(240, 536))

    assert viewport.scale_bar_position.x == pytest.approx(0.24)
    assert viewport.scale_bar_position.y == pytest.approx(0.67)
