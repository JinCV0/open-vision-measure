from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vision_measure.camera.backend import CameraSession
from vision_measure.camera.models import CameraDevice
from vision_measure.camera.opencv_backend import OpenCvCameraBackend
from vision_measure.inspection.models import Line, LineMeasurement
from vision_measure.ui.camera_tasks import CameraDiscoveryThread, CameraOpenThread
from vision_measure.ui.panels import (
    CameraControlBar,
    ImagePanel,
    MeasurementPanel,
    ProjectPanel,
)
from vision_measure.ui.viewport import ImageViewport
from vision_measure.workspace.controller import Workspace, WorkspaceState


class MainWindow(QMainWindow):
    def __init__(
        self,
        workspace: Workspace | None = None,
        backend: OpenCvCameraBackend | None = None,
        parent: QWidget | None = None,
        auto_discover: bool = True,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace or Workspace()
        self._backend = backend or OpenCvCameraBackend()
        self._discovery_thread: CameraDiscoveryThread | None = None
        self._open_thread: CameraOpenThread | None = None
        self._last_pump_error: Exception | None = None
        self.setWindowTitle("Open Vision Measure")
        self.resize(1440, 900)
        self._build_ui()
        self._connect_events()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._refresh_preview)
        self._timer.start()
        if auto_discover:
            QTimer.singleShot(0, self._refresh_cameras)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        self.camera_bar = CameraControlBar()
        left.addWidget(self.camera_bar)
        self.viewport = ImageViewport()
        left.addWidget(self.viewport, 1)
        self.measurement_table = self._build_measurement_table()
        left.addWidget(self.measurement_table)
        root.addLayout(left, 1)

        self.image_panel = ImagePanel()
        self.measurement_panel = MeasurementPanel()
        self.project_panel = ProjectPanel()
        controls = QVBoxLayout()
        controls.addWidget(self.image_panel)
        controls.addWidget(self.measurement_panel)
        controls.addWidget(self.project_panel)
        controls.addStretch(1)
        root.addLayout(controls)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Idle")

    @staticmethod
    def _build_measurement_table() -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(("Type", "Pixels", "Physical", "Unit"))
        table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(180)
        return table

    def _connect_events(self) -> None:
        self.camera_bar.refresh_requested.connect(self._refresh_cameras)
        self.camera_bar.start_requested.connect(self._start_camera)
        self.camera_bar.stop_requested.connect(self._stop_camera)
        self.camera_bar.freeze_requested.connect(self._toggle_freeze)
        self.image_panel.settings_changed.connect(self._apply_image_settings)
        self.image_panel.screenshot_requested.connect(self._save_screenshot)
        self.viewport.line_finished.connect(self._add_line)
        self.measurement_panel.calibrate_requested.connect(self._calibrate)
        self.project_panel.save_requested.connect(self._save_project)
        self.project_panel.load_requested.connect(self._load_project)
        self.project_panel.export_requested.connect(self._export_csv)

    def _refresh_cameras(self) -> None:
        if self._discovery_thread is not None and self._discovery_thread.isRunning():
            return
        self.camera_bar.refresh_button.setEnabled(False)
        self.statusBar().showMessage("Discovering cameras...")
        self._discovery_thread = CameraDiscoveryThread(
            self._backend, self.camera_bar.selected_api(), self
        )
        self._discovery_thread.devices_found.connect(self._cameras_found)
        self._discovery_thread.failed.connect(self._camera_error)
        self._discovery_thread.finished.connect(self._discovery_finished)
        self._discovery_thread.start()

    def _discovery_finished(self) -> None:
        self.camera_bar.refresh_button.setEnabled(True)

    def _cameras_found(self, devices: tuple[CameraDevice, ...]) -> None:
        self.camera_bar.set_devices(devices)
        if devices:
            self.statusBar().showMessage(f"Found {len(devices)} camera(s)")
        else:
            self.statusBar().showMessage("No cameras found")

    def _start_camera(self) -> None:
        device = self.camera_bar.selected_device()
        if device is None:
            self._show_error("No camera is selected")
            return
        self.camera_bar.start_button.setEnabled(False)
        self.statusBar().showMessage("Opening camera...")
        self._open_thread = CameraOpenThread(
            self._backend, device, self.camera_bar.capture_config(), self
        )
        self._open_thread.opened.connect(self._camera_opened)
        self._open_thread.failed.connect(self._camera_error)
        self._open_thread.finished.connect(self._open_finished)
        self._open_thread.start()

    def _open_finished(self) -> None:
        self.camera_bar.start_button.setEnabled(True)

    def _camera_opened(self, session: CameraSession) -> None:
        self.workspace.attach_session(session)
        self._last_pump_error = None
        self._update_state()

    def _camera_error(self, message: str) -> None:
        self.statusBar().showMessage("Camera error")
        self.camera_bar.start_button.setEnabled(True)
        self._show_error(message)

    def _stop_camera(self) -> None:
        self.workspace.stop()
        self.viewport.set_frame(None)
        self._update_state()

    def _toggle_freeze(self) -> None:
        if self.workspace.state is WorkspaceState.FROZEN:
            self.workspace.resume()
        else:
            self.workspace.freeze()
        self._update_state()

    def _update_state(self) -> None:
        state = self.workspace.state
        self.camera_bar.set_frozen(state is WorkspaceState.FROZEN)
        self.statusBar().showMessage(state.value.title())

    def _refresh_preview(self) -> None:
        previous_state = self.workspace.state
        self.workspace.refresh_frame(timeout_s=0.0)
        frame = self.workspace.display_frame
        if frame is not None:
            self.viewport.set_frame(frame)
        self.viewport.set_lines(self.workspace.project.lines)
        pump_error = self.workspace.pump_error
        if pump_error is not None and pump_error is not self._last_pump_error:
            self._last_pump_error = pump_error
            self._show_error(str(pump_error))
            self._stop_camera()
        elif previous_state is not self.workspace.state:
            self._update_state()

    def _apply_image_settings(self) -> None:
        self.workspace.set_image_settings(self.image_panel.settings())

    def _add_line(self, line: Line) -> None:
        try:
            measurement = self.workspace.add_line(line)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self._append_measurement(measurement)
        self.viewport.set_lines(self.workspace.project.lines)

    def _append_measurement(self, measurement: LineMeasurement) -> None:
        row = self.measurement_table.rowCount()
        self.measurement_table.insertRow(row)
        values = (
            "Line",
            f"{measurement.pixel_length:.3f}",
            f"{measurement.physical_length:.4f}",
            measurement.unit.value,
        )
        for column, value in enumerate(values):
            self.measurement_table.setItem(row, column, QTableWidgetItem(value))

    def _calibrate(self) -> None:
        if not self.workspace.project.lines:
            self._show_error("Draw a reference line first")
            return
        try:
            self.workspace.set_reference(
                self.workspace.project.lines[-1],
                self.measurement_panel.reference_length_spin.value(),
                self.measurement_panel.selected_unit(),
            )
            self._rebuild_measurement_table()
        except Exception as exc:
            self._show_error(str(exc))

    def _rebuild_measurement_table(self) -> None:
        self.measurement_table.setRowCount(0)
        for measurement in self.workspace.measurements:
            self._append_measurement(measurement)

    def _save_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save screenshot", "capture.png", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            self.workspace.save_display_frame(Path(path))
        except Exception as exc:
            self._show_error(str(exc))

    def _save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", "project.ovm.json", "Project (*.ovm.json)"
        )
        if not path:
            return
        try:
            self.workspace.save_project(Path(path))
        except Exception as exc:
            self._show_error(str(exc))

    def _load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load project", "", "Project (*.ovm.json)"
        )
        if not path:
            return
        try:
            self.workspace.load_project(Path(path))
            self._sync_controls_from_project()
            self._rebuild_measurement_table()
            self.viewport.set_lines(self.workspace.project.lines)
        except Exception as exc:
            self._show_error(str(exc))

    def _sync_controls_from_project(self) -> None:
        self.image_panel.set_settings(self.workspace.project.image_settings)
        self.measurement_panel.set_unit(self.workspace.project.unit)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export measurements", "measurements.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            self.workspace.export_csv(Path(path))
        except Exception as exc:
            self._show_error(str(exc))

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Open Vision Measure", message)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.workspace.stop()
        event.accept()
