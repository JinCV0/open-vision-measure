from __future__ import annotations

import csv
from dataclasses import replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import numpy as np

from vision_measure.camera.backend import CameraSession
from vision_measure.camera.buffer import LatestFrameBuffer
from vision_measure.camera.models import CaptureConfig, FramePacket
from vision_measure.camera.pump import FramePump
from vision_measure.inspection.annotations import (
    DEFAULT_SCALE_BAR_POSITION,
    NormalizedPoint,
)
from vision_measure.inspection.calibration import measure_line
from vision_measure.inspection.models import (
    DEFAULT_MAGNIFICATION_NAME,
    Calibration,
    Line,
    LineMeasurement,
    MagnificationProfile,
    Unit,
)
from vision_measure.inspection.processing import ImageSettings, process_frame
from vision_measure.inspection.scale_bar import ScaleBarStyle
from vision_measure.workspace.models import (
    MeasurementRecord,
    ProjectDocument,
)
from vision_measure.workspace.project import load_project, save_project
from vision_measure.workspace.screenshot import ScreenshotError, save_capture


class WorkspaceState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    FROZEN = "frozen"

    @property
    def label(self) -> str:
        return {
            WorkspaceState.IDLE: "空闲",
            WorkspaceState.RUNNING: "运行中",
            WorkspaceState.FROZEN: "已冻结",
        }[self]


class ExportError(RuntimeError):
    pass


