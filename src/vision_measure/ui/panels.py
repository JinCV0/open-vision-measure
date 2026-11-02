from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from vision_measure.camera.models import CameraApi, CameraDevice, CaptureConfig
from vision_measure.inspection.models import Unit
from vision_measure.inspection.processing import ImageSettings


class CameraControlBar(QWidget):
    refresh_requested = Signal()
    start_requested = Signal()
    stop_requested = Signal()
    freeze_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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
        self.width_spin = self._dimension_spin(160, 16384, 1280)
        self.height_spin = self._dimension_spin(120, 16384, 720)
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
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.freeze_button.clicked.connect(self.freeze_requested.emit)

    @staticmethod
    def _dimension_spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def selected_api(self) -> CameraApi:
        value = self.api_combo.currentData()
        return value if isinstance(value, CameraApi) else CameraApi.AUTO

    def selected_device(self) -> CameraDevice | None:
        value = self.camera_combo.currentData()
        return value if isinstance(value, CameraDevice) else None

    def capture_config(self) -> CaptureConfig:
        return CaptureConfig(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            fps=float(self.fps_spin.value()),
            api=self.selected_api(),
        )

    def set_devices(self, devices: tuple[CameraDevice, ...]) -> None:
        self.camera_combo.clear()
        for device in devices:
            self.camera_combo.addItem(device.label, device)

    def set_frozen(self, frozen: bool) -> None:
        self.freeze_button.setText("Resume" if frozen else "Freeze")


class ImagePanel(QGroupBox):
    settings_changed = Signal()
    screenshot_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Image", parent)
        form = QFormLayout(self)
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
        self.brightness_spin.valueChanged.connect(self.settings_changed.emit)
        self.contrast_spin.valueChanged.connect(self.settings_changed.emit)
        self.gray_box.toggled.connect(self.settings_changed.emit)
        self.canny_box.toggled.connect(self.settings_changed.emit)
        self.screenshot_button.clicked.connect(self.screenshot_requested.emit)

    def settings(self) -> ImageSettings:
        return ImageSettings(
            brightness=self.brightness_spin.value(),
            contrast=self.contrast_spin.value(),
            grayscale=self.gray_box.isChecked(),
            canny=self.canny_box.isChecked(),
        )

    def set_settings(self, settings: ImageSettings) -> None:
        self.brightness_spin.setValue(settings.brightness)
        self.contrast_spin.setValue(settings.contrast)
        self.gray_box.setChecked(settings.grayscale)
        self.canny_box.setChecked(settings.canny)


class MeasurementPanel(QGroupBox):
    calibrate_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Measurement", parent)
        form = QFormLayout(self)
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
        self.calibrate_button.clicked.connect(self.calibrate_requested.emit)

    def selected_unit(self) -> Unit:
        value = self.unit_combo.currentData()
        return value if isinstance(value, Unit) else Unit.MM

    def set_unit(self, unit: Unit) -> None:
        index = self.unit_combo.findData(unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)


class ProjectPanel(QGroupBox):
    save_requested = Signal()
    load_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Project", parent)
        layout = QVBoxLayout(self)
        self.save_button = QPushButton("Save project")
        self.load_button = QPushButton("Load project")
        self.export_button = QPushButton("Export CSV")
        layout.addWidget(self.save_button)
        layout.addWidget(self.load_button)
        layout.addWidget(self.export_button)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.load_button.clicked.connect(self.load_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)
