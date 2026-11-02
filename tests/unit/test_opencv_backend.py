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


def test_auto_discovery_falls_back_to_directshow() -> None:
    with patch(
        "vision_measure.camera.opencv_backend._probe_camera"
    ) as probe:
        probe.side_effect = lambda index, api: index == 0 and api is CameraApi.DSHOW
        devices = OpenCvCameraBackend(max_devices=2).discover(CameraApi.AUTO)
    assert len(devices) == 1
    assert devices[0].api is CameraApi.DSHOW
