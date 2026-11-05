from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from vision_measure.camera.models import CameraApi, CameraDevice, CaptureConfig
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.inspection.processing import ImageSettings
from vision_measure.ui.theme import (
    configure_card_layout,
    configure_form_layout,
    set_material_property,
)


class CameraControlBar(QWidget):
    refresh_requested = Signal()
    start_requested = Signal()
    stop_requested = Signal()
    freeze_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_material_property(self, "materialRole", "card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        configure_card_layout(layout)
        layout.setContentsMargins(20, 20, 20, 20)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(180)
        self.api_combo = QComboBox()
        self.api_combo.setMinimumWidth(140)
        for label, api in (
            ("自动", CameraApi.AUTO),
            ("Media Foundation", CameraApi.MSMF),
            ("DirectShow", CameraApi.DSHOW),
            ("V4L2", CameraApi.V4L2),
        ):
            self.api_combo.addItem(label, api)
        self.width_spin = self._dimension_spin(0, 16384, 0)
        self.height_spin = self._dimension_spin(0, 16384, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(0, 240)
        self.fps_spin.setValue(0)
        self.fps_spin.setSpecialValueText("最佳")
        self.fps_spin.setMaximumWidth(80)
        self.refresh_button = QPushButton("刷新")
        self.start_button = QPushButton("启动")
        self.stop_button = QPushButton("停止")
        self.freeze_button = QPushButton("冻结")
        top_row.addWidget(QLabel("相机"))
        top_row.addWidget(self.camera_combo, 1)
        top_row.addWidget(self.api_combo)
        bottom_row.addWidget(self.width_spin)
        bottom_row.addWidget(QLabel("×"))
        bottom_row.addWidget(self.height_spin)
        bottom_row.addWidget(QLabel("帧率"))
        bottom_row.addWidget(self.fps_spin)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.refresh_button)
        bottom_row.addWidget(self.start_button)
        bottom_row.addWidget(self.stop_button)
        bottom_row.addWidget(self.freeze_button)
        layout.addLayout(top_row)
        layout.addLayout(bottom_row)
        set_material_property(self.start_button, "materialAppearance", "primary")
        for button in (
            self.refresh_button,
            self.stop_button,
            self.freeze_button,
        ):
            set_material_property(button, "materialAppearance", "text")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.freeze_button.clicked.connect(self.freeze_requested.emit)

    @staticmethod
    def _dimension_spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSpecialValueText("最佳")
        spin.setMaximumWidth(100)
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
        self.freeze_button.setText("继续" if frozen else "冻结")


class ImagePanel(QGroupBox):
    settings_changed = Signal()
    screenshot_requested = Signal()
    ai_screenshot_requested = Signal()
    folder_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("图像", parent)
        form = QFormLayout(self)
        configure_form_layout(form)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_value = QLabel("0")
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(50, 200)
        self.contrast_slider.setValue(100)
        self.contrast_value = QLabel("100%")
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(-100, 100)
        self.temperature_value = QLabel("0")
        self.tint_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_slider.setRange(-100, 100)
        self.tint_value = QLabel("0")
        self.gray_box = QCheckBox("灰度")
        self.canny_box = QCheckBox("边缘")
        self.screenshot_button = QPushButton("保存截图")
        self.ai_screenshot_button = QPushButton("AI 截图")
        self.folder_button = QPushButton("文件夹")
        for value in (
            self.brightness_value,
            self.contrast_value,
            self.temperature_value,
            self.tint_value,
        ):
            set_material_property(value, "materialRole", "value")
        set_material_property(self.folder_button, "materialAppearance", "text")
        form.addRow("亮度", self._slider_row(self.brightness_slider, self.brightness_value))
        form.addRow("对比度", self._slider_row(self.contrast_slider, self.contrast_value))
        form.addRow(
            "色温",
            self._slider_row(self.temperature_slider, self.temperature_value),
        )
        form.addRow("色调", self._slider_row(self.tint_slider, self.tint_value))
        form.addRow(self.gray_box)
        form.addRow(self.canny_box)
        screenshot_row = QHBoxLayout()
        screenshot_row.addWidget(self.screenshot_button)
        screenshot_row.addWidget(self.ai_screenshot_button)
        screenshot_row.addWidget(self.folder_button)
        form.addRow(screenshot_row)
        self.brightness_slider.valueChanged.connect(self._values_changed)
        self.contrast_slider.valueChanged.connect(self._values_changed)
        self.temperature_slider.valueChanged.connect(self._values_changed)
        self.tint_slider.valueChanged.connect(self._values_changed)
        self.gray_box.toggled.connect(self.settings_changed.emit)
        self.canny_box.toggled.connect(self.settings_changed.emit)
        self.screenshot_button.clicked.connect(self.screenshot_requested.emit)
        self.ai_screenshot_button.clicked.connect(self.ai_screenshot_requested.emit)
        self.folder_button.clicked.connect(self.folder_requested.emit)

    @staticmethod
    def _slider_row(slider: QSlider, value: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(slider, 1)
        value.setMinimumWidth(44)
        row.addWidget(value)
        return row

    def _values_changed(self) -> None:
        self.brightness_value.setText(f"{self.brightness_slider.value():+d}")
        self.contrast_value.setText(f"{self.contrast_slider.value()}%")
        self.temperature_value.setText(f"{self.temperature_slider.value():+d}")
        self.tint_value.setText(f"{self.tint_slider.value():+d}")
        self.settings_changed.emit()

    def settings(self) -> ImageSettings:
        return ImageSettings(
            brightness=self.brightness_slider.value() * 2.55,
            contrast=self.contrast_slider.value() / 100.0,
            temperature=float(self.temperature_slider.value()),
            tint=float(self.tint_slider.value()),
            grayscale=self.gray_box.isChecked(),
            canny=self.canny_box.isChecked(),
        )

    def set_settings(self, settings: ImageSettings) -> None:
        controls = (
            self.brightness_slider,
            self.contrast_slider,
            self.temperature_slider,
            self.tint_slider,
            self.gray_box,
            self.canny_box,
        )
        for control in controls:
            control.blockSignals(True)
        self.brightness_slider.setValue(round(settings.brightness / 2.55))
        self.contrast_slider.setValue(round(settings.contrast * 100))
        self.temperature_slider.setValue(round(settings.temperature))
        self.tint_slider.setValue(round(settings.tint))
        self.gray_box.setChecked(settings.grayscale)
        self.canny_box.setChecked(settings.canny)
        for control in controls:
            control.blockSignals(False)
        self._values_changed()


class MagnificationPanel(QGroupBox):
    magnification_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("倍率", parent)
        form = QFormLayout(self)
        configure_form_layout(form)
        self.selector = QComboBox()
        self.selector.setEditable(True)
        self.selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for name in ("4x", "10x", "40x", "100x"):
            self.selector.addItem(name)
        self.status = QLabel("未标定")
        set_material_property(self.status, "materialRole", "value")
        form.addRow("当前", self.selector)
        form.addRow("标定", self.status)
        self.selector.activated.connect(self._emit_selected)
        line_edit = self.selector.lineEdit()
        if line_edit is not None:
            line_edit.editingFinished.connect(self._emit_selected)

    def set_profiles(self, names: tuple[str, ...], current: str | None) -> None:
        existing = {self.selector.itemText(index) for index in range(self.selector.count())}
        for name in names:
            if name not in existing:
                self.selector.addItem(name)
        if current is not None:
            self.selector.setEditText(current)

    def select_magnification(self, name: str) -> None:
        self.selector.setEditText(name)
        self.magnification_changed.emit(name)

    def set_calibration(
        self,
        calibration: Calibration | None,
        message: str | None = None,
    ) -> None:
        if calibration is None:
            self.status.setText(message or "未标定")
            return
        self.status.setText(
            f"{calibration.units_per_pixel:.4g} {calibration.unit.display_name}/像素"
        )

    def _emit_selected(self, _index: int = -1) -> None:
        name = self.selector.currentText().strip()
        if name:
            self.magnification_changed.emit(name)


class CalibrationPanel(QGroupBox):
    calibrate_requested = Signal()
    measure_toggled = Signal(bool)
    unit_changed = Signal(object)
    scale_bar_length_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("标定", parent)
        form = QFormLayout(self)
        configure_form_layout(form)
        self.reference_length_spin = QDoubleSpinBox()
        self.reference_length_spin.setRange(0.001, 1_000_000)
        self.reference_length_spin.setDecimals(4)
        self.reference_length_spin.setValue(10.0)
        self.unit_combo = QComboBox()
        for unit in (Unit.MM, Unit.CM, Unit.UM, Unit.IN, Unit.PX):
            self.unit_combo.addItem(unit.display_name, unit)
        self.measure_button = QPushButton("测量")
        self.measure_button.setCheckable(True)
        set_material_property(self.measure_button, "materialAppearance", "primary")
        self.calibrate_button = QPushButton("设置标定")
        self.scale_bar_box = QCheckBox("比例尺")
        self.scale_bar_box.setEnabled(False)
        self.scale_bar_length_spin = QDoubleSpinBox()
        self.scale_bar_length_spin.setRange(0.001, 1_000_000)
        self.scale_bar_length_spin.setDecimals(4)
        self.scale_bar_length_spin.setValue(10.0)
        self.scale_bar_length_spin.setEnabled(False)
        self.set_scale_bar_unit(Unit.MM)
        form.addRow(self.measure_button)
        form.addRow("已知长度", self.reference_length_spin)
        form.addRow("单位", self.unit_combo)
        form.addRow(self.scale_bar_box)
        form.addRow("比例尺长度", self.scale_bar_length_spin)
        form.addRow(self.calibrate_button)
        self.measure_button.toggled.connect(self.measure_toggled.emit)
        self.unit_combo.currentIndexChanged.connect(self._unit_changed)
        self.calibrate_button.clicked.connect(self.calibrate_requested.emit)
        self.scale_bar_length_spin.editingFinished.connect(
            lambda: self.scale_bar_length_changed.emit(self.scale_bar_length_spin.value())
        )

    def selected_unit(self) -> Unit:
        value = self.unit_combo.currentData()
        try:
            return Unit(value)
        except (TypeError, ValueError):
            return Unit.MM

    def set_unit(self, unit: Unit) -> None:
        index = self.unit_combo.findData(unit)
        if index >= 0:
            self.unit_combo.blockSignals(True)
            self.unit_combo.setCurrentIndex(index)
            self.unit_combo.blockSignals(False)
            self.set_scale_bar_unit(unit)

    def set_scale_bar_unit(self, unit: Unit) -> None:
        self.scale_bar_length_spin.setSuffix(f" {unit.display_name}")

    def _unit_changed(self, _index: int) -> None:
        unit = self.selected_unit()
        self.set_scale_bar_unit(unit)
        self.unit_changed.emit(unit)

    def set_calibration_available(self, available: bool) -> None:
        self.scale_bar_box.setEnabled(available)
        self.scale_bar_length_spin.setEnabled(available)

    def set_measure_active(self, active: bool) -> None:
        self.measure_button.blockSignals(True)
        self.measure_button.setChecked(active)
        self.measure_button.blockSignals(False)

    def set_scale_bar_length(self, length: float | None) -> None:
        if length is None:
            return
        self.scale_bar_length_spin.blockSignals(True)
        self.scale_bar_length_spin.setValue(length)
        self.scale_bar_length_spin.blockSignals(False)


MeasurementPanel = CalibrationPanel


class ProjectPanel(QGroupBox):
    save_requested = Signal()
    load_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("项目", parent)
        layout = QVBoxLayout(self)
        configure_card_layout(layout)
        self.save_button = QPushButton("保存项目")
        self.load_button = QPushButton("打开项目")
        self.export_button = QPushButton("导出 CSV")
        for button in (self.save_button, self.load_button, self.export_button):
            set_material_property(button, "materialAppearance", "text")
        layout.addWidget(self.save_button)
        layout.addWidget(self.load_button)
        layout.addWidget(self.export_button)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.load_button.clicked.connect(self.load_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)
