from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vision_measure.camera.backend import CameraSession
from vision_measure.camera.models import CameraApi, CameraDevice, CaptureConfig
from vision_measure.camera.opencv_backend import OpenCvCameraBackend
from vision_measure.inspection.models import Line, Unit
from vision_measure.inspection.processing import ImageSettings
from vision_measure.ui.camera_tasks import CameraDiscoveryThread, CameraOpenThread
from vision_measure.ui.viewport import ImageViewport
from vision_measure.workspace.controller import Workspace, WorkspaceState


class MainWindow(QMainWindow):
    def __init__(
        self,
        workspace: Workspace | None = None,
        backend: OpenCvCameraBackend | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace or Workspace()
        self._backend = backend or OpenCvCameraBackend()
        self._devices: tuple[CameraDevice, ...] = ()
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
        QTimer.singleShot(0, self._refresh_cameras)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.addLayout(self._build_top_bar())
        self.viewport = ImageViewport()
        left.addWidget(self.viewport, 1)
        self.measurement_table = QTableWidget(0, 4)
        self.measurement_table.setHorizontalHeaderLabels(
            ("Type", "Pixels", "Physical", "Unit")
        )
        self.measurement_table.horizontalHeader().setStretchLastSection(True)
        self.measurement_table.setMaximumHeight(180)
        left.addWidget(self.measurement_table)
        root.addLayout(left, 1)

        controls = QVBoxLayout()
        controls.addWidget(self._build_image_group())
        controls.addWidget(self._build_measurement_group())
        controls.addWidget(self._build_project_group())
        controls.addStretch(1)
        root.addLayout(controls)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Idle")

    def _build_top_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(180)
        self.api_combo = QComboBox()
        for label, api in (
            ("Auto", CameraApi.AUTO),
            ("Media Foundation", CameraApi.MSMF),
            ("DirectShow", CameraApi.DSHOW),
            ("V4L2", CameraApi.V4L2),
        ):
            self.api_combo.addItem(label, api)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(160, 16384)
        self.width_spin.setValue(1280)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(120, 16384)
        self.height_spin.setValue(720)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 240)
        self.fps_spin.setValue(30)
        self.refresh_button = QPushButton("Refresh")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.freeze_button = QPushButton("Freeze")
        for widget in (
            QLabel("Camera"),
            self.camera_combo,
            self.api_combo,
            self.width_spin,
            QLabel("x"),
            self.height_spin,
            QLabel("FPS"),
            self.fps_spin,
            self.refresh_button,
            self.start_button,
            self.stop_button,
            self.freeze_button,
        ):
            layout.addWidget(widget)
        layout.addStretch(1)
        return layout

    def _build_image_group(self) -> QGroupBox:
        group = QGroupBox("Image")
        form = QFormLayout(group)
        self.brightness_spin = QDoubleSpinBox()
        self.brightness_spin.setRange(-255, 255)
        self.contrast_spin = QDoubleSpinBox()
        self.contrast_spin.setRange(0.1, 4.0)
        self.contrast_spin.setSingleStep(0.05)
        self.contrast_spin.setValue(1.0)
        self.gray_box = QCheckBox("Grayscale")
        self.canny_box = QCheckBox("Edges")
        self.screenshot_button = QPushButton("Save screenshot")
        form.addRow("Brightness", self.brightness_spin)
        form.addRow("Contrast", self.contrast_spin)
        form.addRow(self.gray_box)
        form.addRow(self.canny_box)
        form.addRow(self.screenshot_button)
        return group

    def _build_measurement_group(self) -> QGroupBox:
        group = QGroupBox("Measurement")
        form = QFormLayout(group)
        self.reference_length_spin = QDoubleSpinBox()
        self.reference_length_spin.setRange(0.001, 1_000_000)
        self.reference_length_spin.setDecimals(4)
        self.reference_length_spin.setValue(10.0)
        self.unit_combo = QComboBox()
        for unit in (Unit.MM, Unit.CM, Unit.IN, Unit.PX):
            self.unit_combo.addItem(unit.value, unit)
        self.calibrate_button = QPushButton("Calibrate last line")
        form.addRow("Known length", self.reference_length_spin)
        form.addRow("Unit", self.unit_combo)
        form.addRow(self.calibrate_button)
        return group

    def _build_project_group(self) -> QGroupBox:
        group = QGroupBox("Project")
        layout = QVBoxLayout(group)
        self.save_project_button = QPushButton("Save project")
        self.load_project_button = QPushButton("Load project")
        self.export_csv_button = QPushButton("Export CSV")
        layout.addWidget(self.save_project_button)
        layout.addWidget(self.load_project_button)
        layout.addWidget(self.export_csv_button)
        return group

    def _connect_events(self) -> None:
        self.refresh_button.clicked.connect(self._refresh_cameras)
        self.start_button.clicked.connect(self._start_camera)
        self.stop_button.clicked.connect(self._stop_camera)
        self.freeze_button.clicked.connect(self._toggle_freeze)
        self.viewport.line_finished.connect(self._add_line)
        self.calibrate_button.clicked.connect(self._calibrate)
        self.screenshot_button.clicked.connect(self._save_screenshot)
        self.save_project_button.clicked.connect(self._save_project)
        self.load_project_button.clicked.connect(self._load_project)
        self.export_csv_button.clicked.connect(self._export_csv)
        self.brightness_spin.valueChanged.connect(self._apply_image_settings)
        self.contrast_spin.valueChanged.connect(self._apply_image_settings)
        self.gray_box.toggled.connect(self._apply_image_settings)
        self.canny_box.toggled.connect(self._apply_image_settings)

    def _selected_api(self) -> CameraApi:
        value = self.api_combo.currentData()
        return value if isinstance(value, CameraApi) else CameraApi.AUTO

    def _selected_unit(self) -> Unit:
        value = self.unit_combo.currentData()
        return value if isinstance(value, Unit) else Unit.MM

    def _refresh_cameras(self) -> None:
        if self._discovery_thread is not None and self._discovery_thread.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.statusBar().showMessage("Discovering cameras...")
        self._discovery_thread = CameraDiscoveryThread(
            self._backend, self._selected_api(), self
        )
        self._discovery_thread.devices_found.connect(self._cameras_found)
        self._discovery_thread.failed.connect(self._camera_error)
        self._discovery_thread.finished.connect(
            lambda: self.refresh_button.setEnabled(True)
        )
        self._discovery_thread.start()

    def _cameras_found(self, devices: tuple[CameraDevice, ...]) -> None:
        self._devices = devices
        self.camera_combo.clear()
        for device in devices:
            self.camera_combo.addItem(device.label, device)
        if not devices:
            self.statusBar().showMessage("No cameras found")
        else:
            self.statusBar().showMessage(f"Found {len(devices)} camera(s)")

    def _selected_device(self) -> CameraDevice | None:
        value = self.camera_combo.currentData()
        return value if isinstance(value, CameraDevice) else None

    def _start_camera(self) -> None:
        device = self._selected_device()
        if device is None:
            self._show_error("No camera is selected")
            return
        config = CaptureConfig(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            fps=float(self.fps_spin.value()),
            api=self._selected_api(),
        )
        self.start_button.setEnabled(False)
        self.statusBar().showMessage("Opening camera...")
        self._open_thread = CameraOpenThread(self._backend, device, config, self)
        self._open_thread.opened.connect(self._camera_opened)
        self._open_thread.failed.connect(self._camera_error)
        self._open_thread.finished.connect(
            lambda: self.start_button.setEnabled(True)
        )
        self._open_thread.start()

    def _camera_opened(self, session: CameraSession) -> None:
        self.workspace.attach_session(session)
        self._last_pump_error = None
        self._update_state()

    def _camera_error(self, message: str) -> None:
        self.statusBar().showMessage("Camera error")
        self.start_button.setEnabled(True)
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
        self.freeze_button.setText(
            "Resume" if state is WorkspaceState.FROZEN else "Freeze"
        )
        self.statusBar().showMessage(state.value.title())

    def _refresh_preview(self) -> None:
        previous_state = self.workspace.state
        self.workspace.refresh_frame(timeout_s=0.0)
        frame = self.workspace.display_frame
        if frame is not None:
            self.viewport.set_frame(frame)
        self.viewport.set_lines(self.workspace.project.lines)
        if (
            self.workspace.pump_error is not None
            and self.workspace.pump_error is not self._last_pump_error
        ):
            self._last_pump_error = self.workspace.pump_error
            self._show_error(str(self._last_pump_error))
            self._stop_camera()
        elif previous_state is not self.workspace.state:
            self._update_state()

    def _apply_image_settings(self) -> None:
        self.workspace.set_image_settings(
            ImageSettings(
                brightness=self.brightness_spin.value(),
                contrast=self.contrast_spin.value(),
                grayscale=self.gray_box.isChecked(),
                canny=self.canny_box.isChecked(),
            )
        )

    def _add_line(self, line: Line) -> None:
        try:
            measurement = self.workspace.add_line(line)
        except Exception as exc:
            self._show_error(str(exc))
            return
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
        self.viewport.set_lines(self.workspace.project.lines)

    def _calibrate(self) -> None:
        if not self.workspace.project.lines:
            self._show_error("Draw a reference line first")
            return
        try:
            self.workspace.set_reference(
                self.workspace.project.lines[-1],
                self.reference_length_spin.value(),
                self._selected_unit(),
            )
            self._rebuild_measurement_table()
        except Exception as exc:
            self._show_error(str(exc))

    def _rebuild_measurement_table(self) -> None:
        self.measurement_table.setRowCount(0)
        for measurement in self.workspace.measurements:
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
        settings = self.workspace.project.image_settings
        self.brightness_spin.setValue(settings.brightness)
        self.contrast_spin.setValue(settings.contrast)
        self.gray_box.setChecked(settings.grayscale)
        self.canny_box.setChecked(settings.canny)
        index = self.unit_combo.findData(self.workspace.project.unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

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
