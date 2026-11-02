import numpy as np

from vision_measure.ui.viewport import ImageViewport


def test_viewport_maps_widget_coordinates_to_image(qtbot) -> None:
    viewport = ImageViewport()
    qtbot.addWidget(viewport)
    viewport.resize(640, 480)
    viewport.set_frame(np.zeros((480, 640, 3), dtype=np.uint8))
    assert viewport.widget_to_image(320, 240) == (320.0, 240.0)
