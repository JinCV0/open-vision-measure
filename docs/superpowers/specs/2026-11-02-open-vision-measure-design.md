# Open Vision Measure — Core MVP Design

Date: 2026-11-02
Status: Approved direction, pending specification review
License: Apache-2.0

## 1. Objective

Build a local-first camera inspection and measurement desktop application. The
first release must provide a complete vertical slice:

1. Discover and open a local camera.
2. Preview live frames and freeze/resume the preview.
3. Save the currently displayed frame as PNG or JPEG.
4. Add a line measurement in image coordinates.
5. Calibrate pixels to a physical unit by entering the known length of a
   reference line.
6. Display measured physical dimensions.
7. Save and restore the project.
8. Export measurements as CSV.

The application must work without network access.

## 2. Product Boundary

### Included

- Windows-first validation with a cross-platform Qt implementation.
- Camera index-based discovery and configurable resolution/frame rate.
- Live preview, freeze/resume, stop, and screenshot.
- A measurement toolchain centered on image-space geometry.
- Pixel calibration in millimetres, centimetres, inches, and pixels.
- Basic image adjustments needed to inspect the measurement target.
- Project persistence and CSV export.
- A synthetic camera adapter for deterministic tests.

### Deferred

- Video recording.
- AI super-resolution or image restoration.
- Excel reports, PDF reports, and print layouts.
- Licensing, payment, advertising, user accounts, and telemetry.
- Multiple languages, WebView content, automatic updates, and cloud storage.
- Proprietary industrial-camera SDKs.
- Advanced measurement tools beyond the first line-measurement slice.

GPL and AGPL application code will not be copied into this project. The
application will remain Apache-2.0 and depend only on compatible libraries.

## 3. Technology

- Python 3.12, managed by `uv`.
- PySide6 for the desktop UI.
- OpenCV and NumPy for frame acquisition and image processing.
- pytest and pytest-qt for automated tests.
- Ruff and mypy for static checks.
- Hatchling with `pyproject.toml` for packaging.

PySide6 is used as an LGPL dependency and will remain dynamically linked so the
application can comply with the LGPL replacement requirement.

## 4. Architecture

The code is a single installable package, `vision_measure`, with four top-level
modules. Dependencies flow inward: `ui` may depend on application services;
application services depend on camera and inspection interfaces; the core
measurement and image-processing code does not depend on Qt.

### 4.1 `camera`

Owns camera discovery, frame acquisition, backend selection, and resource
cleanup.

Public interface:

```python
class CameraBackend(Protocol):
    def discover(self) -> tuple[CameraDevice, ...]: ...
    def open(self, device: CameraDevice, config: CaptureConfig) -> CameraSession: ...

class CameraSession(Protocol):
    def read_latest(self, timeout_s: float) -> FramePacket: ...
    def close(self) -> None: ...
```

The first adapter uses OpenCV `VideoCapture`. Backend selection is explicit:
`CAP_MSMF` on Windows is preferred, `CAP_DSHOW` is available as a fallback, and
`CAP_V4L2` is used on Linux. Device enumeration scans a bounded configurable
index range and reports an index plus backend. A failed open is a user-visible
`CameraUnavailable` error. Closing is idempotent.

The camera worker owns the backend session and writes at most one frame into a
single-slot bounded buffer. A newer frame replaces a frame that has not yet been
consumed. The UI must never block on camera I/O.

### 4.2 `inspection`

Owns deterministic image processing, geometry, calibration, and measurement
values. It accepts NumPy arrays and returns immutable results. It does not
import PySide6.

Public interface:

```python
def process_frame(frame: np.ndarray, settings: ImageSettings) -> np.ndarray: ...

class Calibration:
    def __init__(self, image_length_px: float, physical_length: float, unit: Unit): ...
    def pixels_to_unit(self, pixels: float) -> float: ...
    def unit_to_pixels(self, value: float) -> float: ...

def measure_line(line: Line, calibration: Calibration) -> LineMeasurement: ...
```

The first release supports:

- Brightness and contrast adjustment.
- Grayscale conversion.
- Canny edge preview.
- Line geometry and length in pixels.
- Calibrated length in the selected physical unit.

Measurement data is stored in image coordinates, not widget coordinates.
Viewport zoom and panning affect only the presentation layer. Invalid
calibration values, non-finite coordinates, and zero-length references produce
typed errors rather than silently clamping.

### 4.3 `workspace`

Owns application state and user workflows.

Public interface:

```python
class Workspace:
    def start_camera(self, device: CameraDevice, config: CaptureConfig) -> None: ...
    def stop_camera(self) -> None: ...
    def freeze(self) -> None: ...
    def resume(self) -> None: ...
    def capture_frame(self) -> FramePacket: ...
    def set_calibration(self, calibration: Calibration) -> None: ...
    def add_line(self, line: Line) -> MeasurementRecord: ...
    def save_project(self, path: Path) -> None: ...
    def load_project(self, path: Path) -> None: ...
    def export_csv(self, path: Path) -> None: ...
```

