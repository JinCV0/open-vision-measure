import numpy as np
import pytest

from vision_measure.subject_extraction.mask import InvalidMask, cleanup_mask


def test_cleanup_mask_drops_far_away_fragments_and_fills_holes() -> None:
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    mask[10:20, 10:20] = 0
    mask[50:52, 50:52] = 255

    cleaned = cleanup_mask(mask, min_component_area=20, fill_holes=True)

    assert cleaned[50, 50] == 0
    assert cleaned[15, 15] == 255


def test_cleanup_mask_can_preserve_interior_holes() -> None:
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[4:24, 4:24] = 255
    mask[10:18, 10:18] = 0

    cleaned = cleanup_mask(mask, min_component_area=20, fill_holes=False)

    assert cleaned[12, 12] == 0


def test_cleanup_mask_rejects_non_binary_shape() -> None:
    with pytest.raises(InvalidMask):
        cleanup_mask(np.zeros((16, 16, 3), dtype=np.uint8))
