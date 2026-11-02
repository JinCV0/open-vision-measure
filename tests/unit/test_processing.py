import numpy as np
import pytest

from vision_measure.inspection.processing import (
    ImageSettings,
    InvalidFrame,
    process_frame,
)


def test_brightness_and_contrast_are_deterministic() -> None:
    frame = np.full((4, 5, 3), 100, dtype=np.uint8)
    result = process_frame(frame, ImageSettings(brightness=10, contrast=1.2))
    expected = np.clip(
        (frame.astype(np.float32) - 127.5) * 1.2 + 127.5 + 10, 0, 255
    )
    np.testing.assert_allclose(result, expected.astype(np.uint8))


def test_grayscale_returns_three_channels() -> None:
    frame = np.zeros((3, 4, 3), dtype=np.uint8)
    result = process_frame(frame, ImageSettings(grayscale=True))
    assert result.shape == (3, 4, 3)


def test_rejects_empty_frame() -> None:
    with pytest.raises(InvalidFrame):
        process_frame(np.empty((0, 0, 3), dtype=np.uint8), ImageSettings())
