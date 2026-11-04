import pytest

from vision_measure.ui.panels import ImagePanel, MeasurementPanel


def test_image_sliders_map_to_processing_settings(qtbot) -> None:
    panel = ImagePanel()
    qtbot.addWidget(panel)
    panel.brightness_slider.setValue(20)
    panel.contrast_slider.setValue(125)
    panel.temperature_slider.setValue(-30)
    panel.tint_slider.setValue(40)
    settings = panel.settings()
    assert settings.brightness == pytest.approx(51.0)
    assert settings.contrast == pytest.approx(1.25)
    assert settings.temperature == pytest.approx(-30.0)
    assert settings.tint == pytest.approx(40.0)


def test_scale_bar_switch_requires_calibration(qtbot) -> None:
    panel = MeasurementPanel()
    qtbot.addWidget(panel)
    assert not panel.scale_bar_box.isEnabled()
    panel.set_calibration_available(True)
    assert panel.scale_bar_box.isEnabled()
