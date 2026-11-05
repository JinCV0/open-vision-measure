# Contributing

Open Vision Measure is an Apache-2.0, local-first desktop application for
microscope imaging, calibration, measurement, and capture workflows.

## Development setup

Requirements:

- Python 3.12
- `uv`
- A camera supported by OpenCV, or the synthetic camera test backend

```powershell
uv sync --extra dev
uv run vision-measure
```

## Validation

Run the full local gate:

```powershell
uv run ruff check .
uv run mypy src
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
uv build
```

Hardware-specific observations must be reported separately from automated test
results. Synthetic-camera tests do not establish real camera compatibility.

## Scope and design rules

- Keep camera acquisition, measurement logic, persistence, and Qt UI concerns
  in their existing module boundaries.
- Preserve user data and project schema compatibility. Add explicit migrations
  instead of silently changing stored meanings.
- Keep expected failures typed and user-visible.
- Do not add decorative UI or explanatory copy beyond the requested workflow.
- Do not commit credentials, personal paths, generated builds, capture data, or
  local planning artifacts.

## Out-of-scope AI contributions

The current product intentionally excludes AI background removal, model
runtimes, and model weights. Users may build independent extensions, but this
repository does not ship or accept model artifacts as part of the core
application. A future proposal must define scope, runtime, privacy, licensing,
and hardware verification before implementation.

## Pull requests

Keep changes focused. Describe:

- the observable problem;
- the behavior after the change;
- tests and manual checks actually executed;
- checks that were not possible or remain unverified;
- any schema, data, packaging, or hardware impact.

AI-assisted contributions are welcome, but a human must review the final diff
and remain responsible for its correctness.

## Reporting issues

Use the issue templates when available. Include the application version,
Windows version, camera model and backend, exact reproduction steps, and the
smallest useful error output. Do not include secrets or unrelated personal data.
