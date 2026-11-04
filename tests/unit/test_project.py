import json

import pytest

from vision_measure.inspection.models import (
    Calibration,
    Line,
    MagnificationProfile,
    Point,
    Unit,
)
from vision_measure.workspace.models import MeasurementRecord, ProjectDocument
from vision_measure.workspace.project import ProjectFormatError, load_project, save_project


def _document() -> ProjectDocument:
    return ProjectDocument(
        schema_version=2,
        magnifications=(
            MagnificationProfile(
                name="10x",
                calibration=Calibration(0.5, Unit.MM),
                scale_bar_length=10.0,
            ),
        ),
        current_magnification="10x",
        records=(MeasurementRecord(Line(Point(1, 2), Point(3, 4)), "10x"),),
    )


def test_v2_project_round_trip(tmp_path) -> None:
    source = _document()
    path = tmp_path / "project.json"
    save_project(path, source)
    loaded = load_project(path)
    assert loaded == source
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2


def test_v1_project_migrates_single_calibration(tmp_path) -> None:
    path = tmp_path / "v1.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lines": [{"start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}}],
                "unit": "mm",
                "calibration": {"units_per_pixel": 0.1, "unit": "mm"},
                "image_settings": {},
            }
        ),
        encoding="utf-8",
    )
    loaded = load_project(path)
    assert loaded.schema_version == 2
    assert [profile.name for profile in loaded.magnifications] == ["default"]
    assert loaded.current_magnification == "default"
    assert loaded.magnifications[0].calibration == Calibration(0.1, Unit.MM)
    assert loaded.records[0].magnification == "default"


def test_unknown_schema_version_is_rejected(tmp_path) -> None:
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(ProjectFormatError):
        load_project(path)
