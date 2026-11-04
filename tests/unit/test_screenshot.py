from pathlib import Path

import numpy as np

from vision_measure.workspace.screenshot import next_capture_path, save_capture


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
