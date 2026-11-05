# Scale Bar Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated Material You scale-bar settings window with rich visual customization, live preview, persistence, and matching live/saved rendering.

**Architecture:** Add an immutable style model in `inspection`, persist it through preferences schema v2, render with shared geometry in Qt and OpenCV, and isolate the separate window behind `ScaleBarSettingsController`. The main Calibration card exposes only the scale-bar switch and settings button.

**Tech Stack:** Python 3.12, PySide6, OpenCV, NumPy, pytest, pytest-qt, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-11-05-scale-bar-studio.md`

## Global Constraints

- Apache-2.0 only.
- Keep AI features removed.
- Physical length is derived from the active magnification calibration.
- Never substitute a different value when the chosen bar does not fit.
- Apply style and position globally; apply length per magnification.
- Reuse the Material You theme and 4/8/12/16/24 spacing.
- Keep `ui/main_window.py` at or below 400 lines.

---

### Task 1: Scale Bar Style Model and Presets

**Files:**
- Create: `src/vision_measure/inspection/scale_bar.py`
- Create: `tests/unit/test_scale_bar_style.py`

**Interfaces:**

```python
class ScaleBarShape(StrEnum): ...
class ScaleBarOrientation(StrEnum): ...
class ScaleBarLabelPosition(StrEnum): ...
class ScaleBarBackground(StrEnum): ...
class ScaleBarPreset(StrEnum): ...

@dataclass(frozen=True, slots=True)
class ScaleBarStyle: ...

DEFAULT_SCALE_BAR_STYLE: ScaleBarStyle

def scale_bar_preset(preset: ScaleBarPreset) -> ScaleBarStyle: ...
def scale_bar_style_to_json(style: ScaleBarStyle) -> dict[str, object]: ...
def scale_bar_style_from_json(raw: object) -> ScaleBarStyle: ...
```

- [ ] **Step 1: Write failing style tests**

```python
def test_presets_are_valid_and_distinct() -> None:
    styles = {preset: scale_bar_preset(preset) for preset in ScaleBarPreset}
    assert len(set(styles.values())) == len(ScaleBarPreset)
    assert styles[ScaleBarPreset.SEGMENTED].shape is ScaleBarShape.SEGMENTED

def test_style_rejects_invalid_color() -> None:
    with pytest.raises(ValueError):
        ScaleBarStyle(line_color="white")

def test_style_round_trips_json() -> None:
    style = scale_bar_preset(ScaleBarPreset.MATERIAL)
    assert scale_bar_style_from_json(scale_bar_style_to_json(style)) == style
```

- [ ] **Step 2: Run tests and verify missing imports**

`uv run pytest tests/unit/test_scale_bar_style.py -v`

- [ ] **Step 3: Implement enums, immutable style, validation, presets, JSON**

Color regex: `^#[0-9a-fA-F]{6}$`.

Numeric bounds:

```text
opacity, background_opacity: 0..1
line_width: 1..20
tick_length: 0..80
label_size: 8..96
segments: 2..12
```

- [ ] **Step 4: Run focused tests**

`uv run pytest tests/unit/test_scale_bar_style.py -v`

- [ ] **Step 5: Commit**

`git commit -m "feat: add scale bar style model"`

---

### Task 2: Preferences Schema v2

**Files:**
- Modify: `src/vision_measure/workspace/preferences.py`
- Modify: `tests/unit/test_preferences.py`

**Consumes:** `ScaleBarStyle`, `DEFAULT_SCALE_BAR_STYLE`,
`scale_bar_style_to_json`, `scale_bar_style_from_json`.

**Produces:** `AppPreferences.scale_bar_style` and schema v1 migration.

- [ ] **Step 1: Write failing migration and round-trip tests**

```python
def test_v1_preferences_load_default_scale_bar_style(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps({"schema_version": 1, "scale_bar_position": {"x": 0.2, "y": 0.8}}),
        encoding="utf-8",
    )
    assert PreferencesStore(path).load().scale_bar_style == DEFAULT_SCALE_BAR_STYLE

def test_custom_scale_bar_style_round_trips(tmp_path: Path) -> None:
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    path = tmp_path / "preferences.json"
    store = PreferencesStore(path)
    store.save(AppPreferences(scale_bar_style=style))
    assert store.load().scale_bar_style == style
```

- [ ] **Step 2: Run tests and verify failure**

`uv run pytest tests/unit/test_preferences.py -v`

- [ ] **Step 3: Implement schema v2**

