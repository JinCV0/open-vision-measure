# Open Vision Measure

Open Vision Measure is a local-first camera inspection and measurement
workbench. It is an independent, clean-room implementation inspired by the
workflow of camera measurement software; it does not contain code, assets, or
models from JCameraPro.

## Core MVP

- Camera discovery through MSMF, DirectShow, or V4L2 with automatic fallback.
- Bounded, non-blocking camera acquisition.
- Live preview, freeze/resume, stop, and screenshot export.
- Brightness, contrast, temperature, tint, grayscale, and edge preview.
- Two-click line measurement in image coordinates.
- Physical calibration from a known reference length.
- Optional draggable academic-style scale bar in live and saved images.
- Persistent screenshot folder with automatic `capture_0001` sequencing.
- Project save/load and CSV measurement export.
- Unicode Windows paths for screenshots and project files.

AI processing, recording, Excel reports, licensing, payment, updates, and
telemetry are intentionally deferred.

## Install and run

Python 3.12 and `uv` are required.

```powershell
uv sync --extra dev
uv run vision-measure
```

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
pwsh -NoProfile -File scripts/build_windows.ps1 -Version 0.2.0
```

The command builds `OpenVisionMeasure.exe`, runs its packaged smoke test,
calculates SHA-256, and creates a distributable ZIP under
`release/0.2.0/windows-x64/`.

## Documents

- [Core MVP design](docs/superpowers/specs/2026-11-02-open-vision-measure-design.md)
- [Implementation plan](docs/superpowers/plans/2026-11-02-core-mvp.md)

## License

Apache-2.0.
