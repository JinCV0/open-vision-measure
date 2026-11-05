from PySide6.QtGui import QPalette

from vision_measure.ui.theme import (
    MaterialThemeManager,
    contrast_ratio,
    material_palette,
)


def test_material_palettes_meet_text_contrast_targets() -> None:
    for dark in (False, True):
        palette = material_palette(dark)
        assert contrast_ratio(palette.text_primary, palette.surface) >= 4.5
        assert contrast_ratio(palette.text_secondary, palette.card) >= 4.5
        assert contrast_ratio(palette.on_primary, palette.primary) >= 4.5


def test_theme_manager_applies_resolved_palette_and_stylesheet(qapp) -> None:
    previous_sheet = qapp.styleSheet()
    previous_palette = qapp.palette()
    try:
        manager = MaterialThemeManager(qapp, dark=False)
        assert "@{" not in manager.style_sheet
        assert qapp.styleSheet() == manager.style_sheet
        assert qapp.palette().color(QPalette.ColorRole.Window).name() == manager.palette.surface
    finally:
        qapp.setStyleSheet(previous_sheet)
        qapp.setPalette(previous_palette)
