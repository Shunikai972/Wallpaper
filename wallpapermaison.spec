# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

ROOT_DIR = Path.cwd()

datas = [
    ('ui', 'ui'),
    ('wallpapermaison.desktop', '.'),
]

hiddenimports = [
    'sqlite3',
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageEnhance',
    'PIL.ImageFilter',
    'PIL.ImageOps',
    'PIL.ImageDraw',
    'psutil',
    'webview',
    'webview.platforms.gtk',
    'app',
    'app.core',
    'app.core.config',
    'app.core.events',
    'app.core.logger',
    'app.storage',
    'app.storage.database',
    'app.storage.cache',
    'app.system',
    'app.system.detector',
    'app.system.monitors',
    'app.system.power',
    'app.system.window_monitor',
    'app.system.autostart',
    'app.system.tray',
    'app.media',
    'app.media.metadata',
    'app.media.thumbnail',
    'app.media.scanner',
    'app.image_processing',
    'app.image_processing.adjuster',
    'app.wallpaper',
    'app.wallpaper.base',
    'app.wallpaper.manager',
    'app.wallpaper.engines.gnome_engine',
    'app.wallpaper.engines.kde_engine',
    'app.wallpaper.engines.mpvpaper_engine',
    'app.wallpaper.engines.swww_engine',
    'app.wallpaper.engines.xwinwrap_engine',
    'app.wallpaper.engines.feh_engine',
    'app.wallpaper.engines.fallback_engine',
    'app.automation',
    'app.automation.scheduler',
    'app.automation.rules',
    'app.api',
    'app.api.bridge',
]

a = Analysis(
    ['app/main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy.tests'],
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
    name='wallpapermaison',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/assets/logo.svg',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='wallpapermaison',
)
