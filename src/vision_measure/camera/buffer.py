from __future__ import annotations

import threading
from dataclasses import dataclass, field

from vision_measure.camera.models import FramePacket


@dataclass(slots=True)
class LatestFrameBuffer:
    _condition: threading.Condition = field(
        default_factory=threading.Condition, init=False, repr=False
    )
    _packet: FramePacket | None = field(default=None, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def put(self, packet: FramePacket) -> bool:
        with self._condition:
            if self._closed:
                return False
            self._packet = packet
            self._condition.notify_all()
            return True

    def take_latest(self, timeout_s: float) -> FramePacket | None:
        if timeout_s < 0:
            raise ValueError("timeout_s must be non-negative")
        with self._condition:
            if self._packet is None and not self._closed:
                self._condition.wait(timeout_s)
            packet = self._packet
            self._packet = None
            return packet

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed
