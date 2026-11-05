import json
from pathlib import Path

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.scale_bar import (
    DEFAULT_SCALE_BAR_STYLE,
    ScaleBarPreset,
    scale_bar_preset,
)
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
    assert preferences.scale_bar_style == DEFAULT_SCALE_BAR_STYLE


def test_v1_preferences_load_default_scale_bar_style(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "scale_bar_position": {"x": 0.2, "y": 0.8},
            }
        ),
        encoding="utf-8",
    )
    assert PreferencesStore(path).load().scale_bar_style == DEFAULT_SCALE_BAR_STYLE


def test_custom_scale_bar_style_round_trips(tmp_path: Path) -> None:
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    path = tmp_path / "preferences.json"
    store = PreferencesStore(path)
    store.save(AppPreferences(scale_bar_style=style))
    assert store.load().scale_bar_style == style