class Workspace:
    def __init__(self) -> None:
        self.projects = ProjectDocument(
            magnifications=(MagnificationProfile(name=DEFAULT_MAGNIFICATION_NAME),),
            current_magnification=DEFAULT_MAGNIFICATION_NAME,
        )
        self.state = WorkspaceState.IDLE
        self._session: CameraSession | None = None
        self._buffer: LatestFrameBuffer | None = None
        self._pump: FramePump | None = None
        self._current: FramePacket | None = None
        self._calibration_configs: dict[str, CaptureConfig | None] = {}

    @property
    def project(self) -> ProjectDocument:
        return self.projects

    @property
    def records(self) -> tuple[MeasurementRecord, ...]:
        return self.projects.records

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(record.line for record in self.projects.records)

    @property
    def current_magnification(self) -> str | None:
        return self.projects.current_magnification

    @property
    def latest_frame(self) -> FramePacket | None:
        return self._current

    @property
    def pump_error(self) -> Exception | None:
        return None if self._pump is None else self._pump.last_error

    def _profile(self, name: str | None) -> MagnificationProfile | None:
        for profile in self.projects.magnifications:
            if profile.name == name:
                return profile
        return None

    def _measure(self, record: MeasurementRecord) -> LineMeasurement:
        profile = self._profile(record.magnification)
        calibration = (
            profile.calibration
            if profile is not None and profile.calibration is not None
            else Calibration(1.0, Unit.PX)
        )
        return measure_line(record.line, calibration)

    @property
    def current_calibration(self) -> Calibration | None:
        profile = self._profile(self.projects.current_magnification)
        return None if profile is None else profile.calibration

    @property
    def current_unit(self) -> Unit:
        calibration = self.current_calibration
        return calibration.unit if calibration is not None else Unit.MM

    @property
    def current_scale_bar_length(self) -> float | None:
        profile = self._profile(self.projects.current_magnification)
        return None if profile is None else profile.scale_bar_length

    @property
    def measurements(self) -> tuple[LineMeasurement, ...]:
        return tuple(self._measure(record) for record in self.projects.records)

    def attach_session(self, session: CameraSession) -> None:
        self.stop()
        self._session = session
        self._buffer = LatestFrameBuffer()
        self._pump = FramePump(session, self._buffer)
        self._pump.start()
        self.state = WorkspaceState.RUNNING

    def refresh_frame(self, timeout_s: float = 0.0) -> FramePacket | None:
        if self.state is WorkspaceState.FROZEN:
            return self._current
        if self.state is not WorkspaceState.RUNNING or self._buffer is None:
            return self._current
        packet = self._buffer.take_latest(timeout_s)
        if packet is not None:
            self._current = packet
        return self._current

    @property
    def display_frame(self) -> np.ndarray | None:
        if self._current is None:
            return None
        return process_frame(self._current.image, self.projects.image_settings)

    def freeze(self) -> None:
        if self.state is WorkspaceState.RUNNING:
            self.state = WorkspaceState.FROZEN

    def resume(self) -> None:
        if self.state is WorkspaceState.FROZEN:
            self.state = WorkspaceState.RUNNING

    def stop(self) -> None:
        if self._pump is not None:
            self._pump.stop()
        self._pump = None
        self._buffer = None
        self._session = None
        self._current = None
        self.state = WorkspaceState.IDLE

    def set_image_settings(self, settings: ImageSettings) -> None:
        self.projects = replace(self.projects, image_settings=settings)

    def set_magnification(self, name: str) -> None:
        if self._profile(name) is None:
            self.projects = replace(
                self.projects,
                magnifications=(*self.projects.magnifications, MagnificationProfile(name=name)),
            )
        self.projects = replace(self.projects, current_magnification=name)

    def set_calibration(
        self,
        profile_name: str,
        calibration: Calibration,
        calibrated_at: str | None = None,
        reference_length: float | None = None,
        capture_config: CaptureConfig | None = None,
    ) -> None:
        if self._profile(profile_name) is None:
            raise ValueError(f"unknown magnification: {profile_name}")
        self.projects = replace(
            self.projects,
            magnifications=tuple(
                replace(
                    profile,
                    calibration=calibration,
                    calibrated_at=calibrated_at,
                    reference_length=reference_length,
                )
                if profile.name == profile_name
                else profile
                for profile in self.projects.magnifications
            ),
        )
        self._calibration_configs[profile_name] = capture_config

    def set_scale_bar_length(self, length: float) -> None:
        name = self.projects.current_magnification
        if name is None:
            self.set_magnification(DEFAULT_MAGNIFICATION_NAME)
            name = DEFAULT_MAGNIFICATION_NAME
        self.projects = replace(
            self.projects,
            magnifications=tuple(
                replace(profile, scale_bar_length=length) if profile.name == name else profile
                for profile in self.projects.magnifications
            ),
        )

    def _clear_calibration(self, profile_name: str) -> None:
        self.projects = replace(
            self.projects,
            magnifications=tuple(
                replace(profile, calibration=None, calibrated_at=None, reference_length=None)
                if profile.name == profile_name
                else profile
                for profile in self.projects.magnifications
            ),
        )

    def clear_current_calibration(self) -> None:
        name = self.projects.current_magnification
        if name is not None:
            self._clear_calibration(name)

    def on_camera_changed(self, capture_config: CaptureConfig) -> None:
        name = self.projects.current_magnification
        if name is None:
            return
        previous = self._calibration_configs.get(name)
        if previous != capture_config:
            self._clear_calibration(name)
        self._calibration_configs[name] = capture_config

    def set_reference(self, line: Line, physical_length: float, unit: Unit) -> None:
        name = self.projects.current_magnification
        if name is None:
            self.set_magnification(DEFAULT_MAGNIFICATION_NAME)
            name = DEFAULT_MAGNIFICATION_NAME
        self.set_calibration(
            name,
            Calibration.from_reference(line, physical_length=physical_length, unit=unit),
            calibrated_at=datetime.now(UTC).isoformat(),
            reference_length=physical_length,
        )

    def add_line(self, line: Line) -> LineMeasurement:
        name = self.projects.current_magnification
        if name is None:
            self.set_magnification(DEFAULT_MAGNIFICATION_NAME)
            name = DEFAULT_MAGNIFICATION_NAME
        record = MeasurementRecord(line, name)
        self.projects = replace(
            self.projects,
            records=(*self.projects.records, record),
        )
        return self._measure(record)

    def save_project(self, path: Path) -> None:
        save_project(path, self.projects)

    def load_project(self, path: Path) -> None:
        self.projects = load_project(path)

    def save_display_frame(
        self,
        path: Path,
        scale_bar_enabled: bool = False,
        scale_bar_position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION,
        scale_bar_length: float | None = None,
        scale_bar_style: ScaleBarStyle | None = None,
    ) -> None:
        frame = self.display_frame
        if frame is None:
            raise ExportError("no frame is available")
        self._save_image(
            frame,
            path,
            scale_bar_enabled=scale_bar_enabled,
            scale_bar_position=scale_bar_position,
            scale_bar_length=scale_bar_length,
            scale_bar_style=scale_bar_style,
        )

    def _save_image(
        self,
        frame: np.ndarray,
        path: Path,
        scale_bar_enabled: bool = False,
        scale_bar_position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION,
        scale_bar_length: float | None = None,
        scale_bar_style: ScaleBarStyle | None = None,
    ) -> None:
        try:
            save_capture(
                frame,
                Path(path),
                calibration=self.current_calibration,
                scale_bar_enabled=scale_bar_enabled,
                scale_bar_position=scale_bar_position,
                scale_bar_length=scale_bar_length,
                scale_bar_style=scale_bar_style,
            )
        except ScreenshotError as exc:
            raise ExportError(f"cannot write image: {path}") from exc

    def export_csv(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(
                    (
                        "index",
                        "magnification",
                        "start_x",
                        "start_y",
                        "end_x",
                        "end_y",
                        "pixel_length",
                        "physical_length",
                        "unit",
                    )
                )
                for index, record in enumerate(self.projects.records, start=1):
                    measurement = self._measure(record)
                    line = record.line
                    writer.writerow(
                        (
                            index,
                            record.magnification,
                            line.start.x,
                            line.start.y,
                            line.end.x,
                            line.end.y,
                            measurement.pixel_length,
                            measurement.physical_length,
                            measurement.unit.value,
                        )
                    )
        except OSError as exc:
            raise ExportError(f"cannot export CSV: {path}") from exc
