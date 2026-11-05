# Microscope Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the microscope electronic-eyepiece workflow: per-magnification calibration, a two-click calibration interaction, a fixed-physical-length scale bar, plant-tissue measurements that keep their source magnification, and optional AI subject extraction with graceful fallback.

**Architecture:** Extend the four-module `vision_measure` package without growing `ui/main_window.py`. `inspection` owns magnification configuration, conversion, scale-bar geometry, and mask cleanup; `workspace` owns switching magnifications, persistence, and the screenshot pipeline; a new `subject_extraction` boundary isolates `rembg` inference; `ui` only collects input and renders.

**Tech Stack:** Python 3.12, uv, PySide6, OpenCV, NumPy, pytest, pytest-qt, Ruff, mypy, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-11-05-microscope-workflow.md`

## Execution Status

As of 2026-11-05:

- Tasks 1-9 are implemented and covered by the local test gate.
- Task 10 is locally complete through wheel/sdist, AI-enabled EXE, basic smoke,
  AI runtime smoke, and packaged real-model inference smoke.
- Real plant-tissue quality validation, the 20-image acceptance set, model-weight
  redistribution review, remote push, and GitHub Release remain pending.

## Global Constraints

- Application code uses Apache-2.0; do not copy GPL/AGPL application code.
- Python 3.12 managed with `uv`.
- `src/vision_measure/ui/app.py:main` is the only entry point and contains assembly only.
- UI code must not call OpenCV directly.
- Measurement data is stored in image coordinates.
- Expected failures use typed exceptions.
- Every production behavior is introduced by a failing test.
- `ui/main_window.py` must not exceed 400 lines; new controls go in `ui/panels.py` or a new module.
- Schema v1 projects must remain loadable; migration never applies one v1 calibration to every magnification.

---

### Task 1: Magnification Profile Value Object

**Files:**
- Modify: `src/vision_measure/inspection/models.py`
- Test: `tests/unit/test_magnification.py`

**Interfaces:**
- Consumes: `Calibration`, `Unit` from `vision_measure.inspection.models`.
- Produces: `DEFAULT_MAGNIFICATION_NAME = "default"` and a frozen
  `MagnificationProfile(name, calibration=None, calibrated_at=None,
  reference_length=None, scale_bar_length=None)`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from vision_measure.inspection.models import (
    DEFAULT_MAGNIFICATION_NAME,
    Calibration,
    MagnificationProfile,
    Unit,
)


def test_default_magnification_name_is_stable() -> None:
    assert DEFAULT_MAGNIFICATION_NAME == "default"


def test_profile_defaults_to_uncalibrated() -> None:
    profile = MagnificationProfile(name="4x")
    assert profile.calibration is None
    assert profile.calibrated_at is None
    assert profile.reference_length is None
    assert profile.scale_bar_length is None


def test_profile_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        MagnificationProfile(name="")


def test_profile_rejects_non_positive_scale_bar_length() -> None:
    with pytest.raises(ValueError):
        MagnificationProfile(name="10x", scale_bar_length=0.0)


def test_profile_holds_calibration() -> None:
    calibration = Calibration(units_per_pixel=0.5, unit=Unit.MM)
    profile = MagnificationProfile(
        name="10x",
        calibration=calibration,
        calibrated_at="2026-11-05T10:00:00Z",
        reference_length=10.0,
        scale_bar_length=10.0,
    )
    assert profile.calibration is calibration
    assert profile.reference_length == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_magnification.py -v`
Expected: FAIL with `ImportError` for `DEFAULT_MAGNIFICATION_NAME` and
`MagnificationProfile`.

- [ ] **Step 3: Implement the value object**

Add to `src/vision_measure/inspection/models.py`, after `Calibration`:

```python
DEFAULT_MAGNIFICATION_NAME = "default"


@dataclass(frozen=True, slots=True)
class MagnificationProfile:
    name: str
    calibration: Calibration | None = None
    calibrated_at: str | None = None
    reference_length: float | None = None
    scale_bar_length: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("magnification name must not be empty")
        for label, value in (
            ("reference_length", self.reference_length),
            ("scale_bar_length", self.scale_bar_length),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{label} must be finite and positive")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_magnification.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/inspection/models.py tests/unit/test_magnification.py
git commit -m "feat: add magnification profile value object"
```

### Task 2: Schema v2 and v1 Migration

