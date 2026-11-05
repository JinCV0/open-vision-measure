from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from vision_measure.inspection.annotations import (
    NormalizedPoint,
    ScaleBarTooLong,
)
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.inspection.scale_bar import ScaleBarStyle
from vision_measure.ui.scale_bar_form import ScaleBarSettingsForm
from vision_measure.ui.scale_bar_preview import ScaleBarPreview
from vision_measure.ui.theme import set_material_property


class ScaleBarDialog(QDialog):
    def __init__(
        self,
        image: np.ndarray | None,
        unit: Unit,
        length: float,
        style: ScaleBarStyle,
        position: NormalizedPoint,
        calibration: Calibration | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("比例尺设置")
        self.setModal(True)
        self.resize(1120, 760)
        self._image = image
        self._calibration = calibration or Calibration(0.1, unit)
        self._build_ui(unit, length, style, position)
        self._update_preview()

    def _build_ui(
        self,
        unit: Unit,
        length: float,
        style: ScaleBarStyle,
        position: NormalizedPoint,
    ) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(12)
        body = QHBoxLayout()
        body.setSpacing(16)

        preview_card = QFrame()
        preview_card.setObjectName("PreviewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        self.preview = ScaleBarPreview()
        preview_layout.addWidget(self.preview)
        body.addWidget(preview_card, 1)

        self.form = ScaleBarSettingsForm(unit, length, style, position)
        self.form.changed.connect(self._update_preview)
        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.form)
        scroll.setMinimumWidth(390)
        scroll.setMaximumWidth(440)
        body.addWidget(scroll)
        root.addLayout(body, 1)

        self.validation_label = QLabel()
        set_material_property(self.validation_label, "materialSeverity", "danger")
        self.validation_label.hide()
        root.addWidget(self.validation_label)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.reset_button = QPushButton("恢复默认")
        self.cancel_button = QPushButton("取消")
        self.apply_button = QPushButton("应用")
        set_material_property(self.reset_button, "materialAppearance", "text")
        set_material_property(self.cancel_button, "materialAppearance", "text")
        set_material_property(self.apply_button, "materialAppearance", "primary")
        footer.addWidget(self.reset_button)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.apply_button)
        root.addLayout(footer)

        self.reset_button.clicked.connect(self._reset)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self._apply)

        self.preset_combo = self.form.preset_combo
        self.position_buttons = self.form.position_buttons
        self.line_width_spin = self.form.line_width_spin
        self.show_label_box = self.form.show_label_box
        self.length_spin = self.form.length_spin

    def _update_preview(self) -> None:
        try:
            style = self.form.selected_style()
            self.preview.set_state(
                self._image,
                self._calibration,
                self.form.length(),
                self.form.position(),
                style,
            )
        except ScaleBarTooLong:
            self.validation_label.setText("比例尺超出画面")
            self.validation_label.show()
            self.apply_button.setEnabled(False)
            return
        except ValueError as exc:
            self.validation_label.setText(str(exc))
            self.validation_label.show()
            self.apply_button.setEnabled(False)
            return
        self.validation_label.hide()
        self.apply_button.setEnabled(True)

    def _reset(self) -> None:
        self.form.reset()
        self._update_preview()

    def _apply(self) -> None:
        try:
            self.form.selected_style()
            self._update_preview()
        except ValueError as exc:
            self.validation_label.setText(str(exc))
            self.validation_label.show()
            return
        if self.apply_button.isEnabled():
            self.accept()

    def selected_style(self) -> ScaleBarStyle:
        return self.form.selected_style()

    def selected_position(self) -> NormalizedPoint:
        return self.form.position()

    def selected_length(self) -> float:
        return self.form.length()

    def selected_unit(self) -> Unit:
        return self.form.unit()
