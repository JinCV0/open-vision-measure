from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vision_measure.inspection.annotations import (
    DEFAULT_SCALE_BAR_POSITION,
    NormalizedPoint,
)

SCHEMA_VERSION = 1
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class PreferencesFormatError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AppPreferences:
    screenshot_directory: Path | None = None
    screenshot_extension: str = ".png"
    scale_bar_enabled: bool = False
    scale_bar_position: NormalizedPoint = DEFAULT_SCALE_BAR_POSITION

    def __post_init__(self) -> None:
        extension = self.screenshot_extension.lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        if extension not in IMAGE_EXTENSIONS:
            raise ValueError("unsupported screenshot extension")
        object.__setattr__(self, "screenshot_extension", extension)


def default_preferences_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "OpenVisionMeasure" / "preferences.json"
    return Path.home() / ".config" / "open-vision-measure" / "preferences.json"


class PreferencesStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> AppPreferences:
        if not self.path.exists():
            return AppPreferences()
        try:
            raw: Any = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
                raise PreferencesFormatError("unsupported preferences schema")
            position = raw.get("scale_bar_position", {})
            directory = raw.get("screenshot_directory")
            return AppPreferences(
                screenshot_directory=None if directory is None else Path(directory),
                screenshot_extension=str(raw.get("screenshot_extension", ".png")),
                scale_bar_enabled=bool(raw.get("scale_bar_enabled", False)),
                scale_bar_position=NormalizedPoint(
                    float(position.get("x", DEFAULT_SCALE_BAR_POSITION.x)),
                    float(position.get("y", DEFAULT_SCALE_BAR_POSITION.y)),
                ),
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PreferencesFormatError("cannot read preferences") from exc

    def save(self, preferences: AppPreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "screenshot_directory": (
                None
                if preferences.screenshot_directory is None
                else str(preferences.screenshot_directory)
            ),
            "screenshot_extension": preferences.screenshot_extension,
            "scale_bar_enabled": preferences.scale_bar_enabled,
            "scale_bar_position": {
                "x": preferences.scale_bar_position.x,
                "y": preferences.scale_bar_position.y,
            },
        }
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                temporary = Path(stream.name)
            os.replace(temporary, self.path)
        except OSError as exc:
            raise PreferencesFormatError("cannot save preferences") from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
