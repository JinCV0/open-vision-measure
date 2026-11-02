from vision_measure.camera.models import CameraDevice, CaptureConfig
from vision_measure.camera.synthetic import SyntheticCameraBackend
from vision_measure.workspace.controller import Workspace, WorkspaceState


def test_workspace_freeze_and_resume() -> None:
    workspace = Workspace()
    session = SyntheticCameraBackend().open(
        CameraDevice(0, "synthetic"), CaptureConfig()
    )
    workspace.attach_session(session)
    workspace.refresh_frame(timeout_s=1.0)
    frozen = workspace.refresh_frame(timeout_s=1.0)
    workspace.freeze()
    after_freeze = workspace.refresh_frame(timeout_s=1.0)
    workspace.resume()
    assert workspace.state is WorkspaceState.RUNNING
    assert frozen is not None
    assert after_freeze == frozen
    workspace.stop()
    assert workspace.state is WorkspaceState.IDLE
