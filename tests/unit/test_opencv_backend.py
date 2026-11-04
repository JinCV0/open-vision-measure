from unittest.mock import patch

import cv2
import numpy as np

from vision_measure.camera.models import (
    CameraApi,
    CameraDevice,
    CameraMode,
    CaptureConfig,
)
from vision_measure.camera.opencv_backend import (
    OpenCvCameraBackend,
    _decode_fourcc,
    choose_best_mode,
)


def test_discovery_uses_requested_backend() -> None:
    with patch(
        "vision_measure.camera.opencv_backend._probe_camera"
    ) as probe:
        probe.side_effect = [True, False]
        devices = OpenCvCameraBackend(max_devices=2).discover(CameraApi.MSMF)
    assert [device.index for device in devices] == [0]
    assert all(call.args[1] is CameraApi.MSMF for call in probe.call_args_list)


def test_auto_discovery_falls_back_to_directshow() -> None:
    with patch(
        "vision_measure.camera.opencv_backend._probe_camera"
    ) as probe:
        probe.side_effect = lambda index, api: index == 0 and api is CameraApi.DSHOW
        devices = OpenCvCameraBackend(max_devices=2).discover(CameraApi.AUTO)
    assert len(devices) == 1
    assert devices[0].api is CameraApi.DSHOW


def test_capture_config_defaults_to_best_mode() -> None:
    config = CaptureConfig()
    assert config.width == 0
    assert config.height == 0
    assert config.fps == 0
    assert config.fourcc == "auto"


def test_best_mode_prioritizes_resolution_then_uncompressed_format() -> None:
    best = choose_best_mode(
        (
            CameraMode(1920, 1080, 60, "MJPG"),
            CameraMode(1920, 1080, 20, "YUY2"),
            CameraMode(1280, 720, 60, "YUY2"),
        )
    )
    assert best.fourcc == "YUY2"
    assert best.width == 1920
    assert best.height == 1080


class FakeCapture:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.width = 640
        self.height = 480
        self.fps = 30.0
        self.opened = True

    def isOpened(self) -> bool:
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        if prop == cv2.CAP_PROP_FOURCC:
            self.mode = _decode_fourcc(value)
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        if self.mode == "YUY2":
            self.width, self.height = 1280, 720
        elif self.mode == "MJPG":
            self.width, self.height = 1920, 1080
        return True, np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def get(self, prop: int) -> float:
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.width)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.height)
        if prop == cv2.CAP_PROP_FPS:
            return self.fps
        if prop == cv2.CAP_PROP_FOURCC:
            return 0.0 if not self.mode else float(
                sum(ord(c) << (8 * i) for i, c in enumerate(self.mode))
            )
        return 0.0

    def release(self) -> None:
        self.opened = False


def test_auto_open_chooses_highest_resolution_format() -> None:
    captures = [FakeCapture("") for _ in range(7)]

    def factory(index: int, api: CameraApi) -> FakeCapture:
        del index, api
        return captures.pop(0)

    backend = OpenCvCameraBackend(capture_factory=factory)  # type: ignore[arg-type]
    session = backend.open(CameraDevice(0, "fake"), CaptureConfig())
    assert session.mode.width == 1920
    assert session.mode.height == 1080
    assert session.mode.fourcc == "MJPG"
    session.close()
