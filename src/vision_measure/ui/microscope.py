from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from vision_measure.inspection.models import Line, Unit
from vision_measure.ui.panels import CalibrationPanel, MagnificationPanel
from vision_measure.ui.viewport import ImageViewport
from vision_measure.workspace.controller import Workspace


class MicroscopeControls(QObject):
    error_occurred = Signal(str)
    overlay_changed = Signal()

    def __init__(
        self,
        workspace: Workspace,
        magnification_panel: MagnificationPanel,
        calibration_panel: CalibrationPanel,
        viewport: ImageViewport,
    ) -> None:
        super().__init__()
        self.workspace = workspace
        self.magnification_panel = magnification_panel
        self.calibration_panel = calibration_panel
        self.viewport = viewport
        magnification_panel.magnification_changed.connect(self.switch_magnification)
        calibration_panel.calibrate_requested.connect(self.begin_calibration)
        calibration_panel.measure_toggled.connect(self.set_measurement_mode)
        calibration_panel.unit_changed.connect(self.change_calibration_unit)
        calibration_panel.scale_bar_box.toggled.connect(self.prepare_scale_bar_length)
        calibration_panel.scale_bar_length_changed.connect(self.set_scale_bar_length)
        viewport.calibration_finished.connect(self.finish_calibration)
        viewport.measurement_mode_changed.connect(calibration_panel.set_measure_active)

    def begin_calibration(self) -> None:
        self.viewport.set_measurement_mode(False)
        self.calibration_panel.set_measure_active(False)
        self.viewport.set_calibration_mode(True)

    def set_measurement_mode(self, active: bool) -> None:
        if active:
            self.viewport.set_calibration_mode(False)
        self.viewport.set_measurement_mode(active)

    def change_calibration_unit(self, unit: object) -> None:
        if not isinstance(unit, Unit):
            return
        calibration = self.workspace.current_calibration
        invalidated = calibration is not None and calibration.unit is not unit
        if invalidated:
            self.workspace.clear_current_calibration()
        self.sync()
        if invalidated:
            self.magnification_panel.set_calibration(
                None,
                "未标定 · 请重新标定",
            )
        self.overlay_changed.emit()

    def finish_calibration(self, line: object) -> None:
        self.viewport.set_calibration_mode(False)
        if not isinstance(line, Line):
            return
        try:
            self.workspace.set_reference(
                line,
                self.calibration_panel.reference_length_spin.value(),
                self.calibration_panel.selected_unit(),
            )
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return
        self.sync()
        self.overlay_changed.emit()

    def switch_magnification(self, name: str) -> None:
        self.viewport.set_calibration_mode(False)
        self.viewport.set_measurement_mode(False)
        self.calibration_panel.set_measure_active(False)
        self.workspace.set_magnification(name)
        self.sync()
        self.overlay_changed.emit()

    def set_scale_bar_length(self, length: float) -> None:
        self.workspace.set_scale_bar_length(length)
        self.overlay_changed.emit()

    def prepare_scale_bar_length(self, enabled: bool) -> None:
        if enabled:
            self.workspace.set_scale_bar_length(
                self.calibration_panel.scale_bar_length_spin.value()
            )

    def sync(self) -> None:
        current = self.workspace.current_magnification
        names = tuple(profile.name for profile in self.workspace.projects.magnifications)
        self.magnification_panel.set_profiles(names, current)
        calibration = self.workspace.current_calibration
        self.magnification_panel.set_calibration(calibration)
        if calibration is not None:
            self.calibration_panel.set_unit(calibration.unit)
        self.calibration_panel.set_scale_bar_unit(
            calibration.unit if calibration is not None else self.calibration_panel.selected_unit()
        )
        self.calibration_panel.set_scale_bar_length(self.workspace.current_scale_bar_length)
