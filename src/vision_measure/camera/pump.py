from __future__ import annotations

import threading

from vision_measure.camera.backend import CameraReadTimeout, CameraSession
from vision_measure.camera.buffer import LatestFrameBuffer


class FramePump:
    def __init__(self, session: CameraSession, target: LatestFrameBuffer) -> None:
        self._session = session
        self._target = target
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: Exception | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="vision-measure-camera-pump",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    packet = self._session.read_latest(timeout_s=0.1)
                except CameraReadTimeout:
                    continue
                if not self._target.put(packet):
                    return
                self._stop_event.wait(0.001)
        except Exception as exc:
            self.last_error = exc
        finally:
            self._target.close()
            self._session.close()

    def stop(self) -> None:
        self._stop_event.set()
        self._target.close()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