**Files:**
- Modify: `src/vision_measure/workspace/models.py`
- Modify: `src/vision_measure/workspace/project.py`
- Modify: `src/vision_measure/workspace/controller.py`
- Test: `tests/unit/test_project.py` (replace)
- Test: `tests/unit/test_magnification.py` (extend)

**Interfaces:**
- Consumes: `MagnificationProfile`, `DEFAULT_MAGNIFICATION_NAME`,
  `Calibration`, `Line`, `ImageSettings`.
- Produces: `MeasurementRecord(line, magnification)`,
  `ProjectDocument(schema_version=2, magnifications=(), current_magnification=None,
  records=(), image_settings=ImageSettings())`, `SCHEMA_VERSION = 2`,
  `load_project`/`save_project` handling v1 and v2, and `Workspace` methods
  `magnifications`, `current_magnification`, `set_magnification`,
  `set_calibration(profile_name, calibration)`, `add_line(line) ->
  MeasurementRecord`, and `measurements`.

- [ ] **Step 1: Write the failing tests**

Replace `tests/unit/test_project.py`:

```python
import json

import pytest

from vision_measure.inspection.models import Calibration, Line, Point, Unit
from vision_measure.workspace.models import MeasurementRecord, ProjectDocument
from vision_measure.workspace.project import ProjectFormatError, load_project, save_project


def test_v2_project_round_trip(tmp_path) -> None:
    source = ProjectDocument(
        schema_version=2,
        magnifications=(
            (lambda m: m)(
                __import__(
                    "vision_measure.inspection.models", fromlist=["MagnificationProfile"]
                ).MagnificationProfile(
                    name="10x",
                    calibration=Calibration(0.5, Unit.MM),
                    scale_bar_length=10.0,
                )
            ),
        ),
        current_magnification="10x",
        records=(MeasurementRecord(Line(Point(1, 2), Point(3, 4)), "10x"),),
    )
    path = tmp_path / "project.json"
    save_project(path, source)
    loaded = load_project(path)
    assert loaded == source
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2


def test_v1_project_migrates_single_calibration(tmp_path) -> None:
    path = tmp_path / "v1.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lines": [{"start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}}],
                "unit": "mm",
                "calibration": {"units_per_pixel": 0.1, "unit": "mm"},
                "image_settings": {},
            }
        ),
        encoding="utf-8",
    )
    loaded = load_project(path)
    assert loaded.schema_version == 2
    assert [p.name for p in loaded.magnifications] == ["default"]
    assert loaded.current_magnification == "default"
    assert loaded.magnifications[0].calibration is not None
    assert loaded.records[0].magnification == "default"


def test_unknown_schema_version_is_rejected(tmp_path) -> None:
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(ProjectFormatError):
        load_project(path)
```

Extend `tests/unit/test_magnification.py` with workspace resolution tests if the
controller is touched; otherwise keep them in Task 3.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_project.py tests/unit/test_magnification.py -v`
Expected: FAIL because `MeasurementRecord` and the v2 fields do not exist.

- [ ] **Step 3: Implement the v2 model, serializer, and migration**

In `workspace/models.py`:

```python
from vision_measure.inspection.models import (
    DEFAULT_MAGNIFICATION_NAME,
    Calibration,
    Line,
    MagnificationProfile,
    Unit,
)


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    line: Line
    magnification: str


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    schema_version: int = 2
    magnifications: tuple[MagnificationProfile, ...] = ()
    current_magnification: str | None = None
    records: tuple[MeasurementRecord, ...] = ()
    image_settings: ImageSettings = ImageSettings()
```

In `project.py`, set `SCHEMA_VERSION = 2`, serialize `magnifications`,
`current_magnification`, and `records`, and add a `_migrate_v1(raw)` helper that
wraps the v1 `calibration` into one profile named
`DEFAULT_MAGNIFICATION_NAME`, maps v1 `lines` to records under that name, and
preserves `image_settings`. `load_project` calls `_migrate_v1` when
`schema_version == 1`, parses v2 directly, and raises `ProjectFormatError` for
any other version.

Update `workspace/controller.py` to the v2 model:

- `set_calibration` becomes `set_calibration(profile_name, calibration)` and
  stores the profile with `calibrated_at` left for the caller to fill.
- `add_line` appends `MeasurementRecord(line, current_magnification)` and
  returns it.
- `measurements` resolves each record's calibration from its
  `magnification` name, falling back to pixel units when the profile is
  uncalibrated.

- [ ] **Step 4: Run the full test suite**

Run: `$env:QT_QPA_PLATFORM='offscreen'; uv run pytest`
Expected: PASS after updating any tests that referenced the old `lines`,
`calibration`, and `unit` fields.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/workspace src/vision_measure/inspection tests
git commit -m "feat: add multi-magnification schema v2 with v1 migration"
```