Set `SCHEMA_VERSION = 2`; accept `1` and `2` when loading. Version 1 uses
`DEFAULT_SCALE_BAR_STYLE`. Save style under `scale_bar_style`.

- [ ] **Step 4: Run tests**

`uv run pytest tests/unit/test_preferences.py -v`

- [ ] **Step 5: Commit**

`git commit -m "feat: persist scale bar styles"`

---

### Task 3: Styled Geometry and Screenshot Rendering

**Files:**
- Modify: `src/vision_measure/inspection/scale_bar.py`
- Modify: `src/vision_measure/workspace/screenshot.py`
- Modify: `tests/unit/test_scale_bar_style.py`
- Modify: `tests/unit/test_screenshot.py`

**Consumes:** `ScaleBarStyle`, `Calibration`, `NormalizedPoint`.

**Produces:**

```python
@dataclass(frozen=True, slots=True)
class ScaleBarLayout:
    geometry: ScaleBarGeometry
    style: ScaleBarStyle

def build_scale_bar_layout(
    image_width: int,
    image_height: int,
    calibration: Calibration,
    length: float,
    position: NormalizedPoint,
    style: ScaleBarStyle,
) -> ScaleBarLayout: ...

def render_scale_bar(
    image: np.ndarray,
    calibration: Calibration,
    length: float,
    position: NormalizedPoint,
    style: ScaleBarStyle,
) -> np.ndarray: ...
```

- [ ] **Step 1: Write failing geometry and rendering tests**

```python
def test_vertical_scale_bar_uses_image_height() -> None:
    style = replace(
        DEFAULT_SCALE_BAR_STYLE,
        orientation=ScaleBarOrientation.VERTICAL,
    )
    layout = build_scale_bar_layout(
        1000, 1000, Calibration(0.1, Unit.MM), 10.0, NormalizedPoint(0.2, 0.2), style
    )
    assert layout.geometry.end.y - layout.geometry.start.y == pytest.approx(100.0)
    assert layout.geometry.end.x == pytest.approx(layout.geometry.start.x)

def test_segmented_render_keeps_dimensions() -> None:
    image = np.zeros((200, 300, 3), dtype=np.uint8)
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    rendered = render_scale_bar(
        image, Calibration(0.1, Unit.MM), 10.0, NormalizedPoint(0.1, 0.8), style
    )
    assert rendered.shape == image.shape
    assert np.count_nonzero(rendered) > 0
```

- [ ] **Step 2: Run focused tests and verify failure**

`uv run pytest tests/unit/test_scale_bar_style.py tests/unit/test_screenshot.py -v`

- [ ] **Step 3: Implement layout and renderer**

Support horizontal and vertical bars and four shapes. Apply line outline,
label placement, text size, transparent/solid backgrounds, opacity, colors, and
segment count. Raise `ScaleBarTooLong` when the bar does not fit.

- [ ] **Step 4: Add `scale_bar_style` to `save_capture` and renderer call**

- [ ] **Step 5: Run focused tests**

`uv run pytest tests/unit/test_scale_bar_style.py tests/unit/test_screenshot.py -v`

- [ ] **Step 6: Commit**

`git commit -m "feat: render customizable scale bars"`

---

### Task 4: Preview and Settings Dialog

**Files:**
- Create: `src/vision_measure/ui/scale_bar_preview.py`
- Create: `src/vision_measure/ui/scale_bar_dialog.py`
- Create: `tests/ui/test_scale_bar_dialog.py`

**Consumes:** style model, `render_scale_bar`, current image, length, unit,
position.

**Produces:**

```python
class ScaleBarPreview(QWidget): ...

class ScaleBarDialog(QDialog):
    def selected_style(self) -> ScaleBarStyle: ...
    def selected_position(self) -> NormalizedPoint: ...
    def selected_length(self) -> float: ...
    def selected_unit(self) -> Unit: ...
```

- [ ] **Step 1: Write failing dialog tests**

```python
def test_preset_changes_dialog_style(qtbot) -> None:
    dialog = ScaleBarDialog(
        image=np.zeros((180, 320, 3), dtype=np.uint8),
        unit=Unit.UM,
        length=10.0,
        style=DEFAULT_SCALE_BAR_STYLE,
        position=NormalizedPoint(0.04, 0.92),
    )
    qtbot.addWidget(dialog)
    dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData(ScaleBarPreset.SEGMENTED))
    assert dialog.selected_style().shape is ScaleBarShape.SEGMENTED

def test_position_grid_updates_selected_position(qtbot) -> None:
    dialog = ScaleBarDialog(
        image=None,
        unit=Unit.MM,
        length=10.0,
        style=DEFAULT_SCALE_BAR_STYLE,
        position=NormalizedPoint(0.04, 0.92),
    )
    qtbot.addWidget(dialog)
    dialog.position_buttons["right-top"].click()
    assert dialog.selected_position().x > 0.8
    assert dialog.selected_position().y < 0.2
```

