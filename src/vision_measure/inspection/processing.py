from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import cv2
import numpy as np


class InvalidFrame(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImageSettings:
    brightness: float = 0.0
    contrast: float = 1.0
    grayscale: bool = False
    canny: bool = False
    canny_low: int = 50
    canny_high: int = 150

    def __post_init__(self) -> None:
        if not math.isfinite(self.brightness) or not -255 <= self.brightness <= 255:
            raise ValueError("brightness must be finite and between -255 and 255")
        if not math.isfinite(self.contrast) or not 0.1 <= self.contrast <= 4.0:
            raise ValueError("contrast must be finite and between 0.1 and 4.0")
        if not 0 <= self.canny_low < self.canny_high <= 255:
            raise ValueError("Canny thresholds must satisfy 0 <= low < high <= 255")


def _validate_frame(frame: np.ndarray) -> None:
    if (
        frame.ndim != 3
        or frame.shape[0] == 0
        or frame.shape[1] == 0
        or frame.shape[2] != 3
    ):
        raise InvalidFrame("frame must be a non-empty HxWx3 BGR image")
    if frame.dtype != np.uint8:
        raise InvalidFrame("frame dtype must be uint8")


def process_frame(frame: np.ndarray, settings: ImageSettings) -> np.ndarray:
    _validate_frame(frame)
    adjusted = (frame.astype(np.float32) - 127.5) * settings.contrast
    adjusted += 127.5 + settings.brightness
    result = np.clip(adjusted, 0, 255).astype(np.uint8)

    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) if settings.grayscale else None
    if settings.canny:
        source = gray if gray is not None else cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.Canny(source, settings.canny_low, settings.canny_high)
    elif gray is not None:
        result = gray

    if result.ndim == 2:
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    return cast(np.ndarray, result)