### Task 3: Per-Magnification Calibration Switching

**Files:**
- Modify: `src/vision_measure/workspace/controller.py`
- Test: `tests/integration/test_magnification_workspace.py`

**Interfaces:**
- Consumes: `Workspace`, `SyntheticCameraBackend`, `MagnificationProfile`,
  `Calibration`, `Line`, `Point`, `Unit`.
- Produces: `Workspace.set_magnification(name)`, `Workspace.current_calibration`,
  and the invariant that switching magnification changes the active calibration
  without mutating existing `MeasurementRecord`s.

- [ ] **Step 1: Write the failing test**

```python
from vision_measure.inspection.models import Calibration, Line, Point, Unit
from vision_measure.workspace.controller import Workspace


def test_switching_magnification_switches_calibration() -> None:
    workspace = Workspace()
    workspace.set_magnification("4x")
    workspace.set_calibration("4x", Calibration(0.2, Unit.MM))
    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))
    workspace.set_magnification("4x")
    assert workspace.current_calibration.units_per_pixel == pytest.approx(0.2)
    workspace.set_magnification("10x")
    assert workspace.current_calibration.units_per_pixel == pytest.approx(0.05)


def test_records_keep_source_magnification() -> None:
    workspace = Workspace()
    workspace.set_magnification("4x")
    workspace.set_calibration("4x", Calibration(0.2, Unit.MM))
    workspace.add_line(Line(Point(0, 0), Point(10, 0)))
    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))
    workspace.add_line(Line(Point(0, 0), Point(20, 0)))
    assert workspace.records[0].magnification == "4x"
    assert workspace.measurements[0].physical_length == pytest.approx(2.0)
    assert workspace.measurements[1].physical_length == pytest.approx(1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_magnification_workspace.py -v`
Expected: FAIL for `set_magnification` and `current_calibration`.

- [ ] **Step 3: Implement switching**

Add `set_magnification(name)` that inserts a profile if missing and sets
`current_magnification`. Add a `current_calibration` property that returns the
active profile's `calibration` or `None`. Update `set_calibration` to write the
named profile with a current ISO `calibrated_at`. Update `add_line` and
`measurements` per Task 2.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_magnification_workspace.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/workspace/controller.py tests/integration/test_magnification_workspace.py
git commit -m "feat: switch per-magnification calibration without mutating records"
```

### Task 4: Fixed Physical Length Scale Bar Geometry

**Files:**
- Modify: `src/vision_measure/inspection/annotations.py`
- Test: `tests/unit/test_scale_bar.py`

**Interfaces:**
- Consumes: `Calibration`, `Unit`, `NormalizedPoint`, image dimensions.
- Produces: `scale_bar_geometry(calibration, length, unit, image_shape,
  position) -> ScaleBarGeometry` and a `ScaleBarTooLarge` error when the fixed
  length does not fit. Replaces the automatic `1/2/5 x 10^n` selection.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pytest

from vision_measure.inspection.annotations import ScaleBarTooLarge, scale_bar_geometry
from vision_measure.inspection.models import Calibration, Unit


def test_fixed_length_geometry_matches_unit_to_pixels() -> None:
    calibration = Calibration(units_per_pixel=0.1, unit=Unit.MM)
    geometry = scale_bar_geometry(
        calibration, length=10.0, unit=Unit.MM, image_shape=(1000, 2000), position=(0.05, 0.9)
    )
    assert geometry.pixel_length == pytest.approx(100.0)


def test_fixed_length_too_large_is_rejected() -> None:
    calibration = Calibration(units_per_pixel=0.1, unit=Unit.MM)
    with pytest.raises(ScaleBarTooLarge):
        scale_bar_geometry(
            calibration, length=10.0, unit=Unit.MM, image_shape=(1000, 500), position=(0.05, 0.9)
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_scale_bar.py -v`
Expected: FAIL because `scale_bar_geometry` and `ScaleBarTooLarge` do not exist.

- [ ] **Step 3: Implement fixed-length geometry**

