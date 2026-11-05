from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QWidget

from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.scale_bar import ScaleBarStyle
from vision_measure.ui.panels import CalibrationPanel
from vision_measure.ui.scale_bar_dialog import ScaleBarDialog
from vision_measure.workspace.controller import Workspace
from vision_measure.workspace.preferences import AppPreferences


class ScaleBarSettingsController(QObject):
    applied = Signal(object, float, object)

    def __init__(
        self,
        workspace: Workspace,
        panel: CalibrationPanel,
        parent: QWidget,
        preferences: Callable[[], AppPreferences],
        set_preferences: Callable[[AppPreferences], None],
    ) -> None:
        super().__init__()
        self._workspace = workspace
        self._panel = panel
        self._parent = parent
        self._preferences = preferences
        self._set_preferences = set_preferences
        panel.scale_bar_settings_requested.connect(self.open)

    def open(self) -> None:
        calibration = self._workspace.current_calibration
        if calibration is None:
            return
        preferences = self._preferences()
        dialog = ScaleBarDialog(
            image=self._workspace.display_frame,
            unit=calibration.unit,
            length=self._workspace.current_scale_bar_length or 10.0,
            style=preferences.scale_bar_style,
            position=preferences.scale_bar_position,
            calibration=calibration,
            parent=self._parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.apply(
            dialog.selected_style(),
            dialog.selected_length(),
            dialog.selected_position(),
        )

    def apply(
        self,
        style: ScaleBarStyle,
        length: float,
        position: NormalizedPoint,
    ) -> None:
        self._workspace.set_scale_bar_length(length)
        self._set_preferences(
            replace(
                self._preferences(),
                scale_bar_enabled=True,
                scale_bar_position=position,
                scale_bar_style=style,
            )
        )
        self.applied.emit(style, length, position)
