from vision_measure.camera.models import CaptureConfig
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.workspace.controller import Workspace


def test_camera_change_invalidates_calibration() -> None:
    workspace = Workspace()
    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))
    workspace.on_camera_changed(CaptureConfig(width=1920, height=1080))
    assert workspace.current_calibration is None


def test_same_camera_config_keeps_calibration() -> None:
    workspace = Workspace()
    workspace.set_magnification("10x")
    config = CaptureConfig(width=1920, height=1080)
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM), capture_config=config)
    workspace.on_camera_changed(config)
    assert workspace.current_calibration is not None
