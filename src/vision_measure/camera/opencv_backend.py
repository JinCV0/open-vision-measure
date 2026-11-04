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
    CameraMode,
    CaptureConfig,
    FramePacket,
)

_FORMAT_CANDIDATES = ("YUY2", "UYVY", "NV12", "MJPG", "H264", "")
_FORMAT_PRIORITY = {
    "YUYV": 6,
    "YUY2": 6,
    "UYVY": 5,
    "I420": 5,
    "NV12": 4,
    "MJPG": 2,
    "H264": 1,
}


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


def _decode_fourcc(value: float) -> str:
    encoded = int(value)
    if encoded == 0:
        return ""
    return "".join(chr((encoded >> (8 * index)) & 0xFF) for index in range(4)).strip()


def _encode_fourcc(value: str) -> int:
    return sum(ord(character) << (8 * index) for index, character in enumerate(value))


def _format_priority(fourcc: str) -> int:
    return _FORMAT_PRIORITY.get(fourcc.upper(), 3)


def choose_best_mode(modes: tuple[CameraMode, ...]) -> CameraMode:
    if not modes:
        raise CameraUnavailable("camera exposed no usable capture mode")
    return max(
        modes,
        key=lambda mode: (
            mode.width * mode.height,
            _format_priority(mode.fourcc),
            mode.fps,
        ),
    )


class OpenCvCameraSession:
    def __init__(self, capture: cv2.VideoCapture, mode: CameraMode) -> None:
        self._capture = capture
        self._mode = mode
        self._sequence = 0
        self._closed = False

    @property
    def mode(self) -> CameraMode:
        return self._mode

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
        formats = (
            (config.fourcc,)
            if config.fourcc != "auto"
            else _FORMAT_CANDIDATES
        )
        modes = tuple(
            mode
            for fourcc in formats
            if (
                mode := self._probe_mode(
                    device,
                    selected_api,
                    config.width,
                    config.height,
                    config.fps,
                    fourcc,
                )
            )
            is not None
        )
        best = choose_best_mode(modes)
        capture = self._capture_factory(device.index, selected_api)
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailable(f"cannot open camera {device.index}")
        self._configure(
            capture,
            best.width,
            best.height,
            best.fps,
            best.fourcc,
        )
        if not capture.read()[0]:
            capture.release()
            raise CameraUnavailable("camera opened but returned no frames")
        return OpenCvCameraSession(capture, best)

    def _probe_mode(
        self,
        device: CameraDevice,
        api: CameraApi,
        width: int,
        height: int,
        fps: float,
        fourcc: str,
    ) -> CameraMode | None:
        capture = self._capture_factory(device.index, api)
        try:
            if not capture.isOpened():
                return None
            self._configure(capture, width, height, fps, fourcc)
            grabbed, image = capture.read()
            if not grabbed or image is None:
                return None
            actual_width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
            actual_height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            if actual_width <= 0 or actual_height <= 0:
                actual_height, actual_width = image.shape[:2]
            actual_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            actual_fourcc = _decode_fourcc(capture.get(cv2.CAP_PROP_FOURCC))
            return CameraMode(
                width=actual_width,
                height=actual_height,
                fps=actual_fps,
                fourcc=actual_fourcc or fourcc or "AUTO",
            )
        finally:
            capture.release()

    @staticmethod
    def _configure(
        capture: cv2.VideoCapture,
        width: int,
        height: int,
        fps: float,
        fourcc: str,
    ) -> None:
        if fourcc and fourcc.upper() != "AUTO":
            capture.set(cv2.CAP_PROP_FOURCC, _encode_fourcc(fourcc))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width if width > 0 else 100_000)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height if height > 0 else 100_000)
        if fps > 0:
            capture.set(cv2.CAP_PROP_FPS, fps)
