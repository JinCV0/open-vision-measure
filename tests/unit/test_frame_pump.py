import numpy as np

from vision_measure.camera.buffer import LatestFrameBuffer
from vision_measure.camera.models import FramePacket
from vision_measure.camera.pump import FramePump


class FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.index = 0

    def read_latest(self, timeout_s: float) -> FramePacket:
        del timeout_s
        self.index += 1
        return FramePacket(np.zeros((1, 1, 3), np.uint8), self.index)

    def close(self) -> None:
        self.closed = True


def test_pump_delivers_frames_and_closes_session() -> None:
    session = FakeSession()
    target = LatestFrameBuffer()
    pump = FramePump(session, target)
    pump.start()
    frame = target.take_latest(1.0)
    pump.stop()
    assert frame is not None
    assert session.closed
