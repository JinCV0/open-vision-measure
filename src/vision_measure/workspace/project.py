from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vision_measure.inspection.models import Calibration, Line, Point, Unit
from vision_measure.inspection.processing import ImageSettings
from vision_measure.workspace.models import ProjectDocument

SCHEMA_VERSION = 1


class ProjectFormatError(ValueError):
    pass


def _point_json(point: Point) -> dict[str, float]:
    return {"x": point.x, "y": point.y}


def _document_json(document: ProjectDocument) -> dict[str, Any]:
    calibration = document.calibration
    return {
        "schema_version": document.schema_version,
        "lines": [
            {"start": _point_json(line.start), "end": _point_json(line.end)}
            for line in document.lines
        ],
        "unit": document.unit.value,
        "calibration": (
            None
            if calibration is None
            else {
                "units_per_pixel": calibration.units_per_pixel,
                "unit": calibration.unit.value,
            }
        ),
        "image_settings": asdict(document.image_settings),
    }


def save_project(path: Path, document: ProjectDocument) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_document_json(document), ensure_ascii=False, indent=2)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(payload)
            stream.write("\n")
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _parse_point(raw: Any) -> Point:
    if not isinstance(raw, dict):
        raise ProjectFormatError("point must be an object")
    try:
        return Point(float(raw["x"]), float(raw["y"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid point") from exc


def _parse_line(raw: Any) -> Line:
    if not isinstance(raw, dict):
        raise ProjectFormatError("line must be an object")
    return Line(_parse_point(raw.get("start")), _parse_point(raw.get("end")))


def load_project(path: Path) -> ProjectDocument:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectFormatError("cannot read project") from exc
    if not isinstance(raw, dict):
        raise ProjectFormatError("project root must be an object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ProjectFormatError("unsupported schema version")
    try:
        unit = Unit(raw.get("unit", Unit.MM.value))
        lines = tuple(_parse_line(item) for item in raw.get("lines", []))
        calibration_raw = raw.get("calibration")
        calibration = (
            None
            if calibration_raw is None
            else Calibration(
                units_per_pixel=float(calibration_raw["units_per_pixel"]),
                unit=Unit(calibration_raw["unit"]),
            )
        )
        settings_raw = raw.get("image_settings", {})
        return ProjectDocument(
            schema_version=SCHEMA_VERSION,
            lines=lines,
            unit=unit,
            calibration=calibration,
            image_settings=ImageSettings(**settings_raw),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid project data") from exc
