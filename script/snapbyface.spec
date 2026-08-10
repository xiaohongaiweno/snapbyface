# -*- mode: python ; coding: utf-8 -*-
"""SnapByFace cross-platform PyInstaller configuration.

Windows:
    pyinstaller --clean --noconfirm snapbyface.spec

macOS:
    pyinstaller --clean --noconfirm snapbyface.spec
"""
import sys
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# insightface / faiss / onnxruntime 有大量动态导入的子模块，需显式收集
hiddenimports = []
hiddenimports += collect_submodules("insightface")
hiddenimports += collect_submodules("insightface.app")
hiddenimports += collect_submodules("insightface.model_zoo")
hiddenimports += collect_submodules("faiss")
hiddenimports += collect_submodules("onnxruntime")
hiddenimports += collect_submodules("watchdog")
hiddenimports += collect_submodules("cv2")
hiddenimports += collect_submodules("rawpy")

# 排除无关且体积大的 Qt 模块
excludes = [
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
    "PyQt6.QtQuick",
    "PyQt6.QtQml",
    "PyQt6.QtMultimedia",
    "tkinter",
]

root = Path(SPEC).resolve().parents[1]
icon_ico = root / "resources" / "snapbyface.ico"
icon_icns = root / "resources" / "snapbyface.icns"
icon_path = str(icon_icns if sys.platform == "darwin" and icon_icns.exists() else icon_ico)
datas = []
if icon_ico.exists():
    datas.append((str(icon_ico), "resources"))
if icon_icns.exists():
    datas.append((str(icon_icns), "resources"))
if os.environ.get("SNAPBYFACE_INCLUDE_MODELS") == "1":
    model_dir = root / "data" / "models"
    if model_dir.exists():
        datas.append((str(model_dir), "data/models"))

a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="SnapByFace",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(icon_icns) if icon_icns.exists() else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="SnapByFace",
    )

    app = BUNDLE(
        coll,
        name="SnapByFace.app",
        icon=str(icon_icns) if icon_icns.exists() else None,
        bundle_identifier="com.snapbyface.desktop",
        info_plist={
            "NSCameraUsageDescription": (
                "SnapByFace 需要使用摄像头采集游客人脸以搜索照片。"
            ),
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="SnapByFace",
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

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="SnapByFace",
    )
