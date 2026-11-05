from __future__ import annotations

import threading
import time

import numpy as np

from vision_measure.camera.backend import CameraUnavailable
from vision_measure.camera.models import (
    CameraApi,
    CameraDevice,
    CameraMode,
    CaptureConfig,
    FramePacket,
)


class SyntheticCameraSession:
    def __init__(self, size: tuple[int, int]) -> None:
        self._height, self._width = size
        self._sequence = 0
        self._closed = False
        self._lock = threading.Lock()

    @property
    def mode(self) -> CameraMode:
        return CameraMode(self._width, self._height, 30.0, "RGB ")

    def read_latest(self, timeout_s: float) -> FramePacket:
        if timeout_s < 0:
            raise ValueError("timeout_s must be non-negative")
        with self._lock:
            if self._closed:
                raise CameraUnavailable("synthetic camera is closed")
            self._sequence += 1
            value = min(1 + (self._sequence % 200), 254)
            image = np.full((self._height, self._width, 3), value, dtype=np.uint8)
            return FramePacket(image, self._sequence, time.time_ns())

    def close(self) -> None:
        with self._lock:
            self._closed = True


class SyntheticCameraBackend:
    def __init__(self, size: tuple[int, int] = (480, 640)) -> None:
        self._size = size

    def discover(self, api: CameraApi = CameraApi.AUTO) -> tuple[CameraDevice, ...]:
        del api
        return (CameraDevice(0, "合成相机"),)

    def open(self, device: CameraDevice, config: CaptureConfig) -> SyntheticCameraSession:
        del device, config
        return SyntheticCameraSession(self._size)
