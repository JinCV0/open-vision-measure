from pathlib import Path

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.workspace.preferences import AppPreferences, PreferencesStore


def test_preferences_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    store = PreferencesStore(path)
    expected = AppPreferences(
        screenshot_directory=tmp_path / "captures",
        screenshot_extension=".jpg",
        scale_bar_enabled=True,
        scale_bar_position=NormalizedPoint(0.22, 0.81),
    )
    store.save(expected)
    assert store.load() == expected


def test_missing_preferences_use_lower_left_scale_bar(tmp_path: Path) -> None:
    preferences = PreferencesStore(tmp_path / "missing.json").load()
    assert preferences.screenshot_directory is None
    assert preferences.scale_bar_position == NormalizedPoint(0.04, 0.92)