The state machine is:

```text
IDLE -> RUNNING <-> FROZEN -> RUNNING
  |        |
  +--------+----> IDLE
```

`capture_frame` always returns the frame associated with the current displayed
state. It never opens a second camera session. Project writes use a temporary
sibling file followed by an atomic replace. The JSON project format has an
explicit `schema_version` and stores calibration, settings, and measurements.
CSV output contains measurement type, coordinates, pixel length, physical
length, and unit.

### 4.4 `ui`

Owns the PySide6 windows, widgets, viewport rendering, and event translation.
The UI calls `Workspace` and renders its results; it does not call OpenCV or
implement geometric formulas.

The first screen contains:

- Camera selector, resolution and frame-rate controls.
- Start, stop, freeze/resume, and screenshot controls.
- Main image viewport with measurement overlay.
- Image-adjustment controls.
- Line tool, calibration fields, measurement list, and export controls.

The viewport preserves the image aspect ratio. Mouse coordinates are converted
from widget coordinates to image coordinates before being sent to the
`inspection` module.

## 5. Error Handling

Typed errors are used for expected failures:

- `CameraUnavailable`
- `CameraReadTimeout`
- `InvalidCalibration`
- `InvalidMeasurement`
- `ProjectFormatError`
- `ExportError`

The UI displays a concise error message and leaves the workspace recoverable.
Camera disconnect stops acquisition and releases the backend. A failed save
does not modify the previous project file. Unexpected exceptions are logged
with context; they are not converted into successful empty results.

## 6. Data Flow

```text
camera worker -> single-slot frame buffer -> workspace state
                                             |
                                             v
                                  inspection processing
                                             |
                                             v
                           image + line overlay -> Qt viewport
                                             |
                              +--------------+-------------+
                              |                            |
                         project JSON                   CSV
```

The UI receives frame updates through Qt signals. The camera thread does not
mutate widgets. Freeze changes which frame the workspace presents; it does not
stop the camera device unless the user explicitly stops it.

## 7. Testing

### Unit tests

- Calibration conversion and round trips.
- Line length in pixel and physical coordinates.
- Brightness/contrast/grayscale/Canny output shape and determinism.
- JSON serialization and schema migration rejection for unknown versions.
- CSV header and row formatting.
- Error cases: invalid calibration, non-finite coordinates, zero-length line.

### Integration tests

- Synthetic camera emits deterministic frames through the camera interface.
- Start, freeze, resume, capture, save, load, and export as one workflow.
- A single-slot buffer drops stale frames without unbounded growth.
- A failure to open a camera leaves the workspace in `IDLE`.

### UI tests

- Headless `pytest-qt` smoke test launches the main window.
- Camera selector and controls update workspace state.
- Viewport converts widget coordinates to image coordinates correctly.

### Acceptance test

On a real Windows camera:

1. Open the camera and observe a live preview.
2. Freeze and resume without restarting the camera.
3. Capture a screenshot and verify the saved file opens.
4. Draw a line against a known reference and calibrate it.
5. Add a second line and verify its physical length.
6. Save, restart, reload, and export the project.
7. Run a 60-second preview and verify the frame buffer does not grow without
   bound.

## 8. Repository Layout

```text
open-vision-measure/
  pyproject.toml
  uv.lock
  LICENSE
  README.md
  src/vision_measure/
    camera/
    inspection/
    workspace/
    ui/
  tests/
    unit/
    integration/
    ui/
  docs/
    superpowers/specs/
```

The package entry point is `vision_measure.ui.app:main`. No business logic is
placed in that entry point.

## 9. Implementation Order

1. Create the uv/Python project, package metadata, license, and test layout.
2. Implement measurement primitives and calibration with tests.
3. Implement the synthetic camera and camera interface with tests.
4. Implement the OpenCV camera adapter and single-slot frame buffer.
5. Implement workspace lifecycle and project persistence with tests.
6. Implement the PySide6 camera preview and screenshot flow.
7. Implement viewport-to-image coordinate mapping and line tools.
8. Add CSV export, UI smoke tests, and real-camera acceptance.

Each step must keep the unit and integration test suite green. Real-camera
behavior is reported separately from synthetic-camera tests.

## 10. Definition of Done

The first milestone is complete when a new user can run one documented command,
open a local camera, freeze and capture a frame, calibrate pixels against a
known length, measure a line in millimetres, save and reload the project, and
export the measurements to CSV. Production behavior must be demonstrated on a
real camera; synthetic tests alone do not satisfy acceptance.
