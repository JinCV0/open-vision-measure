from dataclasses import replace

import numpy as np
import pytest

from vision_measure.inspection.annotations import NormalizedPoint, ScaleBarTooLong
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.inspection.scale_bar import (
    DEFAULT_SCALE_BAR_STYLE,
    ScaleBarOrientation,
    ScaleBarPreset,
    ScaleBarShape,
    ScaleBarStyle,
    build_scale_bar_layout,
    render_scale_bar,
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


def test_vertical_scale_bar_uses_image_height() -> None:
    style = replace(
        DEFAULT_SCALE_BAR_STYLE,
        orientation=ScaleBarOrientation.VERTICAL,
    )
    layout = build_scale_bar_layout(
        1000,
        1000,
        Calibration(0.1, Unit.MM),
        length=10.0,
        position=NormalizedPoint(0.2, 0.2),
        style=style,
    )
    assert layout.geometry.end.y - layout.geometry.start.y == pytest.approx(100.0)
    assert layout.geometry.end.x == pytest.approx(layout.geometry.start.x)


def test_vertical_bar_too_long_is_rejected() -> None:
    style = replace(
        DEFAULT_SCALE_BAR_STYLE,
        orientation=ScaleBarOrientation.VERTICAL,
    )
    with pytest.raises(ScaleBarTooLong):
        build_scale_bar_layout(
            300,
            200,
            Calibration(0.01, Unit.MM),
            length=10.0,
            position=NormalizedPoint(0.1, 0.1),
            style=style,
        )


def test_segmented_render_keeps_dimensions() -> None:
    image = np.zeros((200, 300, 3), dtype=np.uint8)
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    rendered = render_scale_bar(
        image,
        Calibration(0.1, Unit.MM),
        length=10.0,
        position=NormalizedPoint(0.1, 0.8),
        style=style,
    )
    assert rendered.shape == image.shape
    assert np.count_nonzero(rendered) > 0
    assert np.count_nonzero(image) == 0
