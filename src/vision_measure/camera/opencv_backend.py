from __future__ import annotations

import sys
import time
from collections.abc import Callable

import cv2
import numpy as np

from vision_measure.camera.backend import CameraReadTimeout, CameraUnavailable
from vision_measure.camera.models import (
    CameraApi,
    CameraDevice,
    CaptureConfig,
    FramePacket,
)


def _backend_code(api: CameraApi) -> int:
    mapping: dict[CameraApi, int] = {
        CameraApi.AUTO: cv2.CAP_ANY,
        CameraApi.MSMF: cv2.CAP_MSMF,
        CameraApi.DSHOW: cv2.CAP_DSHOW,
        CameraApi.V4L2: cv2.CAP_V4L2,
    }
    return mapping[api]


def _open_capture(index: int, api: CameraApi) -> cv2.VideoCapture:
    return cv2.VideoCapture(index, _backend_code(api))


def _probe_camera(index: int, api: CameraApi) -> bool:
    capture = _open_capture(index, api)
    try:
        return bool(capture.isOpened() and capture.read()[0])
    finally:
        capture.release()


class OpenCvCameraSession:
    def __init__(self, capture: cv2.VideoCapture) -> None:
        self._capture = capture
        self._sequence = 0
        self._closed = False

    def read_latest(self, timeout_s: float) -> FramePacket:
        if timeout_s < 0:
            raise ValueError("timeout_s must be non-negative")
        if self._closed:
            raise CameraUnavailable("camera session is closed")
        grabbed, image = self._capture.read()
        if not grabbed or image is None:
            raise CameraReadTimeout("camera did not return a frame")
        self._sequence += 1
        return FramePacket(
            image=np.asarray(image, dtype=np.uint8),
            sequence=self._sequence,
            captured_at_ns=time.time_ns(),
        )

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._capture.release()


class OpenCvCameraBackend:
    def __init__(
        self,
        max_devices: int = 5,
        capture_factory: Callable[[int, CameraApi], cv2.VideoCapture] = _open_capture,
    ) -> None:
        if max_devices <= 0:
            raise ValueError("max_devices must be positive")
        self._max_devices = max_devices
        self._capture_factory = capture_factory

    def discover(self, api: CameraApi = CameraApi.AUTO) -> tuple[CameraDevice, ...]:
        candidates = (
            (api,)
            if api is not CameraApi.AUTO
            else (
                (CameraApi.MSMF, CameraApi.DSHOW)
                if sys.platform == "win32"
                else (CameraApi.V4L2,)
            )
        )
        devices: list[CameraDevice] = []
        for index in range(self._max_devices):
            for candidate in candidates:
                if _probe_camera(index, candidate):
                    devices.append(
                        CameraDevice(
                            index=index,
                            label=f"Camera {index} ({candidate.value})",
                            api=candidate,
                        )
                    )
                    break
        return tuple(devices)

    def open(self, device: CameraDevice, config: CaptureConfig) -> OpenCvCameraSession:
        selected_api = config.api if config.api is not CameraApi.AUTO else device.api
        capture = self._capture_factory(device.index, selected_api)
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailable(f"cannot open camera {device.index}")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
        capture.set(cv2.CAP_PROP_FPS, config.fps)
        return OpenCvCameraSession(capture)
