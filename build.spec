# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys

block_cipher = None

all_datas, all_binaries, all_hidden = [], [], []
for mod in ['win32gui', 'win32process', 'psutil']:
    d, b, h = collect_all(mod, include_py_files=True)
    all_datas += d
    all_binaries += b
    all_hidden += h

sys32 = None
for p in sys.path:
    d = os.path.join(p, 'pywin32_system32')
    if os.path.isdir(d):
        sys32 = d
        break
if sys32:
    for f in os.listdir(sys32):
        if f.endswith('.dll'):
            all_binaries.append((os.path.join(sys32, f), 'pywin32_system32'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas + [('assets', 'assets')],
    hiddenimports=all_hidden + ['win32gui', 'win32process', 'psutil',
                                 'win32api', 'win32security'],
    hookspath=[],
    runtime_hooks=['rthook_pywin32.py'],
    excludes=['tkinter', 'matplotlib'],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='RusLOXPy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='assets/app.ico',
    version='version_info.txt',
)
