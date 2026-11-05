from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from vision_measure.camera.backend import CameraSession
from vision_measure.camera.models import CameraDevice, CaptureConfig
from vision_measure.camera.opencv_backend import OpenCvCameraBackend
from vision_measure.inspection.annotations import NormalizedPoint
from vision_measure.inspection.models import Line
from vision_measure.ui.ai_capture import AiScreenshotController
from vision_measure.ui.camera_tasks import CameraDiscoveryThread, CameraOpenThread
from vision_measure.ui.microscope import MicroscopeControls
from vision_measure.ui.panels import (
    CalibrationPanel,
    CameraControlBar,
    ImagePanel,
    MagnificationPanel,
    ProjectPanel,
)
from vision_measure.ui.screenshot_flow import choose_capture_path
from vision_measure.ui.viewport import ImageViewport
from vision_measure.workspace.controller import ExportError, Workspace, WorkspaceState
from vision_measure.workspace.preferences import (
    AppPreferences,
    PreferencesFormatError,
    PreferencesStore,
    default_preferences_path,
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        workspace: Workspace | None = None,
        backend: OpenCvCameraBackend | None = None,
        parent: QWidget | None = None,
        auto_discover: bool = True,
        preferences_store: PreferencesStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace or Workspace()
        self._backend = backend or OpenCvCameraBackend()
        self._discovery_thread: CameraDiscoveryThread | None = None
        self._open_thread: CameraOpenThread | None = None
        self._last_pump_error: Exception | None = None
        self._preferences_store = preferences_store or PreferencesStore(default_preferences_path())
        self.preferences = self._load_preferences()
        self.setWindowTitle("Open Vision Measure")
        self.resize(1440, 900)
        self._build_ui()
        self.microscope = MicroscopeControls(
            self.workspace,
            self.magnification_panel,
            self.calibration_panel,
            self.viewport,
        )
        self.ai_capture = AiScreenshotController(
            self.workspace,
            self.image_panel,
            self,
            lambda: self.preferences,
            self._set_preferences,
            self._show_error,
            self.statusBar().showMessage,
        )
        self._connect_events()
        self.microscope.sync()
        self.image_panel.set_settings(self.workspace.project.image_settings)
        self._sync_scale_bar_overlay()
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
        root.addLayout(left, 1)

        self.image_panel = ImagePanel()
        self.magnification_panel = MagnificationPanel()
        self.magnification_selector = self.magnification_panel.selector
        self.calibration_status = self.magnification_panel.status
        self.calibration_panel = CalibrationPanel()
        self.project_panel = ProjectPanel()
        controls = QVBoxLayout()
        controls.addWidget(self.magnification_panel)
        controls.addWidget(self.image_panel)
        controls.addWidget(self.calibration_panel)
        controls.addWidget(self.project_panel)
        controls.addStretch(1)
        root.addLayout(controls)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Idle")

    def _connect_events(self) -> None:
        self.camera_bar.refresh_requested.connect(self._refresh_cameras)
        self.camera_bar.start_requested.connect(self._start_camera)
        self.camera_bar.stop_requested.connect(self._stop_camera)
        self.camera_bar.freeze_requested.connect(self._toggle_freeze)
        self.image_panel.settings_changed.connect(self._apply_image_settings)
        self.image_panel.screenshot_requested.connect(self._save_screenshot)
        self.image_panel.folder_requested.connect(self._choose_screenshot_folder)
        self.viewport.line_finished.connect(self._add_line)
        self.microscope.error_occurred.connect(self._show_error)
        self.microscope.overlay_changed.connect(self._sync_scale_bar_overlay)
        self.calibration_panel.scale_bar_box.toggled.connect(self._scale_bar_toggled)
        self.viewport.scale_bar_moved.connect(self._scale_bar_moved)
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
        mode = session.mode
        self.workspace.on_camera_changed(
            CaptureConfig(
                width=mode.width,
                height=mode.height,
                fps=mode.fps,
                api=self.camera_bar.selected_api(),
                fourcc=mode.fourcc,
            )
        )
        self._last_pump_error = None
        self._update_state()
        self.microscope.sync()
        self._sync_scale_bar_overlay()
        fps = f" · {mode.fps:g} FPS" if mode.fps > 0 else ""
        self.statusBar().showMessage(f"Running · {mode.width}x{mode.height}{fps} · {mode.fourcc}")

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
        self.viewport.set_lines(self.workspace.lines)
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
            self.workspace.add_line(line)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self.viewport.set_lines(self.workspace.lines)

    def _save_screenshot(self) -> None:
        selected = choose_capture_path(self, self.preferences)
        if selected is None:
            return
        path, preferences = selected
        try:
            self.workspace.save_display_frame(
                path,
                scale_bar_enabled=(
                    preferences.scale_bar_enabled and self.workspace.current_calibration is not None
                ),
                scale_bar_position=preferences.scale_bar_position,
                scale_bar_length=self.workspace.current_scale_bar_length,
            )
            self._set_preferences(preferences)
            self.statusBar().showMessage(f"Saved {path}")
        except (ExportError, ValueError) as exc:
            self._show_error(str(exc))

    def _choose_screenshot_folder(self) -> None:
        start = (
            str(self.preferences.screenshot_directory)
            if self.preferences.screenshot_directory is not None
            else ""
        )
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose screenshot folder",
            start,
        )
        if selected:
            self._set_preferences(
                AppPreferences(
                    screenshot_directory=Path(selected),
                    screenshot_extension=self.preferences.screenshot_extension,
                    scale_bar_enabled=self.preferences.scale_bar_enabled,
                    scale_bar_position=self.preferences.scale_bar_position,
                )
            )

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
        path, _ = QFileDialog.getOpenFileName(self, "Load project", "", "Project (*.ovm.json)")
        if not path:
            return
        try:
            self.workspace.load_project(Path(path))
            self._sync_controls_from_project()
            self.viewport.set_lines(self.workspace.lines)
            self._sync_scale_bar_overlay()
        except Exception as exc:
            self._show_error(str(exc))

    def _sync_controls_from_project(self) -> None:
        self.image_panel.set_settings(self.workspace.project.image_settings)
        self.microscope.sync()

    def _load_preferences(self) -> AppPreferences:
        try:
            return self._preferences_store.load()
        except PreferencesFormatError:
            return AppPreferences()

    def _set_preferences(self, preferences: AppPreferences) -> None:
        try:
            self._preferences_store.save(preferences)
        except PreferencesFormatError as exc:
            self._show_error(str(exc))
            return
        self.preferences = preferences

    def _scale_bar_toggled(self, enabled: bool) -> None:
        self._set_preferences(
            AppPreferences(
                screenshot_directory=self.preferences.screenshot_directory,
                screenshot_extension=self.preferences.screenshot_extension,
                scale_bar_enabled=enabled,
                scale_bar_position=self.preferences.scale_bar_position,
            )
        )
        self._sync_scale_bar_overlay()

    def _scale_bar_moved(self, position: object) -> None:
        if not isinstance(position, NormalizedPoint):
            return
        self._set_preferences(
            AppPreferences(
                screenshot_directory=self.preferences.screenshot_directory,
                screenshot_extension=self.preferences.screenshot_extension,
                scale_bar_enabled=self.preferences.scale_bar_enabled,
                scale_bar_position=position,
            )
        )

    def _sync_scale_bar_overlay(self) -> None:
        calibration = self.workspace.current_calibration
        self.calibration_panel.set_calibration_available(calibration is not None)
        self.calibration_panel.scale_bar_box.blockSignals(True)
        self.calibration_panel.scale_bar_box.setChecked(
            self.preferences.scale_bar_enabled and calibration is not None
        )
        self.calibration_panel.scale_bar_box.blockSignals(False)
        self.viewport.set_scale_bar(
            calibration,
            self.preferences.scale_bar_enabled and calibration is not None,
            self.preferences.scale_bar_position,
            self.workspace.current_scale_bar_length,
        )

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
