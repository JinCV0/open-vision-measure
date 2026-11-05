from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from vision_measure.subject_extraction import (
    ModelUnavailable,
    SubjectExtractionError,
)


class RemBgExtractor:
    def __init__(
        self,
        model: str = "birefnet-general",
        providers: tuple[str, ...] = ("CPUExecutionProvider",),
    ) -> None:
        try:
            rembg: Any = importlib.import_module("rembg")
            sessions: Any = importlib.import_module("rembg.sessions")
        except ImportError as exc:
            raise SubjectExtractionError("rembg is not installed") from exc

        self._rembg = rembg
        sessions_class = sessions.sessions_class
        session_class = next(
            (item for item in sessions_class if item.name() == model),
            None,
        )
        if session_class is None:
            raise ModelUnavailable(f"unknown rembg model: {model}")
        model_path = Path(session_class.model_dir()) / f"{model}.onnx"
        if not model_path.is_file():
            raise ModelUnavailable(f"model is not installed: {model_path}")
        try:
            self._session = rembg.new_session(model, providers=list(providers))
        except Exception as exc:
            raise SubjectExtractionError(f"cannot load model: {model}") from exc

    def extract(self, image: np.ndarray) -> np.ndarray:
        if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
            raise ValueError("image must be a non-empty HxWx3 BGR image")
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            result = self._rembg.remove(rgb, session=self._session, only_mask=True)
        except Exception as exc:
            raise SubjectExtractionError("subject extraction failed") from exc
        mask = np.asarray(result, dtype=np.uint8)
        if mask.ndim != 2 or mask.shape != image.shape[:2]:
            raise SubjectExtractionError("extractor returned an invalid mask")
        return mask
