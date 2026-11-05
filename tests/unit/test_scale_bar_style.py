import pytest

from vision_measure.inspection.scale_bar import (
    ScaleBarShape,
    ScaleBarPreset,
    ScaleBarStyle,
    scale_bar_preset,
    scale_bar_style_from_json,
    scale_bar_style_to_json,
)


def test_presets_are_valid_and_distinct() -> None:
    styles = {preset: scale_bar_preset(preset) for preset in ScaleBarPreset}
    assert len(set(styles.values())) == len(ScaleBarPreset)
    assert styles[ScaleBarPreset.SEGMENTED].shape is ScaleBarShape.SEGMENTED
    assert styles[ScaleBarPreset.MATERIAL].line_color == "#356b53"


def test_style_rejects_invalid_color() -> None:
    with pytest.raises(ValueError):
        ScaleBarStyle(line_color="white")


def test_style_rejects_invalid_numeric_range() -> None:
    with pytest.raises(ValueError):
        ScaleBarStyle(line_width=0.5)
    with pytest.raises(ValueError):
        ScaleBarStyle(opacity=1.1)


def test_style_round_trips_json() -> None:
    style = scale_bar_preset(ScaleBarPreset.MATERIAL)
    assert scale_bar_style_from_json(scale_bar_style_to_json(style)) == style
