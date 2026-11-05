# Scale Bar Studio Design

Date: 2026-11-05
Status: Approved
License: Apache-2.0

## 1. Objective

Replace the basic fixed scale-bar controls with a dedicated Material You settings
window that provides live preview, presets, shape and color customization,
precise sizing, orientation, label controls, and nine-position placement.

The scale-bar value remains scientifically tied to the active magnification
calibration. Styling must never change the physical length represented by the
bar.

## 2. Product Boundary

The feature includes:

- A `比例尺设置…` button in the Calibration card.
- A separate modal `QDialog`.
- A preview using the current camera frame, or a synthetic fallback.
- Five presets.
- Shape, orientation, label, color, background, width, and tick controls.
- A 3x3 placement shortcut.
- Per-magnification scale-bar length.
- Global visual style and position preferences.
- Matching style in the live viewport and saved screenshots.

The feature excludes:

- Arbitrary label text.
- False or independently editable physical values.
- AI processing.
- Animated or decorative overlays unrelated to the scale bar.

## 3. Style Model

The immutable `ScaleBarStyle` contains:

```text
shape: line | ticks | segmented | bracket
orientation: horizontal | vertical
label_position: above | below
background: none | translucent | solid
line_color
outline_color
label_color
background_color
opacity
background_opacity
line_width
tick_length
label_size
show_outline
show_label
segments
```

All numeric values are validated. Colors use `#RRGGBB`.

The five presets are:

- `简洁线`
- `科研描边`
- `分段标尺`
- `Material 绿`
- `紧凑括号`

## 4. Persistence

Preferences schema v2 adds a serialized global `scale_bar_style`. Schema v1
preferences load with the scientific preset. The scale-bar length remains part
of each magnification profile in the project document.

Changing the calibration unit still invalidates the old calibration. Selecting
a preset or changing style never changes calibration.

## 5. Window

The window uses two columns:

- Left: large preview.
- Right: scrollable controls grouped into Preset, Shape, Size, Label, Color,
  Background, Position.

Footer actions:

- `恢复默认`
- `取消`
- `应用`

The preview updates immediately while editing. Preferences and the main canvas
change only after `应用`.

## 6. Rendering

The same geometry and style object drive both renderers:

- `ui/scale_bar_painter.py` draws the live canvas through Qt.
- `inspection/scale_bar_renderer.py` draws with OpenCV for previews and
  screenshots.

Horizontal and vertical geometry use the same physical length conversion and
bounds checking. If the bar does not fit, the operation fails rather than
silently substituting another length.

## 7. Placement

The dialog exposes nine normalized positions:

```text
left-top     center-top     right-top
left-middle  center-middle  right-middle
left-bottom  center-bottom  right-bottom
```

Drag position remains available in the main viewport and is preserved when the
dialog opens.

## 8. Validation

- Existing project and preference migrations remain readable.
- A custom style round-trips through preferences JSON.
- Presets produce valid styles.
- Vertical and horizontal geometry fit and reject overlong bars.
- Dialog Apply persists style, position, and current magnification length.
- Live viewport and saved screenshots use the selected style.
- Light and dark themes render without clipping.
- Scale-bar tests remain independent of AI code.
