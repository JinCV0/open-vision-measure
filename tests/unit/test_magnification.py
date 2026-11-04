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
