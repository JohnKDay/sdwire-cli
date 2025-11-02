# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for creating a portable sdwire binary.

This configuration bundles the sdwire CLI application and all its dependencies
into a single executable file suitable for Linux systems (specifically Ubuntu 24.04).
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys
import os

block_cipher = None

# Get the path to the sdwire package
sdwire_path = os.path.join(os.getcwd(), 'sdwire')

# Collect all sdwire submodules
hiddenimports = []
hiddenimports += collect_submodules('sdwire')
hiddenimports += collect_submodules('usb')
hiddenimports += collect_submodules('pyftdi')
hiddenimports += collect_submodules('click')

# Additional hidden imports that PyInstaller might miss
hiddenimports += [
    'usb.backend.libusb1',
    'usb.backend.libusb0',
    'usb.backend.openusb',
]

a = Analysis(
    ['sdwire/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include the entire sdwire package
        ('sdwire', 'sdwire'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='sdwire',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
