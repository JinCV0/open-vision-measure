from __future__ import annotations

import csv
from dataclasses import replace
from enum import StrEnum
from pathlib import Path

import cv2
import numpy as np

from vision_measure.camera.backend import CameraSession
from vision_measure.camera.buffer import LatestFrameBuffer
from vision_measure.camera.models import FramePacket
from vision_measure.camera.pump import FramePump
from vision_measure.inspection.calibration import measure_line
from vision_measure.inspection.models import (
    Calibration,
    Line,
    LineMeasurement,
    Unit,
)
from vision_measure.inspection.processing import ImageSettings, process_frame
from vision_measure.workspace.models import ProjectDocument
from vision_measure.workspace.project import load_project, save_project


class WorkspaceState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    FROZEN = "frozen"


class ExportError(RuntimeError):
    pass


class Workspace:
    def __init__(self) -> None:
        self.projects = ProjectDocument()
        self.state = WorkspaceState.IDLE
        self._session: CameraSession | None = None
        self._buffer: LatestFrameBuffer | None = None
        self._pump: FramePump | None = None
        self._current: FramePacket | None = None

    @property
    def project(self) -> ProjectDocument:
        return self.projects

    @property
    def latest_frame(self) -> FramePacket | None:
        return self._current

    @property
    def pump_error(self) -> Exception | None:
        return None if self._pump is None else self._pump.last_error

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

    def set_calibration(self, calibration: Calibration) -> None:
        self.projects = replace(
            self.projects,
            calibration=calibration,
            unit=calibration.unit,
        )

    def set_reference(self, line: Line, physical_length: float, unit: Unit) -> None:
        self.set_calibration(
            Calibration.from_reference(line, physical_length=physical_length, unit=unit)
        )

    def add_line(self, line: Line) -> LineMeasurement:
        self.projects = replace(
            self.projects,
            lines=(*self.projects.lines, line),
        )
        return self.measurements[-1]

    @property
    def measurements(self) -> tuple[LineMeasurement, ...]:
        calibration = self.projects.calibration or Calibration(1.0, Unit.PX)
        return tuple(measure_line(line, calibration) for line in self.projects.lines)

    def save_project(self, path: Path) -> None:
        save_project(path, self.projects)

    def load_project(self, path: Path) -> None:
        self.projects = load_project(path)

    def save_display_frame(self, path: Path) -> None:
        frame = self.display_frame
        if frame is None:
            raise ExportError("no frame is available")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        extension = path.suffix.lower()
        image_format = ".jpg" if extension in {".jpg", ".jpeg"} else ".png"
        encoded, buffer = cv2.imencode(image_format, frame)
        if not encoded:
            raise ExportError(f"cannot write image: {path}")
        try:
            path.write_bytes(buffer.tobytes())
        except OSError as exc:
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
                        "start_x",
                        "start_y",
                        "end_x",
                        "end_y",
                        "pixel_length",
                        "physical_length",
                        "unit",
                    )
                )
                for index, measurement in enumerate(self.measurements, start=1):
                    line = measurement.source
                    writer.writerow(
                        (
                            index,
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
