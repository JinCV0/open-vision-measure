# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

root = Path(SPECPATH).resolve().parent
theme_datas = [
    (
        str(root / "src" / "vision_measure" / "ui" / "assets"),
        "vision_measure/ui/assets",
    )
]
analysis = Analysis(
    [str(root / "scripts" / "exe_entry.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=theme_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtGraphs",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
    optimize=1,
)

# Python's standalone distribution ships an ICU build that is incompatible with
# the Qt wheel. Windows provides the matching ICU used by Qt in System32.
python_icu = {"icuuc.dll", "icudt78.dll"}
analysis.binaries = [
    binary
    for binary in analysis.binaries
    if Path(binary[0]).name.lower() not in python_icu
]

pyz = PYZ(analysis.pure)

onedir_build = os.environ.get("OVM_ONEDIR_BUILD") == "1"
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="OpenVisionMeasure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=os.environ.get("OVM_CONSOLE_BUILD") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(root / "packaging" / "windows-version-info.txt"),
    exclude_binaries=onedir_build,
)

if onedir_build:
    collection = COLLECT(
        exe,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        name="OpenVisionMeasure",
    )
