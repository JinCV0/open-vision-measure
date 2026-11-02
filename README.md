# Open Vision Measure

Open Vision Measure is a local-first camera inspection and measurement
workbench. The core MVP covers camera preview, freeze/resume, screenshots,
calibrated line measurements, project persistence, and CSV export.

AI processing, recording, Excel reports, licensing, payment, updates, and
telemetry are intentionally deferred.

## Development

```powershell
uv sync --extra dev
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
```

Launch the desktop application on Windows:

```powershell
uv run vision-measure
```

The approved design and implementation plan are in
`docs/superpowers/specs/2026-11-02-open-vision-measure-design.md` and
`docs/superpowers/plans/2026-11-02-core-mvp.md`.
