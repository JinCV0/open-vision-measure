from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np

from vision_measure.inspection.annotations import (
    DEFAULT_SCALE_BAR_POSITION,
    NormalizedPoint,
    draw_scale_bar,
)
from vision_measure.inspection.models import Calibration
from vision_measure.inspection.scale_bar import ScaleBarStyle
from vision_measure.inspection.scale_bar_renderer import render_scale_bar
from vision_measure.workspace.preferences import IMAGE_EXTENSIONS


class ScreenshotError(RuntimeError):
    pass


def next_capture_path(
    directory: Path,
    extension: str = ".png",
    stem: str = "capture",
) -> Path:
    directory = Path(directory)
    extension = extension.lower()
    if not extension.startswith("."):
        extension = f".{extension}"
    if extension not in IMAGE_EXTENSIONS:
        raise ValueError("unsupported screenshot extension")
    directory.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(stem)}_(\d+)\.[^.]+$", re.IGNORECASE)
    indexes = [
        int(match.group(1))
        for path in directory.iterdir()
        if path.is_file() and (match := pattern.match(path.name))
    ]
    return directory / f"{stem}_{max(indexes, default=0) + 1:04d}{extension}"


def save_capture(
    image: np.ndarray,
    path: Path,
    calibration: Calibration | None = None,
    scale_bar_enabled: bool = False,
    scale_bar_position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION,
    scale_bar_length: float | None = None,
    scale_bar_style: ScaleBarStyle | None = None,
) -> Path:
    if image.ndim != 3 or image.shape[2] != 3:
        raise ScreenshotError("image must be an HxWx3 BGR image")
    rendered = image
    if scale_bar_enabled:
        if calibration is None:
            raise ScreenshotError("scale bar requires calibration")
        if scale_bar_style is not None:
            if scale_bar_length is None:
                raise ScreenshotError("fixed scale bar length is required")
            rendered = render_scale_bar(
                image,
                calibration,
                scale_bar_length,
                scale_bar_position,
                scale_bar_style,
            )
        else:
            rendered = draw_scale_bar(
                image,
                calibration,
                scale_bar_position,
                fixed_length=scale_bar_length,
            )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    extension = path.suffix.lower()
    image_format = ".jpg" if extension in {".jpg", ".jpeg"} else ".png"
    encoded, buffer = cv2.imencode(image_format, rendered)
    if not encoded:
        raise ScreenshotError(f"cannot encode image: {path}")
    try:
        path.write_bytes(buffer.tobytes())
    except OSError as exc:
        raise ScreenshotError(f"cannot write image: {path}") from exc
    return path
