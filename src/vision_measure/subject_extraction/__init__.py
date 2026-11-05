from __future__ import annotations

from typing import Protocol

import numpy as np


class SubjectExtractionError(RuntimeError):
    pass


class ModelUnavailable(SubjectExtractionError):
    pass


class SubjectExtractor(Protocol):
    def extract(self, image: np.ndarray) -> np.ndarray: ...


__all__ = [
    "ModelUnavailable",
    "SubjectExtractionError",
    "SubjectExtractor",
]
