from pathlib import Path

import pytest

from vision_measure.camera.models import CameraDevice, CaptureConfig
from vision_measure.camera.synthetic import SyntheticCameraBackend
from vision_measure.inspection.models import Line, Point, Unit
from vision_measure.workspace.controller import Workspace


def test_capture_calibrate_save_load_export(tmp_path: Path) -> None:
    workspace = Workspace()
    session = SyntheticCameraBackend().open(
        CameraDevice(0, "synthetic"), CaptureConfig()
    )
    workspace.attach_session(session)
    assert workspace.refresh_frame(1.0) is not None
    workspace.freeze()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.MM)
    result = workspace.add_line(Line(Point(0, 0), Point(50, 0)))
    assert result.physical_length == pytest.approx(5.0)

    project = tmp_path / "sample.ovm.json"
    csv_path = tmp_path / "measurements.csv"
    screenshot = tmp_path / "截图.png"
    workspace.save_project(project)
    workspace.save_display_frame(screenshot)
    workspace.export_csv(csv_path)

    loaded = Workspace()
    loaded.load_project(project)
    assert screenshot.is_file()
    assert "physical_length" in csv_path.read_text(encoding="utf-8")
    assert len(loaded.project.lines) == 1
    workspace.stop()
