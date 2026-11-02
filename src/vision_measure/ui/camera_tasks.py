from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from vision_measure.camera.models import CameraApi, CameraDevice, CaptureConfig
from vision_measure.camera.opencv_backend import OpenCvCameraBackend


class CameraDiscoveryThread(QThread):
    devices_found = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        backend: OpenCvCameraBackend,
        api: CameraApi,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._api = api

    def run(self) -> None:
        try:
            self.devices_found.emit(self._backend.discover(self._api))
        except Exception as exc:
            self.failed.emit(str(exc))


class CameraOpenThread(QThread):
    opened = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        backend: OpenCvCameraBackend,
        device: CameraDevice,
        config: CaptureConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._device = device
        self._config = config

    def run(self) -> None:
        try:
            self.opened.emit(self._backend.open(self._device, self._config))
        except Exception as exc:
            self.failed.emit(str(exc))
