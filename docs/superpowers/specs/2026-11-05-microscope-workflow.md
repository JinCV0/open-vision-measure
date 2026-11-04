# Open Vision Measure — Microscope Workflow Design (0.3.0)

Date: 2026-11-05
Status: Direction approved; specification under implementation
License: Apache-2.0

## 1. Objective

Pivot the camera measurement workbench toward a microscope electronic-eyepiece
workstation for plant tissue sections. A user connects an eyepiece camera,
manually selects the objective magnification, calibrates each magnification
independently, measures tissue features with a calibrated physical scale bar,
and captures screenshots for papers and teaching. Original frames are always
preserved; AI subject extraction is an optional, graceful-degrading enhancement.

## 2. Product Boundary

### Included (0.3.0)

- Connect an electronic eyepiece and auto-select the best camera mode.
- User-maintained magnification list (at least `4x`/`10x`/`40x`/`100x`).
- Independent `pixels-per-unit` calibration per magnification.
- New two-click calibration flow: enter known physical length, then click the
  reference endpoints on the canvas.
- Fixed physical length scale bar, draggable, shared between live canvas and
  saved screenshots.
- Plant-tissue measurements: layer thickness (line), point-to-point distance,
  area/perimeter, vessel/cell/lacuna diameter, count, and mean/std/min/max.
- Measurement records keep the magnification they were measured under.
- Screenshot with scale bar and magnification label; original frame preserved.
- Optional AI subject extraction with transparent/white-background output.
- Schema migration from v1 projects without silently applying a single v1
  calibration to all magnifications.

### Deferred

- Automatic magnification recognition.
- Fluorescence, polarization, confocal, or motorized-stage support.
- Automatic cell counting, automatic tissue-layer recognition, section
  classification.
- Recording, Excel, PDF, licensing, payment, multi-language, updates, cloud.

## 3. Confirmed Decisions

1. **Calibration interaction** — right panel: enter known physical length and
   unit, click `Set calibration`, then click two reference endpoints on the
   canvas; the second click completes and exits calibration mode. The previous
   "last line + Calibrate last line" interaction is removed.
2. **Uncalibrated magnification** — pixel measurement is always available;
   physical length/area show an `未标定` placeholder under an uncalibrated
   magnification, with a prominent `标定此倍率` entry. Switching magnification
   never mutates historical records.
3. **AI screenshot modes (v1)** — original image (always available) and
   white-background clean image. Transparent PNG is a cheap add-on because the
   alpha mask is already produced. Darkened-background highlighting is deferred.

## 4. Technology

- Python 3.12, `uv`, PySide6, OpenCV, NumPy.
- `rembg` + `birefnet-general` for subject extraction (spike first).
- ONNX Runtime CPU by default; DirectML only after a measured-compatible spike.
- pytest, pytest-qt, Ruff, mypy.

## 5. Architecture

The four existing modules keep their direction; magnification and AI land
without growing `ui/main_window.py` (currently ~388 lines).

### 5.1 `inspection`

Owns magnification configuration, per-magnification calibration conversion,
fixed-physical-length scale-bar geometry, and AI mask post-processing as pure,
Qt-free data and computation.

```python
@dataclass(frozen=True, slots=True)
class MagnificationProfile:
    name: str
    calibration: Calibration | None = None
    calibrated_at: str | None = None
    reference_length: float | None = None
    scale_bar_length: float | None = None
```

### 5.2 `workspace`

Owns switching the current magnification, detecting camera configuration
changes, triggering re-calibration, the screenshot pipeline, and persisting the
multi-magnification project. Model loading, inference, and image algorithms stay
out.

### 5.3 `ui`

Owns magnification/calibration controls and the screenshot preview. It only
collects input, renders, and forwards events.

### 5.4 `subject_extraction` (new boundary)

```python
class SubjectExtractor(Protocol):
    def extract(self, image: np.ndarray) -> np.ndarray: ...
```

The v1 implementation uses `rembg + birefnet-general` in a controlled worker so
a missing model, inference failure, or worker crash cannot freeze the UI. Any
failure falls back to the ordinary screenshot path.

## 6. Domain Model and Schema

`inspection/models.py` adds `MagnificationProfile` and
`DEFAULT_MAGNIFICATION_NAME = "default"`.

