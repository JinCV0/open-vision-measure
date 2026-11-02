from unittest.mock import patch

from vision_measure.camera.models import CameraApi
from vision_measure.camera.opencv_backend import OpenCvCameraBackend


def test_discovery_uses_requested_backend() -> None:
    with patch(
        "vision_measure.camera.opencv_backend._probe_camera"
    ) as probe:
        probe.side_effect = [True, False]
        devices = OpenCvCameraBackend(max_devices=2).discover(CameraApi.MSMF)
    assert [device.index for device in devices] == [0]
    assert all(call.args[1] is CameraApi.MSMF for call in probe.call_args_list)
