from __future__ import annotations

import cv2
import numpy as np


class InvalidMask(ValueError):
    pass


def cleanup_mask(
    alpha_mask: np.ndarray,
    min_component_area: int = 20,
    fill_holes: bool = True,
) -> np.ndarray:
    if alpha_mask.ndim != 2 or alpha_mask.size == 0:
        raise InvalidMask("alpha mask must be a non-empty 2D array")
    if min_component_area < 1:
        raise ValueError("min_component_area must be positive")

    binary = (alpha_mask > 0).astype(np.uint8)
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary,
        connectivity=8,
    )
    cleaned = np.zeros_like(binary)
    for label in range(1, component_count):
        if stats[label, cv2.CC_STAT_AREA] >= min_component_area:
            cleaned[labels == label] = 1

    if fill_holes:
        holes = (cleaned == 0).astype(np.uint8)
        hole_count, hole_labels, _, _ = cv2.connectedComponentsWithStats(
            holes,
            connectivity=8,
        )
        border_labels = np.unique(
            np.concatenate(
                (
                    hole_labels[0, :],
                    hole_labels[-1, :],
                    hole_labels[:, 0],
                    hole_labels[:, -1],
                )
            )
        )
        for label in range(1, hole_count):
            if label not in border_labels:
                cleaned[hole_labels == label] = 1

    return (cleaned * 255).astype(np.uint8)