`workspace/models.py` replaces `lines` with records that carry their source
magnification:

```python
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

The v1 `unit` and `calibration` top-level fields are removed. Unit is now carried
by each magnification's `Calibration`.

### Schema v1 -> v2 migration

- `schema_version` becomes `2`.
- The v1 single `calibration` becomes one `MagnificationProfile` named
  `DEFAULT_MAGNIFICATION_NAME`, with `calibrated_at=None`,
  `reference_length=None`, `scale_bar_length=None`.
- v1 `lines` become `records` whose `magnification` is
  `DEFAULT_MAGNIFICATION_NAME`.
- `current_magnification` is set to `DEFAULT_MAGNIFICATION_NAME`.
- `image_settings` is preserved.

`load_project` must read v1 and v2. An unknown schema version raises
`ProjectFormatError`. A v1 calibration is never silently copied onto every
magnification.

## 7. Calibration and Scale Bar

The new calibration flow is:

1. User enters a known physical length and unit.
2. User clicks `Set calibration`.
3. User clicks the reference endpoints on the canvas.
4. The second click completes calibration and exits calibration mode.

The scale bar uses a user-specified fixed physical length (for example
`10 mm`). When the current magnification is calibrated, the drawn length is
`calibration.unit_to_pixels(length)`. Live preview and saved screenshots must
use the same geometry function from `inspection/annotations.py`. If the fixed
length does not fit the canvas, it is rejected explicitly rather than silently
replaced with a "nicer" length. The scale bar default position is bottom-left,
dragged position persists in normalized image coordinates.

## 8. AI Screenshot Pipeline

1. Freeze the original frame; keep it immutable.
2. Generate a subject alpha mask with `rembg + birefnet-general`.
3. Clean the mask morphologically: drop small far-away connected components,
   fill small holes inside the subject, and flag large tissue fragments for
   manual confirmation.
4. Background fluff and bubbles disappear through background replacement.
5. Bubbles or impurities inside the subject body are not removed by the alpha
   mask; v1 must not claim automatic removal.
6. Show original, mask, and composite before saving; allow turning AI off and
   exporting the original.
7. Missing model, timeout, out-of-memory, or worker failure falls back to the
   normal screenshot.

## 9. Error Handling

Typed errors are used for expected failures. Uncalibrated physical measurement
is a placeholder, not an error. Camera configuration change invalidates the
affected magnification rather than silently reusing a stale calibration. A
failed save never modifies the previous project file.

## 10. Testing

- Unit: `MagnificationProfile` validation, v1->v2 migration, per-magnification
  conversion, fixed scale-bar geometry, mask cleanup.
- Integration: workspace switching magnifications, measurement records keeping
  source magnification, project round trip for v1 and v2, camera-config-change
  invalidation.
- UI: offscreen two-click calibration flow, uncalibrated placeholder, scale-bar
  drag persistence.
- Acceptance: a real eyepiece camera and at least 20 real plant-tissue sections
  with different staining, magnification, bubbles, and impurities. Synthetic
  cameras and mocked segmenters do not establish real-hardware or real-model
  behavior.

## 11. 0.3.0 Acceptance

- Open an eyepiece and record backend, resolution, pixel format, and startup
  time.
- Switch at least `4x`/`10x`/`40x`/`100x`, each independently calibrated.
- Switching magnification does not rewrite historical records' magnification.
- Camera resolution/format change does not silently reuse a stale calibration.
- New calibration uses only two canvas clicks.
- Fixed scale bar matches between live canvas and screenshots.
- v1 and v2 project load, save, and reload pass automated tests.
- Original frame is always saveable; AI output never overwrites it.
- Background fluff/bubbles disappear via background replacement; internal
  bubbles are not falsely claimed removed.
- Packaging runs offline with no first-run model download; model source,
  version, SHA-256, and license are recorded.

## 12. Risks

1. `rembg`/`birefnet-general` increases package size, cold start, and memory.
2. ONNX Runtime, multiprocessing worker, and Qt plugins may conflict under
   PyInstaller.
3. Multi-magnification schema touches historical data; migration must keep old
   projects loadable.
4. A scale bar length that does not fit must be rejected, not silently adjusted.
