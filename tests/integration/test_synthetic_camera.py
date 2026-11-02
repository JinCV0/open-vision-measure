import numpy as np

from vision_measure.camera.models import CameraDevice, CaptureConfig
from vision_measure.camera.synthetic import SyntheticCameraBackend


def test_synthetic_camera_emits_incrementing_frames() -> None:
    backend = SyntheticCameraBackend()
    session = backend.open(CameraDevice(0, "synthetic"), CaptureConfig())
    first = session.read_latest(timeout_s=0)
    second = session.read_latest(timeout_s=0)
    session.close()
    assert first.image.shape == (480, 640, 3)
    assert np.all(second.image > first.image)