- [ ] **Step 2: Run tests and verify failure**

`$env:QT_QPA_PLATFORM='offscreen'; uv run pytest tests/ui/test_scale_bar_dialog.py -v`

- [ ] **Step 3: Implement preview**

Use current BGR frame when available, otherwise a synthetic sample. Render
through `render_scale_bar` and scale to the widget with `QImage`.

- [ ] **Step 4: Implement dialog**

Two columns, scrollable controls, five presets, four shapes, orientation,
position, size, label, colors, background, reset/cancel/apply. Use the existing
Material theme; no local QSS.

- [ ] **Step 5: Run UI tests**

- [ ] **Step 6: Commit**

`git commit -m "feat: add scale bar studio window"`

---

### Task 5: Product Integration and Shared Rendering

**Files:**
- Create: `src/vision_measure/ui/scale_bar_controller.py`
- Modify: `src/vision_measure/ui/panels.py`
- Modify: `src/vision_measure/ui/microscope.py`
- Modify: `src/vision_measure/ui/viewport.py`
- Modify: `src/vision_measure/ui/main_window.py`
- Modify: `src/vision_measure/ui/screenshot_flow.py`
- Modify: `tests/ui/test_calibration_flow.py`
- Modify: `tests/ui/test_viewport.py`
- Modify: `tests/ui/test_main_window.py`

**Consumes:** `ScaleBarDialog`, style model, preferences callbacks.

**Produces:** Main Calibration card shows `比例尺` and `比例尺设置…`; viewport
receives the selected style; Apply persists style, position, and length.

- [ ] **Step 1: Write failing integration tests**

```python
def test_scale_bar_settings_button_requires_calibration(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert not window.calibration_panel.scale_bar_settings_button.isEnabled()

def test_applied_style_reaches_viewport(qtbot) -> None:
    workspace = Workspace()
    workspace.set_reference(Line(Point(0, 0), Point(100, 0)), 10.0, Unit.UM)
    window = MainWindow(workspace=workspace, auto_discover=False)
    qtbot.addWidget(window)
    style = scale_bar_preset(ScaleBarPreset.SEGMENTED)
    window.scale_bar_settings.applied.emit(style, 12.0, NormalizedPoint(0.3, 0.4))
    assert window.viewport.scale_bar_style == style
```

- [ ] **Step 2: Run focused tests and verify failure**

- [ ] **Step 3: Replace main-panel length controls with settings button**

Keep the checkbox. Disable settings until calibration exists. When enabling with
no stored length, use `10.0` in the current calibration unit.

- [ ] **Step 4: Implement `ScaleBarSettingsController`**

Open dialog with current frame, unit, length, style, and position. On apply:

```python
workspace.set_scale_bar_length(length)
updated = replace(
    preferences,
    scale_bar_enabled=True,
    scale_bar_position=position,
    scale_bar_style=style,
)
```

Emit `applied`.

- [ ] **Step 5: Update viewport and screenshot calls**

Viewport and screenshot render the selected style. Preserve drag and hit-test.

- [ ] **Step 6: Preserve style when other preferences change**

Use `dataclasses.replace` for screenshot folder, switch, and position updates.

- [ ] **Step 7: Run full tests**

`$env:QT_QPA_PLATFORM='offscreen'; uv run pytest`

- [ ] **Step 8: Commit**

`git commit -m "feat: integrate scale bar studio"`

---

### Task 6: Visual and Release Verification

**Files:**
- Modify: `README.md`
- Modify: `HANDOFF.md`
- Modify: `docs/images/micrometre-workflow.png`

- [ ] **Step 1: Render light and dark screenshots**

Verify the main Calibration card and the settings dialog at 100% and 150%.

- [ ] **Step 2: Run project gates**

```powershell
uv run ruff check .
uv run mypy src
$env:QT_QPA_PLATFORM='offscreen'
uv run pytest
uv build
pwsh -NoProfile -File scripts\build_windows.ps1 -Version 0.3.0
```

- [ ] **Step 3: Update documentation and release hashes**

- [ ] **Step 4: Commit and push public main**

`git commit -m "docs: document scale bar studio"`

Push `main` only after verification.
