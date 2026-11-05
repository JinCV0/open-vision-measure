from vision_measure.ui.app import is_smoke_test


def test_smoke_test_argument_is_recognized() -> None:
    assert is_smoke_test(["OpenVisionMeasure.exe", "--smoke-test"])
    assert not is_smoke_test(["OpenVisionMeasure.exe"])