Add `ScaleBarTooLarge(ValueError)`. Add `scale_bar_geometry` that computes the
pixel length from `calibration.unit_to_pixels(length)` after converting `length`
to the calibration unit, and raises `ScaleBarTooLarge` when it exceeds the
image width or height. Reuse this single geometry in the live canvas and in
`save_capture` so both render paths share one conversion.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_scale_bar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/inspection/annotations.py tests/unit/test_scale_bar.py
git commit -m "feat: add fixed physical length scale bar geometry"
```

### Task 5: Camera Configuration Change Invalidation

**Files:**
- Modify: `src/vision_measure/workspace/controller.py`
- Test: `tests/integration/test_camera_invalidation.py`

**Interfaces:**
- Consumes: `Workspace`, `CaptureConfig`, `FramePacket`.
- Produces: `Workspace.on_camera_changed(config)` that clears the affected
  calibration profile so a changed resolution or pixel format cannot silently
  reuse a stale calibration.

- [ ] **Step 1: Write the failing test**

```python
from vision_measure.camera.models import CaptureConfig
from vision_measure.inspection.models import Calibration, Unit
from vision_measure.workspace.controller import Workspace


def test_camera_change_invalidates_calibration() -> None:
    workspace = Workspace()
    workspace.set_magnification("10x")
    workspace.set_calibration("10x", Calibration(0.05, Unit.MM))
    workspace.on_camera_changed(CaptureConfig(width=1920, height=1080))
    assert workspace.current_calibration is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_camera_invalidation.py -v`
Expected: FAIL because `on_camera_changed` does not exist.

- [ ] **Step 3: Implement invalidation**

Track the `CaptureConfig` used for the current calibration and clear the current
profile's `calibration`/`calibrated_at` when `on_camera_changed` receives a
different width, height, or pixel format.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_camera_invalidation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/workspace/controller.py tests/integration/test_camera_invalidation.py
git commit -m "feat: invalidate calibration on camera configuration change"
```

### Task 6: Two-Click Calibration and Magnification UI

**Files:**
- Modify: `src/vision_measure/ui/panels.py`
- Modify: `src/vision_measure/ui/viewport.py`
- Modify: `src/vision_measure/ui/main_window.py`
- Test: `tests/ui/test_calibration_flow.py`

**Interfaces:**
- Consumes: `Workspace`, `MainWindow`, `ImageViewport`.
- Produces: a magnification selector, a "known length + unit -> Set calibration"
  form, a viewport calibration mode that emits `calibration_finished(Line)`,
  and an `未标定` placeholder for uncalibrated magnifications.

- [ ] **Step 1: Write the failing UI tests**

```python
from vision_measure.ui.main_window import MainWindow


def test_main_window_exposes_magnification_selector(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.magnification_selector.count() >= 4


def test_uncalibrated_shows_placeholder(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace.set_magnification("4x")
    assert window.calibration_status.text() == "未标定"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; uv run pytest tests/ui/test_calibration_flow.py -v`
Expected: FAIL because the selector and status attributes do not exist.

- [ ] **Step 3: Implement the controls**

Add `MagnificationPanel` and `CalibrationPanel` in `panels.py`. The calibration
panel has a numeric length field, a unit selector, and a `Set calibration`
button. Clicking it enters viewport calibration mode; two canvas clicks emit a
`Line`; the second click completes and exits. `main_window.py` only assembles
these panels and connects signals. Physical lengths under an uncalibrated
magnification render as `未标定`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; uv run pytest tests/ui -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/ui tests/ui
git commit -m "feat: add two-click calibration and magnification UI"
```

### Task 7: AI Subject Extraction Spike

**Files:**
- Create: `scripts/ai_spike.py`

**Interfaces:**
- Consumes: `rembg`, `onnxruntime`, and the `birefnet-general` model files.
- Produces: a standalone script that times mask generation on a frozen sample
  and prints model size, cold/warm latency (p50/p95), and peak private memory
  for the CPU path, plus a DirectML compatibility check.

- [ ] **Step 1: Run the spike against a sample frame**

Run: `uv run --with rembg --with onnxruntime python scripts/ai_spike.py`
Expected: printed metrics; no package changes to the application.

- [ ] **Step 2: Record metrics**

Record model file size, first-load time, p50/p95 inference time, and peak
private memory in the task notes. Do not state performance numbers that were
not measured.

- [ ] **Step 3: Commit the spike**

```bash
git add scripts/ai_spike.py
git commit -m "chore: add AI subject extraction spike"
```

### Task 8: Subject Extraction Boundary and Mask Cleanup

**Files:**
- Create: `src/vision_measure/subject_extraction/__init__.py`
- Create: `src/vision_measure/subject_extraction/mask.py`
- Create: `src/vision_measure/subject_extraction/rembg_extractor.py`
- Test: `tests/unit/test_mask_cleanup.py`

**Interfaces:**
- Consumes: NumPy arrays.
- Produces: `SubjectExtractor.extract(image) -> alpha_mask`,
  `cleanup_mask(alpha_mask, min_component_area, fill_holes)`.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from vision_measure.subject_extraction.mask import cleanup_mask


def test_cleanup_mask_drops_far_away_fragments_and_fills_holes() -> None:
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    mask[10:20, 10:20] = 0  # hole inside subject
    mask[50:52, 50:52] = 255  # far-away fragment
    cleaned = cleanup_mask(mask, min_component_area=20, fill_holes=True)
    assert cleaned[50, 50] == 0
    assert cleaned[15, 15] == 255
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_mask_cleanup.py -v`
Expected: FAIL because `cleanup_mask` does not exist.

