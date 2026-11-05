from __future__ import annotations

from typing import cast

import numpy as np


def composite_on_background(
    image: np.ndarray,
    alpha_mask: np.ndarray,
    background: tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
        raise ValueError("image must be a non-empty HxWx3 BGR image")
    if alpha_mask.shape != image.shape[:2]:
        raise ValueError("alpha mask dimensions must match the image")
    alpha = alpha_mask.astype(np.float32) / 255.0
    alpha = alpha[:, :, np.newaxis]
    backdrop = np.asarray(background, dtype=np.float32).reshape(1, 1, 3)
    blended = image.astype(np.float32) * alpha + backdrop * (1.0 - alpha)
    return cast(np.ndarray, np.clip(blended, 0, 255).astype(np.uint8))
