from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from vision_measure.inspection.annotations import DEFAULT_SCALE_BAR_POSITION, NormalizedPoint
from vision_measure.inspection.models import Unit
from vision_measure.inspection.scale_bar import (
    DEFAULT_SCALE_BAR_STYLE,
    ScaleBarBackground,
    ScaleBarLabelPosition,
    ScaleBarOrientation,
    ScaleBarPreset,
    ScaleBarShape,
    ScaleBarStyle,
    scale_bar_preset,
)
from vision_measure.ui.theme import configure_form_layout

_PRESET_LABELS = {
    ScaleBarPreset.MINIMAL: "简洁线",
    ScaleBarPreset.SCIENTIFIC: "科研描边",
    ScaleBarPreset.SEGMENTED: "分段标尺",
    ScaleBarPreset.MATERIAL: "Material 绿",
    ScaleBarPreset.COMPACT: "紧凑括号",
}

_POSITION_LABELS = {
    "left-top": "左上",
    "center-top": "上",
    "right-top": "右上",
    "left-middle": "左",
    "center-middle": "中",
    "right-middle": "右",
    "left-bottom": "左下",
    "center-bottom": "下",
    "right-bottom": "右下",
}

_POSITION_VALUES = {
    "left-top": NormalizedPoint(0.04, 0.08),
    "center-top": NormalizedPoint(0.5, 0.08),
    "right-top": NormalizedPoint(0.96, 0.08),
    "left-middle": NormalizedPoint(0.04, 0.5),
    "center-middle": NormalizedPoint(0.5, 0.5),
    "right-middle": NormalizedPoint(0.96, 0.5),
    "left-bottom": NormalizedPoint(0.04, 0.92),
    "center-bottom": NormalizedPoint(0.5, 0.92),
    "right-bottom": NormalizedPoint(0.96, 0.92),
}


