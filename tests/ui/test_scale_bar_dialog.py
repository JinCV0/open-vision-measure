import numpy as np

from vision_measure.inspection.annotations import DEFAULT_SCALE_BAR_POSITION, NormalizedPoint
from vision_measure.inspection.models import Unit
from vision_measure.inspection.scale_bar import (
    DEFAULT_SCALE_BAR_STYLE,
    ScaleBarPreset,
    ScaleBarShape,
)
from vision_measure.ui.scale_bar_dialog import ScaleBarDialog


def _dialog(image: np.ndarray | None = None) -> ScaleBarDialog:
    return ScaleBarDialog(
        image=image,
        unit=Unit.UM,
        length=10.0,
        style=DEFAULT_SCALE_BAR_STYLE,
        position=DEFAULT_SCALE_BAR_POSITION,
    )


def test_preset_changes_dialog_style(qtbot) -> None:
    dialog = _dialog()
    qtbot.addWidget(dialog)
    index = dialog.preset_combo.findData(ScaleBarPreset.SEGMENTED)
    dialog.preset_combo.setCurrentIndex(index)
    assert dialog.selected_style().shape is ScaleBarShape.SEGMENTED


def test_position_grid_updates_selected_position(qtbot) -> None:
    dialog = _dialog()
    qtbot.addWidget(dialog)
    dialog.position_buttons["right-top"].click()
    position = dialog.selected_position()
    assert position.x > 0.8
    assert position.y < 0.2


def test_detail_controls_update_style(qtbot) -> None:
    dialog = _dialog(np.zeros((180, 320, 3), dtype=np.uint8))
    qtbot.addWidget(dialog)
    dialog.line_width_spin.setValue(7)
    dialog.show_label_box.setChecked(False)
    style = dialog.selected_style()
    assert style.line_width == 7.0
    assert style.show_label is False


def test_dialog_returns_length_and_unit(qtbot) -> None:
    dialog = _dialog()
    qtbot.addWidget(dialog)
    dialog.length_spin.setValue(25.0)
    assert dialog.selected_length() == 25.0
    assert dialog.selected_unit() is Unit.UM


def test_apply_accepts_dialog(qtbot) -> None:
    dialog = _dialog()
    qtbot.addWidget(dialog)
    dialog.apply_button.click()
    assert dialog.result() == dialog.DialogCode.Accepted


def test_reset_restores_defaults(qtbot) -> None:
    dialog = _dialog()
    qtbot.addWidget(dialog)
    dialog.position_buttons["right-middle"].click()
    dialog.line_width_spin.setValue(9)
    dialog.reset_button.click()
    assert dialog.selected_style() == DEFAULT_SCALE_BAR_STYLE
    assert dialog.selected_position() == NormalizedPoint(0.04, 0.92)
