from pathlib import Path

import numpy as np
import pytest

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.inspection.scale_bar import ScaleBarPreset, scale_bar_preset
from vision_measure.workspace.screenshot import (
    ScreenshotError,
    next_capture_path,
    save_capture,
)


def test_capture_sequence_uses_largest_existing_number(tmp_path: Path) -> None:
    (tmp_path / "capture_0001.png").write_bytes(b"one")
    (tmp_path / "capture_0007.jpg").write_bytes(b"seven")
    assert next_capture_path(tmp_path, ".png").name == "capture_0008.png"


def test_capture_save_supports_unicode_path(tmp_path: Path) -> None:
    path = tmp_path / "截图_0001.png"
    image = np.full((24, 32, 3), 128, dtype=np.uint8)
    saved = save_capture(image, path)
    assert saved == path
    assert path.is_file()


def test_capture_save_accepts_custom_scale_bar_style(tmp_path: Path) -> None:
    path = tmp_path / "styled.png"
    image = np.full((200, 300, 3), 90, dtype=np.uint8)
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)

    save_capture(
        image,
        path,
        calibration=Calibration(0.1, Unit.MM),
        scale_bar_enabled=True,
        scale_bar_position=NormalizedPoint(0.1, 0.8),
        scale_bar_length=10.0,
        scale_bar_style=style,
    )

    assert path.is_file()


def test_styled_capture_requires_fixed_length(tmp_path: Path) -> None:
    with pytest.raises(ScreenshotError, match="fixed scale bar length"):
        save_capture(
            np.full((200, 300, 3), 90, dtype=np.uint8),
            tmp_path / "missing-length.png",
            calibration=Calibration(0.1, Unit.MM),
            scale_bar_enabled=True,
            scale_bar_style=scale_bar_preset(ScaleBarPreset.SEGMENTED),
        )
