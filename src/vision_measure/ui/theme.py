from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QFormLayout, QLayout, QWidget

ASSET_DIR = Path(__file__).with_name("assets")


@dataclass(frozen=True, slots=True)
class MaterialPalette:
    surface: str
    card: str
    surface_variant: str
    text_primary: str
    text_secondary: str
    primary: str
    on_primary: str
    primary_hover: str
    primary_pressed: str
    primary_container: str
    on_primary_container: str
    container_hover: str
    container_pressed: str
    outline: str
    outline_variant: str
    focus: str
    error: str
    on_error: str


_LIGHT = MaterialPalette(
    surface="#f7f4ee",
    card="#fffbf5",
    surface_variant="#ece7de",
    text_primary="#1e201b",
    text_secondary="#5b6056",
    primary="#356b53",
    on_primary="#ffffff",
    primary_hover="#2b5b46",
    primary_pressed="#214a38",
    primary_container="#d3e8dc",
    on_primary_container="#0f3828",
    container_hover="#c6dfd1",
    container_pressed="#b8d6c5",
    outline="#7a7f74",
    outline_variant="#d7d8cf",
    focus="#1f6f4d",
    error="#ba1a1a",
    on_error="#ffffff",
)

_DARK = MaterialPalette(
    surface="#10140f",
    card="#1b2019",
    surface_variant="#262c23",
    text_primary="#e3e5dc",
    text_secondary="#bec3b8",
    primary="#9cd3b6",
    on_primary="#003824",
    primary_hover="#b2dfc6",
    primary_pressed="#c4ead4",
    primary_container="#214c37",
    on_primary_container="#c6efda",
    container_hover="#295c44",
    container_pressed="#30684e",
    outline="#8a9186",
    outline_variant="#3f463f",
    focus="#9cd3b6",
    error="#ffb4ab",
    on_error="#690005",
)


def material_palette(dark: bool) -> MaterialPalette:
    return _DARK if dark else _LIGHT


def viewport_background(dark: bool) -> str:
    return "#0d120e" if dark else "#20271f"


def contrast_ratio(first: str, second: str) -> float:
    def luminance(value: str) -> float:
        color = QColor(value)
        channels = (color.redF(), color.greenF(), color.blueF())
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def set_material_property(widget: QWidget, name: str, value: object) -> None:
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def configure_card_layout(layout: QLayout) -> None:
    layout.setContentsMargins(20, 8, 20, 20)
    layout.setSpacing(12)


def configure_form_layout(form: QFormLayout) -> None:
    form.setContentsMargins(20, 8, 20, 20)
    form.setHorizontalSpacing(16)
    form.setVerticalSpacing(12)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)


def _resolve(template: str, palette: MaterialPalette, dark: bool) -> str:
    values = {
        "surface": palette.surface,
        "card": palette.card,
        "surface_variant": palette.surface_variant,
        "text_primary": palette.text_primary,
        "text_secondary": palette.text_secondary,
        "primary": palette.primary,
        "on_primary": palette.on_primary,
        "primary_hover": palette.primary_hover,
        "primary_pressed": palette.primary_pressed,
        "primary_container": palette.primary_container,
        "on_primary_container": palette.on_primary_container,
        "container_hover": palette.container_hover,
        "container_pressed": palette.container_pressed,
        "outline": palette.outline,
        "outline_variant": palette.outline_variant,
        "focus": palette.focus,
        "error": palette.error,
        "on_error": palette.on_error,
        "check_icon": (ASSET_DIR / ("check_dark.svg" if dark else "check.svg")).as_posix(),
        "chevron_down_icon": (
            ASSET_DIR / ("chevron_down_light.svg" if dark else "chevron_down.svg")
        ).as_posix(),
        "chevron_up_icon": (
            ASSET_DIR / ("chevron_up_light.svg" if dark else "chevron_up.svg")
        ).as_posix(),
    }
    result = template
    for name, value in values.items():
        result = result.replace(f"@{{{name}}}", value)
    if "@{" in result:
        raise ValueError("unresolved material theme token")
    return result


class MaterialThemeManager(QObject):
    def __init__(
        self,
        app: QApplication,
        dark: bool | None = None,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._dark = dark
        self.apply()
        hints = QGuiApplication.styleHints()
        signal = getattr(hints, "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(self._system_scheme_changed)

    @property
    def dark(self) -> bool:
        if self._dark is not None:
            return self._dark
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark

    @property
    def palette(self) -> MaterialPalette:
        return material_palette(self.dark)

    @property
    def style_sheet(self) -> str:
        template = (ASSET_DIR / "material.qss").read_text(encoding="utf-8")
        return _resolve(template, self.palette, self.dark)

    def apply(self) -> None:
        palette = self.palette
        qt_palette = QPalette()
        roles = (
            (QPalette.ColorRole.Window, palette.surface),
            (QPalette.ColorRole.WindowText, palette.text_primary),
            (QPalette.ColorRole.Base, palette.card),
            (QPalette.ColorRole.AlternateBase, palette.surface_variant),
            (QPalette.ColorRole.Text, palette.text_primary),
            (QPalette.ColorRole.Button, palette.primary_container),
            (QPalette.ColorRole.ButtonText, palette.on_primary_container),
            (QPalette.ColorRole.Highlight, palette.primary),
            (QPalette.ColorRole.HighlightedText, palette.on_primary),
            (QPalette.ColorRole.Link, palette.primary),
            (QPalette.ColorRole.ToolTipBase, palette.text_primary),
            (QPalette.ColorRole.ToolTipText, palette.surface),
        )
        for role, color in roles:
            qt_palette.setColor(role, QColor(color))
        qt_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(palette.outline),
        )
        qt_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(palette.outline),
        )
        if hasattr(QPalette.ColorRole, "PlaceholderText"):
            qt_palette.setColor(
                QPalette.ColorRole.PlaceholderText,
                QColor(palette.text_secondary),
            )
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        families = set(QFontDatabase.families())
        if "Segoe UI Variable Text" in families:
            font.setFamily("Segoe UI Variable Text")
        elif "Segoe UI" in families:
            font.setFamily("Segoe UI")
        font.setPixelSize(14)
        self._app.setFont(font)
        self._app.setPalette(qt_palette)
        self._app.setStyleSheet(self.style_sheet)
        for widget in self._app.allWidgets():
            widget.update()

    def _system_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if self._dark is None:
            self.apply()
