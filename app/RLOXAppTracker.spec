# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/rlox_app_tracker/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
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
    a.binaries,
    a.datas,
    [],
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
    icon='assets/app.ico',
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