class ScaleBarSettingsForm(QWidget):
    changed = Signal()

    def __init__(
        self,
        unit: Unit,
        length: float,
        style: ScaleBarStyle,
        position: NormalizedPoint,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._unit = unit
        self._position = position
        self._colors = {
            "line_color": style.line_color,
            "outline_color": style.outline_color,
            "label_color": style.label_color,
            "background_color": style.background_color,
        }
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_preset_group())
        layout.addWidget(self._build_shape_group())
        layout.addWidget(self._build_size_group())
        layout.addWidget(self._build_label_group())
        layout.addWidget(self._build_background_group())
        layout.addWidget(self._build_color_group())
        layout.addWidget(self._build_position_group())
        layout.addStretch(1)
        self.length_spin.setValue(length)
        self.set_style(style)
        self.set_position(position)

    def _group(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        group = QGroupBox(title)
        form = QFormLayout(group)
        configure_form_layout(form)
        return group, form

    def _build_preset_group(self) -> QGroupBox:
        group, form = self._group("预设")
        self.preset_combo = QComboBox()
        for preset, label in _PRESET_LABELS.items():
            self.preset_combo.addItem(label, preset)
        self.preset_combo.addItem("自定义", None)
        form.addRow("样式", self.preset_combo)
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        return group

    def _build_shape_group(self) -> QGroupBox:
        group, form = self._group("形态")
        self.shape_combo = QComboBox()
        for label, shape in (
            ("标准线", ScaleBarShape.LINE),
            ("双端刻度", ScaleBarShape.TICKS),
            ("分段色块", ScaleBarShape.SEGMENTED),
            ("括号式", ScaleBarShape.BRACKET),
        ):
            self.shape_combo.addItem(label, shape)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("水平", ScaleBarOrientation.HORIZONTAL)
        self.orientation_combo.addItem("垂直", ScaleBarOrientation.VERTICAL)
        form.addRow("形状", self.shape_combo)
        form.addRow("方向", self.orientation_combo)
        self.shape_combo.currentIndexChanged.connect(self._detail_changed)
        self.orientation_combo.currentIndexChanged.connect(self._detail_changed)
        return group

    def _build_size_group(self) -> QGroupBox:
        group, form = self._group("尺寸")
        self.length_spin = self._double_spin(
            0.001,
            1_000_000,
            4,
            f" {self._unit.display_name}",
        )
        self.line_width_spin = self._double_spin(1, 20, 1, " px")
        self.tick_length_spin = self._double_spin(0, 80, 1, " px")
        self.label_size_spin = self._double_spin(8, 96, 1, " px")
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(2, 12)
        form.addRow("物理长度", self.length_spin)
        form.addRow("线宽", self.line_width_spin)
        form.addRow("刻度长度", self.tick_length_spin)
        form.addRow("标签字号", self.label_size_spin)
        form.addRow("分段数量", self.segments_spin)
        for control in (
            self.length_spin,
            self.line_width_spin,
            self.tick_length_spin,
            self.label_size_spin,
            self.segments_spin,
        ):
            control.valueChanged.connect(self._detail_changed)
        return group

    def _build_label_group(self) -> QGroupBox:
        group, form = self._group("标签")
        self.show_label_box = QCheckBox("显示标签")
        self.show_outline_box = QCheckBox("文字描边")
        self.label_position_combo = QComboBox()
        self.label_position_combo.addItem("上方", ScaleBarLabelPosition.ABOVE)
        self.label_position_combo.addItem("下方", ScaleBarLabelPosition.BELOW)
        form.addRow(self.show_label_box)
        form.addRow(self.show_outline_box)
        form.addRow("位置", self.label_position_combo)
        self.show_label_box.toggled.connect(self._detail_changed)
        self.show_outline_box.toggled.connect(self._detail_changed)
        self.label_position_combo.currentIndexChanged.connect(self._detail_changed)
        return group

    def _build_background_group(self) -> QGroupBox:
        group, form = self._group("背景")
        self.background_combo = QComboBox()
        self.background_combo.addItem("无", ScaleBarBackground.NONE)
        self.background_combo.addItem("半透明", ScaleBarBackground.TRANSLUCENT)
        self.background_combo.addItem("实色", ScaleBarBackground.SOLID)
        self.opacity_spin = self._double_spin(0, 1, 2, "", step=0.05)
        self.background_opacity_spin = self._double_spin(0, 1, 2, "", step=0.05)
        form.addRow("样式", self.background_combo)
        form.addRow("整体透明度", self.opacity_spin)
        form.addRow("底板透明度", self.background_opacity_spin)
        self.background_combo.currentIndexChanged.connect(self._detail_changed)
        self.opacity_spin.valueChanged.connect(self._detail_changed)
        self.background_opacity_spin.valueChanged.connect(self._detail_changed)
        return group

    def _build_color_group(self) -> QGroupBox:
        group, form = self._group("颜色")
        self.color_buttons: dict[str, QPushButton] = {}
        for key, label in (
            ("line_color", "线条"),
            ("outline_color", "描边"),
            ("label_color", "标签"),
            ("background_color", "底板"),
        ):
            button = QPushButton()
            button.setAccessibleName(f"{label}颜色")
            button.clicked.connect(lambda _checked=False, field=key: self._choose_color(field))
            self.color_buttons[key] = button
            form.addRow(label, button)
        return group

    def _build_position_group(self) -> QGroupBox:
        group = QGroupBox("位置")
        grid = QGridLayout(group)
        grid.setContentsMargins(20, 40, 20, 20)
        grid.setSpacing(8)
        self.position_buttons: dict[str, QPushButton] = {}
        for index, (key, label) in enumerate(_POSITION_LABELS.items()):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setAccessibleName(f"位置：{label}")
            button.clicked.connect(
                lambda _checked=False, position_key=key: self._set_position_by_key(position_key)
            )
            self.position_buttons[key] = button
            grid.addWidget(button, index // 3, index % 3)
        return group

    @staticmethod
    def _double_spin(
        minimum: float,
        maximum: float,
        decimals: int,
        suffix: str,
        step: float = 1.0,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        return spin

    def _color_icon(self, color: str) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    def _set_color_button(self, field: str, color: str) -> None:
        button = self.color_buttons[field]
        button.setText(color)
        button.setIcon(self._color_icon(color))
        self._colors[field] = color

    def _choose_color(self, field: str) -> None:
        color = QColorDialog.getColor(QColor(self._colors[field]), self, "选择颜色")
        if not color.isValid():
            return
        self._set_color_button(field, color.name())
        self._detail_changed()

    def set_style(self, style: ScaleBarStyle) -> None:
        self._updating = True
        try:
            self.shape_combo.setCurrentIndex(self.shape_combo.findData(style.shape))
            self.orientation_combo.setCurrentIndex(
                self.orientation_combo.findData(style.orientation)
            )
            self.label_position_combo.setCurrentIndex(
                self.label_position_combo.findData(style.label_position)
            )
            self.background_combo.setCurrentIndex(self.background_combo.findData(style.background))
            self.line_width_spin.setValue(style.line_width)
            self.tick_length_spin.setValue(style.tick_length)
            self.label_size_spin.setValue(style.label_size)
            self.show_label_box.setChecked(style.show_label)
            self.show_outline_box.setChecked(style.show_outline)
            self.opacity_spin.setValue(style.opacity)
            self.background_opacity_spin.setValue(style.background_opacity)
            self.segments_spin.setValue(style.segments)
            self._colors = {
                "line_color": style.line_color,
                "outline_color": style.outline_color,
                "label_color": style.label_color,
                "background_color": style.background_color,
            }
            for field, color in self._colors.items():
                self._set_color_button(field, color)
            for preset in ScaleBarPreset:
                if scale_bar_preset(preset) == style:
                    self.preset_combo.setCurrentIndex(self.preset_combo.findData(preset))
                    break
            else:
                self.preset_combo.setCurrentIndex(self.preset_combo.findData(None))
        finally:
            self._updating = False
        self._update_enabled_states()

    def _preset_changed(self) -> None:
        if self._updating:
            return
        value = self.preset_combo.currentData()
        if value is None:
            return
        self.set_style(scale_bar_preset(ScaleBarPreset(str(value))))
        self.changed.emit()

    def _detail_changed(self) -> None:
        if self._updating:
            return
        self._updating = True
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(None))
        self._updating = False
        self._update_enabled_states()
        self.changed.emit()

    def _update_enabled_states(self) -> None:
        shape = ScaleBarShape(str(self.shape_combo.currentData()))
        self.segments_spin.setEnabled(shape is ScaleBarShape.SEGMENTED)
        self.show_label_box.setEnabled(True)
        self.label_position_combo.setEnabled(self.show_label_box.isChecked())
        self.show_outline_box.setEnabled(self.show_label_box.isChecked())

    def selected_style(self) -> ScaleBarStyle:
        return ScaleBarStyle(
            shape=ScaleBarShape(str(self.shape_combo.currentData())),
            orientation=ScaleBarOrientation(str(self.orientation_combo.currentData())),
            label_position=ScaleBarLabelPosition(str(self.label_position_combo.currentData())),
            background=ScaleBarBackground(str(self.background_combo.currentData())),
            line_color=self._colors["line_color"],
            outline_color=self._colors["outline_color"],
            label_color=self._colors["label_color"],
            background_color=self._colors["background_color"],
            opacity=self.opacity_spin.value(),
            background_opacity=self.background_opacity_spin.value(),
            line_width=self.line_width_spin.value(),
            tick_length=self.tick_length_spin.value(),
            label_size=self.label_size_spin.value(),
            show_outline=self.show_outline_box.isChecked(),
            show_label=self.show_label_box.isChecked(),
            segments=self.segments_spin.value(),
        )

    def length(self) -> float:
        return self.length_spin.value()

    def unit(self) -> Unit:
        return self._unit

    def position(self) -> NormalizedPoint:
        return self._position

    def set_position(self, position: NormalizedPoint) -> None:
        self._position = position
        for key, button in self.position_buttons.items():
            value = _POSITION_VALUES[key]
            button.setChecked(abs(value.x - position.x) < 1e-9 and abs(value.y - position.y) < 1e-9)

    def _set_position_by_key(self, key: str) -> None:
        self.set_position(_POSITION_VALUES[key])
        self.changed.emit()

    def reset(self) -> None:
        self.length_spin.setValue(10.0)
        self.set_style(DEFAULT_SCALE_BAR_STYLE)
        self.set_position(DEFAULT_SCALE_BAR_POSITION)
        self.changed.emit()
