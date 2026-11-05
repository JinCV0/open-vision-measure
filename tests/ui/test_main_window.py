from pathlib import Path

from vision_measure.camera.models import CameraDevice, CaptureConfig
from vision_measure.camera.synthetic import SyntheticCameraBackend
from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Line, Point, Unit
from vision_measure.ui.main_window import MainWindow
from vision_measure.workspace.controller import Workspace
from vision_measure.workspace.preferences import AppPreferences, PreferencesStore


def test_main_window_opens_with_idle_workspace(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert window.workspace.state.value == "idle"
    assert window.windowTitle() == "Open Vision Measure"
    assert not hasattr(window, "measurement_table")
    assert window.camera_bar.width_spin.value() == 0
    assert window.camera_bar.height_spin.value() == 0
    assert window.camera_bar.fps_spin.value() == 0


def test_main_window_does_not_expose_ai_capture(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert not hasattr(window, "ai_capture")
    assert not hasattr(window.image_panel, "ai_screenshot_button")


def test_screenshot_uses_persisted_folder_and_sequence(qtbot, tmp_path: Path) -> None:
    screenshot_directory = tmp_path / "captures"
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(AppPreferences(screenshot_directory=screenshot_directory))
    workspace = Workspace()
    session = SyntheticCameraBackend().open(CameraDevice(0, "synthetic"), CaptureConfig())
    workspace.attach_session(session)
    assert workspace.refresh_frame(1.0) is not None
    workspace.freeze()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.MM)
    window = MainWindow(
        workspace=workspace,
        preferences_store=store,
        auto_discover=False,
    )
    qtbot.addWidget(window)

    window._save_screenshot()
    window._save_screenshot()

    assert (screenshot_directory / "capture_0001.png").is_file()
    assert (screenshot_directory / "capture_0002.png").is_file()
    workspace.stop()


def test_scale_bar_switch_persists_on_calibrated_workspace(qtbot, tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.MM)
    window = MainWindow(workspace=workspace, preferences_store=store, auto_discover=False)
    qtbot.addWidget(window)
    window.calibration_panel.scale_bar_box.setChecked(True)
    assert store.load().scale_bar_enabled is True


def test_scale_bar_position_persists_after_drag(qtbot, tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.MM)
    window = MainWindow(workspace=workspace, preferences_store=store, auto_discover=False)
    qtbot.addWidget(window)
    window.viewport.scale_bar_moved.emit(NormalizedPoint(0.3, 0.6))
    assert store.load().scale_bar_position == NormalizedPoint(0.3, 0.6)
