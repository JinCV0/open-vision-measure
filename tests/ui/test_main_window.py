from vision_measure.ui.main_window import MainWindow


def test_main_window_opens_with_idle_workspace(qtbot) -> None:
    window = MainWindow(auto_discover=False)
    qtbot.addWidget(window)
    assert window.workspace.state.value == "idle"
    assert window.windowTitle() == "Open Vision Measure"
