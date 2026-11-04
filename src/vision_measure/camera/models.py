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
class CameraMode:
    width: int
    height: int
    fps: float
    fourcc: str


@dataclass(frozen=True, slots=True)
class CameraDevice:
    index: int
    label: str
    api: CameraApi = CameraApi.AUTO


@dataclass(frozen=True, slots=True)
class CaptureConfig:
    width: int = 0
    height: int = 0
    fps: float = 0.0
    api: CameraApi = CameraApi.AUTO
    fourcc: str = "auto"

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("capture dimensions must be non-negative")
        if (self.width == 0) != (self.height == 0):
            raise ValueError("width and height must both be automatic or specified")
        if self.fps < 0:
            raise ValueError("frame rate must be non-negative")
        if self.fourcc != "auto" and len(self.fourcc) != 4:
            raise ValueError("fourcc must be auto or four characters")


@dataclass(frozen=True, slots=True)
class FramePacket:
    image: np.ndarray = field(repr=False)
    sequence: int
    captured_at_ns: int | None = None
