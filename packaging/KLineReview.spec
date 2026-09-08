# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(SPECPATH).parent
SRC_ROOT = PROJECT_ROOT / "src"


def collect_data_files():
    """收集运行时仍需从文件系统读取的只读资源。

    - .ui 文件：运行时由 uic.loadUi 加载；
    - i18n .qm：运行时由 QTranslator 加载。
    其余图标/QSS 已由 resources_rc.py 等 Qt 资源模块编译进代码，无需重复携带。
    """
    datas = []
    ui_root = SRC_ROOT / "gui"
    for f in ui_root.rglob("*.ui"):
        dest = "src/" + f.relative_to(SRC_ROOT).parent.as_posix()
        datas.append((str(f), dest))

    i18n_root = SRC_ROOT / "resources" / "i18n"
    if i18n_root.exists():
        for f in i18n_root.rglob("*.qm"):
            dest = "src/" + f.relative_to(SRC_ROOT).parent.as_posix()
            datas.append((str(f), dest))
    return datas


icon_ico = PROJECT_ROOT / "packaging" / "build" / "KLineReview.ico"
icon_icns = PROJECT_ROOT / "packaging" / "build" / "KLineReview.icns"

a = Analysis(
    [str(SRC_ROOT / "main.py")],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=collect_data_files(),
    hiddenimports=(
        collect_submodules("gui.qt_widgets.MComponents.qfluentwidgets")
        + ["PyQt5.QtSvg"]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="KLineReview",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_ico) if icon_ico.exists() else None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="KLineReview.app",
        icon=str(icon_icns) if icon_icns.exists() else None,
        bundle_identifier="com.daydreamerai.klinereview",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleDisplayName": "KLineReview",
        },
    )
