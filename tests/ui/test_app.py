from vision_measure.ui.app import is_ai_model_smoke_test, is_ai_smoke_test, is_smoke_test


def test_smoke_test_argument_is_recognized() -> None:
    assert is_smoke_test(["OpenVisionMeasure.exe", "--smoke-test"])
    assert not is_smoke_test(["OpenVisionMeasure.exe"])


def test_ai_smoke_test_argument_is_recognized() -> None:
    assert is_ai_smoke_test(["OpenVisionMeasure.exe", "--ai-smoke-test"])
    assert not is_ai_smoke_test(["OpenVisionMeasure.exe"])


def test_ai_model_smoke_test_argument_is_recognized() -> None:
    assert is_ai_model_smoke_test(["OpenVisionMeasure.exe", "--ai-model-smoke-test"])
    assert not is_ai_model_smoke_test(["OpenVisionMeasure.exe"])
