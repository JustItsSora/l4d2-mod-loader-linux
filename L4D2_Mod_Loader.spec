# -*- mode: python ; coding: utf-8 -*-

import sys
from importlib.metadata import version
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files
from flet_desktop import ensure_client_cached

if version('flet') != version('flet-desktop'):
    raise RuntimeError('flet and flet-desktop must have matching versions.')

# Resolve the official client at build time, never on the user's first launch.
desktop_dir = ensure_client_cached() / 'flet'
required_files = (('flet.exe', 'flutter_windows.dll', 'data/app.so', 'data/icudtl.dat')
                  if sys.platform == 'win32' else ('flet', 'data/app.so', 'data/icudtl.dat'))
for required in required_files:
    if not (desktop_dir / required).is_file():
        raise RuntimeError('Incomplete Flet desktop runtime: ' + str(desktop_dir / required))

flet_data = [(str(desktop_dir), 'flet_desktop/app/flet')]
flet_data += collect_data_files('flet.controls.material', includes=['icons.json'])
flet_data += collect_data_files('flet.controls.cupertino', includes=['cupertino_icons.json'])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons/icono.png', 'assets/icons'),
        ('assets/backgrounds/L4D2 BACKGROUND.png', 'assets/backgrounds'),
        ('l4d2_core.py', '.'),
    ] + flet_data,
    hiddenimports=['flet_desktop'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(Path(SPECPATH) / 'packaging_hooks' / 'pyi_rth_flet_desktop.py'),
                   str(Path(SPECPATH) / 'packaging_hooks' / 'pyi_rth_flet_desktop_linux.py')],
    excludes=[],
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
    name='L4D2 Mod Loader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icons/icon.ico'] if sys.platform == 'win32' else None,
)
