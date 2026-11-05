# Open Vision Measure

Open Vision Measure is a local-first microscope imaging and measurement
workbench for plant tissue sections. It is an independent, clean-room
implementation inspired by the workflow of camera measurement software; it does
not contain code, assets, or models from JCameraPro.

## Core MVP

- Camera discovery through MSMF, DirectShow, or V4L2 with automatic fallback.
- Automatic highest-resolution, best-format camera mode by default.
- Bounded, non-blocking camera acquisition.
- Live preview, freeze/resume, stop, and screenshot export.
- Brightness, contrast, temperature, tint, grayscale, and edge preview.
- Two-click line measurement in image coordinates.
- Per-magnification physical calibration from a two-click reference.
- Optional draggable fixed-length scale bar in live and saved images.
- Persistent screenshot folder with automatic `capture_0001` sequencing.
- Project save/load and CSV measurement export.
- Unicode Windows paths for screenshots and project files.
- Optional BiRefNet subject extraction with original, mask, and cleaned previews.

Recording, area/perimeter tools, Excel reports, licensing, payment, updates, and
telemetry remain deferred.

## Install and run

Python 3.12 and `uv` are required.

```powershell
uv sync --extra dev
uv run vision-measure
```

For the optional AI runtime:

```powershell
uv sync --extra dev --extra ai
```

The AI runtime does not download or redistribute a model weight. After verifying
the weight's own license, place `birefnet-general.onnx` at:

```text
%USERPROFILE%\.rembg\models\birefnet-general\birefnet-general.onnx
```

If the runtime or model is unavailable, AI screenshot uses the ordinary original
image and disables the cleaned-image save action.

On a Windows machine with a camera that is exposed through DirectShow, choose
`Refresh`, select the camera, and click `Start`. The combined camera label shows
the backend that was detected.

## Test

```powershell
uv run ruff check .
uv run mypy src
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
```

Synthetic-camera tests establish deterministic workflows. They do not prove
compatibility with a specific physical camera or driver.

## Build Windows executable

```powershell
pwsh -NoProfile -File scripts/build_windows.ps1 -Version 0.3.0 -WithAI
```

The command builds `OpenVisionMeasure.exe`, runs its packaged smoke test,
calculates SHA-256, and creates a distributable ZIP under
`release/0.3.0/windows-x64/`. Omit `-WithAI` to build the smaller package without
the AI runtime; the application remains usable through original-image fallback.

## Documents

- [Core MVP design](docs/superpowers/specs/2026-11-02-open-vision-measure-design.md)
- [Implementation plan](docs/superpowers/plans/2026-11-02-core-mvp.md)
- [Microscope workflow spec](docs/superpowers/specs/2026-11-05-microscope-workflow.md)
- [AI spike measurements](docs/ai-spike-2026-11-05.md)

## License

Apache-2.0.
