import numpy as np

from vision_measure.camera.buffer import LatestFrameBuffer
from vision_measure.camera.models import FramePacket


def packet(value: int) -> FramePacket:
    return FramePacket(np.full((2, 2, 3), value, dtype=np.uint8), value)


def test_new_frame_replaces_unconsumed_frame() -> None:
    buffer = LatestFrameBuffer()
    buffer.put(packet(1))
    buffer.put(packet(2))
    taken = buffer.take_latest(timeout_s=0)
    assert taken is not None
    assert int(taken.image[0, 0, 0]) == 2
