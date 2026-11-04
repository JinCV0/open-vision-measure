from __future__ import annotations

from dataclasses import dataclass

from vision_measure.inspection.models import Calibration, Line, Unit
from vision_measure.inspection.processing import ImageSettings


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    schema_version: int = 1
    lines: tuple[Line, ...] = ()
    unit: Unit = Unit.MM
    calibration: Calibration | None = None
    image_settings: ImageSettings = ImageSettings()
