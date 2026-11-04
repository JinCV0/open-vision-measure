from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vision_measure.inspection.models import (
    DEFAULT_MAGNIFICATION_NAME,
    Calibration,
    Line,
    MagnificationProfile,
    Point,
    Unit,
)
from vision_measure.inspection.processing import ImageSettings
from vision_measure.workspace.models import MeasurementRecord, ProjectDocument

SCHEMA_VERSION = 2


class ProjectFormatError(ValueError):
    pass


def _point_json(point: Point) -> dict[str, float]:
    return {"x": point.x, "y": point.y}


def _line_json(line: Line) -> dict[str, Any]:
    return {"start": _point_json(line.start), "end": _point_json(line.end)}


def _calibration_json(calibration: Calibration | None) -> dict[str, Any] | None:
    if calibration is None:
        return None
    return {
        "units_per_pixel": calibration.units_per_pixel,
        "unit": calibration.unit.value,
    }


def _profile_json(profile: MagnificationProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "calibration": _calibration_json(profile.calibration),
        "calibrated_at": profile.calibrated_at,
        "reference_length": profile.reference_length,
        "scale_bar_length": profile.scale_bar_length,
    }


def _document_json(document: ProjectDocument) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "magnifications": [_profile_json(profile) for profile in document.magnifications],
        "current_magnification": document.current_magnification,
        "records": [
            {"line": _line_json(record.line), "magnification": record.magnification}
            for record in document.records
        ],
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


def _parse_calibration(raw: Any) -> Calibration | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ProjectFormatError("calibration must be an object or null")
    try:
        return Calibration(
            units_per_pixel=float(raw["units_per_pixel"]),
            unit=Unit(raw["unit"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid calibration") from exc


def _parse_profile(raw: Any) -> MagnificationProfile:
    if not isinstance(raw, dict):
        raise ProjectFormatError("magnification must be an object")
    try:
        return MagnificationProfile(
            name=str(raw["name"]),
            calibration=_parse_calibration(raw.get("calibration")),
            calibrated_at=raw.get("calibrated_at"),
            reference_length=raw.get("reference_length"),
            scale_bar_length=raw.get("scale_bar_length"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid magnification") from exc


def _parse_record(raw: Any) -> MeasurementRecord:
    if not isinstance(raw, dict):
        raise ProjectFormatError("record must be an object")
    try:
        return MeasurementRecord(
            _parse_line(raw.get("line")),
            str(raw.get("magnification", DEFAULT_MAGNIFICATION_NAME)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid record") from exc


def _migrate_v1(raw: dict[str, Any]) -> ProjectDocument:
    profile = MagnificationProfile(
        name=DEFAULT_MAGNIFICATION_NAME,
        calibration=_parse_calibration(raw.get("calibration")),
    )
    records = tuple(
        MeasurementRecord(_parse_line(item), DEFAULT_MAGNIFICATION_NAME)
        for item in raw.get("lines", [])
    )
    try:
        image_settings = ImageSettings(**raw.get("image_settings", {}))
    except (TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid project data") from exc
    return ProjectDocument(
        schema_version=SCHEMA_VERSION,
        magnifications=(profile,),
        current_magnification=DEFAULT_MAGNIFICATION_NAME,
        records=records,
        image_settings=image_settings,
    )


def load_project(path: Path) -> ProjectDocument:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectFormatError("cannot read project") from exc
    if not isinstance(raw, dict):
        raise ProjectFormatError("project root must be an object")
    version = raw.get("schema_version")
    if version == 1:
        return _migrate_v1(raw)
    if version != SCHEMA_VERSION:
        raise ProjectFormatError("unsupported schema version")
    try:
        magnifications = tuple(
            _parse_profile(item) for item in raw.get("magnifications", [])
        )
        records = tuple(_parse_record(item) for item in raw.get("records", []))
        image_settings = ImageSettings(**raw.get("image_settings", {}))
        return ProjectDocument(
            schema_version=SCHEMA_VERSION,
            magnifications=magnifications,
            current_magnification=raw.get("current_magnification"),
            records=records,
            image_settings=image_settings,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError("invalid project data") from exc
