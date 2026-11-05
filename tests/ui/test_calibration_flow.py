import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Line, Point, Unit
from vision_measure.inspection.scale_bar import ScaleBarPreset, scale_bar_preset
from vision_measure.ui.main_window import MainWindow
from vision_measure.workspace.controller import Workspace
from vision_measure.workspace.preferences import AppPreferences, PreferencesStore


def test_main_window_exposes_magnification_selector(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert window.magnification_selector.count() >= 4


def test_uncalibrated_magnification_shows_placeholder(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert window.calibration_status.text() == "未标定"


def test_magnification_selection_switches_workspace_context(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    window.magnification_panel.select_magnification("40x")
    assert window.workspace.current_magnification == "40x"


def test_set_calibration_uses_two_viewport_clicks(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    window.calibration_panel.reference_length_spin.setValue(10.0)

    window.calibration_panel.calibrate_button.click()
    assert window.viewport.calibration_mode is True

    window.viewport.calibration_finished.emit(Line(Point(0, 0), Point(100, 0)))

    assert window.viewport.calibration_mode is False
    assert window.workspace.current_calibration is not None
    assert window.workspace.current_calibration.units_per_pixel == pytest.approx(0.1)
    assert window.workspace.current_calibration.unit is Unit.MM
    assert window.calibration_status.text() != "未标定"


def test_scale_bar_settings_requires_calibration(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert not window.calibration_panel.scale_bar_settings_button.isEnabled()


def test_measure_button_enables_one_shot_canvas_measurement(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    window.viewport.resize(500, 500)
    window.viewport.set_frame(np.zeros((100, 100, 3), dtype=np.uint8))

    window.calibration_panel.measure_button.click()
    assert window.viewport.measurement_mode is True
    assert window.calibration_panel.measure_button.isChecked() is True

    qtbot.mouseClick(window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
    qtbot.mouseClick(window.viewport, Qt.MouseButton.LeftButton, pos=QPoint(450, 50))

    assert len(window.workspace.lines) == 1
    assert window.viewport.measurement_mode is False
    assert window.calibration_panel.measure_button.isChecked() is False


def test_unit_selector_includes_micrometre(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    index = window.calibration_panel.unit_combo.findData(Unit.UM)
    assert index >= 0
    assert window.calibration_panel.unit_combo.itemText(index) == "微米"


def test_changing_unit_invalidates_stale_calibration(qtbot) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.MM)
    workspace.set_scale_bar_length(25.0)
    window = MainWindow(workspace=workspace, auto_discover=False)
    qtbot.addWidget(window)

    window.calibration_panel.unit_combo.setCurrentIndex(
        window.calibration_panel.unit_combo.findData(Unit.UM)
    )

    assert workspace.current_calibration is None
    assert workspace.current_scale_bar_length is None
    assert window.calibration_panel.selected_unit() is Unit.UM
    assert window.calibration_status.text() == "未标定 · 请重新标定"


def test_micrometre_calibration_enables_scale_bar_settings(qtbot) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.UM)
    window = MainWindow(workspace=workspace, auto_discover=False)
    qtbot.addWidget(window)

    assert workspace.current_calibration is not None
    assert workspace.current_calibration.unit is Unit.UM
    assert window.calibration_panel.scale_bar_settings_button.isEnabled()


def test_enabling_scale_bar_uses_profile_or_default_length(qtbot, tmp_path) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.UM)
    store = PreferencesStore(tmp_path / "preferences.json")
    window = MainWindow(workspace=workspace, preferences_store=store, auto_discover=False)
    qtbot.addWidget(window)

    window.calibration_panel.scale_bar_box.setChecked(True)

    assert workspace.current_scale_bar_length == pytest.approx(10.0)


def test_persisted_scale_bar_uses_fixed_default_after_calibration(qtbot, tmp_path) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.UM)
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(AppPreferences(scale_bar_enabled=True))

    window = MainWindow(workspace=workspace, preferences_store=store, auto_discover=False)
    qtbot.addWidget(window)

    assert workspace.current_scale_bar_length == pytest.approx(10.0)


def test_applied_scale_bar_settings_reach_viewport_and_preferences(qtbot, tmp_path) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.UM)
    store = PreferencesStore(tmp_path / "preferences.json")
    window = MainWindow(workspace=workspace, preferences_store=store, auto_discover=False)
    qtbot.addWidget(window)
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    position = NormalizedPoint(0.3, 0.4)

    window.scale_bar_settings.apply(style, 12.0, position)

    assert workspace.current_scale_bar_length == pytest.approx(12.0)
    assert window.viewport.scale_bar_style == style
    assert window.preferences.scale_bar_style == style
    assert window.preferences.scale_bar_position == position
    assert store.load().scale_bar_style == style


def test_two_click_calibration_uses_selected_micrometre_unit(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    window.calibration_panel.unit_combo.setCurrentIndex(
        window.calibration_panel.unit_combo.findData(Unit.UM)
    )
    window.calibration_panel.reference_length_spin.setValue(5.0)

    window.viewport.calibration_finished.emit(Line(Point(0, 0), Point(100, 0)))

    calibration = window.workspace.current_calibration
    assert calibration is not None
    assert calibration.unit is Unit.UM
    assert calibration.units_per_pixel == pytest.approx(0.05)
