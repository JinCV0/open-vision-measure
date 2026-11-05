import numpy as np

from vision_measure.camera.models import FramePacket
from vision_measure.ui.ai_capture import AiCaptureThread, AiScreenshotDialog
from vision_measure.workspace.controller import Workspace
from vision_measure.workspace.models import SubjectCaptureResult


class FailingExtractor:
    def extract(self, image: np.ndarray) -> np.ndarray:
        raise RuntimeError("boom")


def _subject_result() -> SubjectCaptureResult:
    original = np.full((32, 32, 3), (10, 20, 30), dtype=np.uint8)
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    composite = original.copy()
    composite[:8] = 255
    return SubjectCaptureResult(original, mask, composite)


def test_ai_preview_can_select_cleaned_or_original(qtbot) -> None:
    dialog = AiScreenshotDialog(_subject_result())
    qtbot.addWidget(dialog)

    assert dialog.save_original_button.isEnabled()
    assert dialog.save_cleaned_button.isEnabled()

    dialog.save_cleaned_button.click()

    assert dialog.selected_source == "cleaned"
    assert dialog.result() == dialog.DialogCode.Accepted


def test_ai_preview_disables_cleaned_save_on_fallback(qtbot) -> None:
    original = np.zeros((16, 16, 3), dtype=np.uint8)
    result = SubjectCaptureResult(original, None, original.copy(), "boom")
    dialog = AiScreenshotDialog(result)
    qtbot.addWidget(dialog)

    assert dialog.save_original_button.isEnabled()
    assert not dialog.save_cleaned_button.isEnabled()


def test_ai_capture_thread_produces_fallback_result(qtbot) -> None:
    workspace = Workspace()
    workspace._current = FramePacket(np.zeros((32, 32, 3), dtype=np.uint8), 1)
    thread = AiCaptureThread(
        workspace,
        extractor_factory=FailingExtractor,
    )

    with qtbot.waitSignal(thread.completed, timeout=2000) as emitted:
        thread.start()
    thread.wait(2000)

    result = emitted.args[0]
    assert isinstance(result, SubjectCaptureResult)
    assert result.error == "boom"
    assert result.mask is None
