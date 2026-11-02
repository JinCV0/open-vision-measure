import json

import pytest

from vision_measure.inspection.models import Line, Point, Unit
from vision_measure.workspace.models import ProjectDocument
from vision_measure.workspace.project import ProjectFormatError, load_project, save_project


def test_project_round_trip(tmp_path) -> None:
    source = ProjectDocument(
        lines=(Line(Point(1, 2), Point(3, 4)),),
        unit=Unit.MM,
    )
    path = tmp_path / "project.json"
    save_project(path, source)
    loaded = load_project(path)
    assert loaded == source
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_unknown_schema_version_is_rejected(tmp_path) -> None:
    path = tmp_path / "project.json"
    path.write_text('{"schema_version": 99}', encoding="utf-8")
    with pytest.raises(ProjectFormatError, match="unsupported schema version"):
        load_project(path)
