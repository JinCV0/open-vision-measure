from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


class CameraApi(StrEnum):
    AUTO = "auto"
    MSMF = "msmf"
    DSHOW = "dshow"
    V4L2 = "v4l2"


@dataclass(frozen=True, slots=True)
class CameraDevice:
    index: int
    label: str


@dataclass(frozen=True, slots=True)
class CaptureConfig:
    width: int = 1280
    height: int = 720
    fps: float = 30.0
    api: CameraApi = CameraApi.AUTO

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("capture dimensions must be positive")
        if self.fps <= 0:
            raise ValueError("frame rate must be positive")


@dataclass(frozen=True, slots=True)
class FramePacket:
    image: np.ndarray = field(repr=False)
    sequence: int
    captured_at_ns: int | None = None
