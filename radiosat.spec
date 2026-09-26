# -*- mode: python ; coding: utf-8 -*-
# radiosat.spec — Configuración de PyInstaller para RadioSAT XP

import sys
import os
import shutil

block_cipher = None

# Ruta base del proyecto
BASE = os.path.abspath('.')

# Empaquetar FFmpeg dentro de la aplicación. El bus de programa lo utiliza para
# enviar la mezcla completa (cabecera, pauta local y retorno) hacia Icecast.
if sys.platform == 'win32' and os.path.exists('ffmpeg.exe'):
    FFMPEG = os.path.abspath('ffmpeg.exe')
else:
    FFMPEG = shutil.which('ffmpeg')
EXTRA_BINARIES = [(FFMPEG, '.')] if FFMPEG else []

# Determinar icono según plataforma
if sys.platform == 'darwin':
    app_icon = os.path.join(BASE, 'assets', 'icon.icns')
else:
    app_icon = os.path.join(BASE, 'assets', 'icon.ico')

a = Analysis(
    ['main.py'],
    pathex=[BASE],
    binaries=EXTRA_BINARIES,
    datas=[
        # Iconos Windows XP
        ('winxpicons', 'winxpicons'),
        ('icons', 'icons'),
        # Icono de la app
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.sip',
        'numpy',
        'sounddevice',
        'mutagen',
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.nsss',
        'json',
        'traceback',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
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
    [],
    exclude_binaries=True,
    name='RadioSAT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RadioSAT',
)

# Configuración específica para macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='RadioSAT.app',
        icon=app_icon,
        bundle_identifier='com.radiosat.app',
        info_plist={
            'CFBundleName': 'RadioSAT XP',
            'CFBundleDisplayName': 'RadioSAT XP',
            'CFBundleVersion': '1.6.0',
            'CFBundleShortVersionString': '1.6.0',
            'NSHighResolutionCapable': True,
            'NSMicrophoneUsageDescription': 'RadioSAT necesita acceso al micrófono para funciones de audio en tiempo real.',
        },
    )
