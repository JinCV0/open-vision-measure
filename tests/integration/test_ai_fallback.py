import cv2
import numpy as np

from vision_measure.camera.models import FramePacket
from vision_measure.workspace.controller import Workspace


class ExplodingExtractor:
    def extract(self, image: np.ndarray) -> np.ndarray:
        raise RuntimeError("boom")


class FixedMaskExtractor:
    def extract(self, image: np.ndarray) -> np.ndarray:
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        mask[16:48, 16:48] = 255
        return mask


def test_ai_failure_falls_back_to_original() -> None:
    image = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(image, 1)

    result = workspace.capture_with_subject(ExplodingExtractor())

    assert result.shape == (64, 64, 3)
    np.testing.assert_array_equal(result, image)


def test_ai_success_composites_subject_on_white() -> None:
    image = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(image, 1)

    result = workspace.capture_with_subject(FixedMaskExtractor())

    np.testing.assert_array_equal(result[0, 0], (255, 255, 255))
    np.testing.assert_array_equal(result[32, 32], (12, 34, 56))


def test_prepared_capture_keeps_original_mask_and_composite() -> None:
    image = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(image, 1)

    result = workspace.prepare_subject_capture(FixedMaskExtractor())

    np.testing.assert_array_equal(result.original, image)
    assert result.mask is not None
    assert result.mask[32, 32] == 255
    np.testing.assert_array_equal(result.composite[0, 0], (255, 255, 255))
    assert result.error is None


def test_prepared_capture_reports_fallback_reason() -> None:
    image = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(image, 1)

    result = workspace.prepare_subject_capture(ExplodingExtractor())

    np.testing.assert_array_equal(result.original, image)
    assert result.mask is None
    np.testing.assert_array_equal(result.composite, image)
    assert result.error == "boom"


def test_ai_capture_can_save_original_or_cleaned(tmp_path) -> None:
    image = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(image, 1)
    result = workspace.prepare_subject_capture(FixedMaskExtractor())

    original_path = tmp_path / "original.png"
    cleaned_path = tmp_path / "cleaned.png"
    workspace.save_subject_capture(result, original_path, source="original")
    workspace.save_subject_capture(result, cleaned_path, source="cleaned")

    original = cv2.imread(str(original_path))
    cleaned = cv2.imread(str(cleaned_path))
    assert original is not None
    assert cleaned is not None
    np.testing.assert_array_equal(original[0, 0], (12, 34, 56))
    np.testing.assert_array_equal(cleaned[0, 0], (255, 255, 255))


def test_prepare_capture_uses_frozen_source_frame() -> None:
    first = np.full((64, 64, 3), (12, 34, 56), dtype=np.uint8)
    second = np.full((64, 64, 3), (90, 80, 70), dtype=np.uint8)
    workspace = Workspace()
    workspace._current = FramePacket(first, 1)
    frozen = workspace.display_frame
    assert frozen is not None
    workspace._current = FramePacket(second, 2)

    result = workspace.prepare_subject_capture(
        FixedMaskExtractor(),
        image=frozen,
    )

    np.testing.assert_array_equal(result.original, first)
