from __future__ import annotations

from typing import Protocol

from vision_measure.camera.models import (
    CameraApi,
    CameraDevice,
    CameraMode,
    CaptureConfig,
    FramePacket,
)


class CameraUnavailable(RuntimeError):
    pass


class CameraReadTimeout(RuntimeError):
    pass


class CameraSession(Protocol):
    @property
    def mode(self) -> CameraMode: ...

    def read_latest(self, timeout_s: float) -> FramePacket: ...

    def close(self) -> None: ...


class CameraBackend(Protocol):
    def discover(self, api: CameraApi = CameraApi.AUTO) -> tuple[CameraDevice, ...]: ...

    def open(self, device: CameraDevice, config: CaptureConfig) -> CameraSession: ...