- [ ] **Step 3: Implement the boundary**

`cleanup_mask` uses connected-component labeling to drop components smaller
than `min_component_area` and a hole-filling pass for interior holes.
`RemBgExtractor` implements `SubjectExtractor` and returns an alpha mask; it
must not run at import time and must raise a typed error when the model is
missing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_mask_cleanup.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/subject_extraction tests/unit/test_mask_cleanup.py
git commit -m "feat: add subject extraction boundary and mask cleanup"
```

### Task 9: AI Screenshot Preview and Fallback

**Files:**
- Modify: `src/vision_measure/workspace/controller.py`
- Modify: `src/vision_measure/ui/panels.py`
- Test: `tests/integration/test_ai_fallback.py`

**Interfaces:**
- Consumes: `SubjectExtractor`, `Workspace`.
- Produces: `Workspace.capture_with_subject(extractor) -> np.ndarray` that
  returns the composite or falls back to the ordinary frame on any failure,
  and a screenshot preview showing original, mask, and composite before saving.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from vision_measure.camera.models import FramePacket
from vision_measure.subject_extraction import SubjectExtractor
from vision_measure.workspace.controller import Workspace


class ExplodingExtractor:
    def extract(self, image: np.ndarray) -> np.ndarray:
        raise RuntimeError("boom")


def test_ai_failure_falls_back_to_original() -> None:
    workspace = Workspace()
    workspace._current = FramePacket(np.zeros((8, 8, 3), dtype=np.uint8), 1)
    result = workspace.capture_with_subject(ExplodingExtractor())
    assert result.shape == (8, 8, 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_ai_fallback.py -v`
Expected: FAIL because `capture_with_subject` does not exist.

- [ ] **Step 3: Implement capture with fallback**

`capture_with_subject` catches any `Exception` from the extractor and returns
the processed original frame. Add the preview dialog in `panels.py` that shows
original, mask, and composite and allows saving the original when AI is
disabled.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_ai_fallback.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vision_measure/workspace src/vision_measure/ui tests/integration/test_ai_fallback.py
git commit -m "feat: add AI screenshot preview with original fallback"
```

### Task 10: Packaging and 0.3.0 Release

**Files:**
- Modify: `pyproject.toml`, `src/vision_measure/__init__.py`,
  `packaging/windows-version-info.txt`, `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Consumes: the complete package.
- Produces: `0.3.0` wheel/sdist, a PyInstaller single-file EXE that passes
  `--smoke-test`, and a GitHub Release with EXE, ZIP, checksums, and model
  artifacts.

- [ ] **Step 1: Bump versions and run the full gate**

Run: `uv run ruff check .`, `uv run mypy src`,
`$env:QT_QPA_PLATFORM='offscreen'; uv run pytest`, `uv build`.
Expected: all pass.

- [ ] **Step 2: Build and smoke-test the EXE**

Run: `pwsh -NoProfile -File scripts\build_windows.ps1 -Version 0.3.0`
Expected: `--smoke-test` exits 0.

- [ ] **Step 3: Verify on a real eyepiece**

Open a real eyepiece, switch magnifications, calibrate one, measure, and save a
screenshot with the scale bar. Record backend, resolution, pixel format, and
startup time. Report only observed behavior.

- [ ] **Step 4: Commit, push, and release**

Commit the version bump, push `main`, create the `v0.3.0` GitHub Release, and
upload EXE, ZIP, `SHA256SUMS.txt`, and model artifacts with their licenses.
