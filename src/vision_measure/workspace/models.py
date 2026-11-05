from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vision_measure.inspection.models import Line, MagnificationProfile
from vision_measure.inspection.processing import ImageSettings


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    line: Line
    magnification: str


@dataclass(frozen=True, slots=True)
class SubjectCaptureResult:
    original: np.ndarray = field(repr=False)
    mask: np.ndarray | None = field(repr=False)
    composite: np.ndarray = field(repr=False)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    schema_version: int = 2
    magnifications: tuple[MagnificationProfile, ...] = ()
    current_magnification: str | None = None
    records: tuple[MeasurementRecord, ...] = ()
    image_settings: ImageSettings = ImageSettings()
