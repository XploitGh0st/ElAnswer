# -*- mode: python ; coding: utf-8 -*-
"""
ElAnswer PyInstaller Specification File
Build a standalone executable for Windows distribution.

To build: pyinstaller ElAnswer.spec
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all data for google-generativeai package
datas_genai = []
binaries_genai = []
hiddenimports_genai = []

try:
    datas_genai, binaries_genai, hiddenimports_genai = collect_all('google.generativeai')
except Exception:
    pass

# Additional hidden imports for the application
hidden_imports = [
    'PIL._tkinter_finder',
    'pystray._win32',
    'google.generativeai',
    'google.ai.generativelanguage',
    'google.auth',
    'google.auth.transport.requests',
    'google.api_core',
    'grpc',
    'keyboard',
    'tkinter',
    'tkinter.scrolledtext',
    'ctypes',
    'ctypes.wintypes',
    'threading',
    'json',
    'logging',
    'datetime',
    'webbrowser',
    'platform',
    'subprocess',
    *hiddenimports_genai
]

# Determine icon file (prefer .ico, fallback to .png)
icon_file = None
if os.path.exists('assets/logo.ico'):
    icon_file = 'assets/logo.ico'
elif os.path.exists('assets/logo.png'):
    icon_file = 'assets/logo.png'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_genai,
    datas=[
        ('assets', 'assets'),  # Include assets folder
        *datas_genai
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'unittest',
    ],
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
    name='ElAnswer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',  # Build for 64-bit Windows (most common)
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,  # Application icon
    version='version_info.txt',  # Windows version info
    uac_admin=False,  # Don't require admin privileges
)
