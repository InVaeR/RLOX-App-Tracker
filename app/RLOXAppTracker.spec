# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

APP_ROOT = Path(SPECPATH).resolve()
REPO_ROOT = APP_ROOT.parent
SRC_ROOT = APP_ROOT / "src"
ASSETS_ROOT = REPO_ROOT / "assets"
VERSION_INFO = REPO_ROOT / "version_info.txt"

a = Analysis(
    [str(SRC_ROOT / 'rlox_app_tracker' / '__main__.py')],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=[
        (str(ASSETS_ROOT), 'assets'),
    ],
    hiddenimports=[
        'win32gui',
        'win32process',
        'psutil',
        'PySide6.QtNetwork',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'PIL',
        'curses',
        'distutils',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='RLOXAppTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_ROOT / 'app.ico'),
    version=str(VERSION_INFO),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RLOXAppTracker',
)
