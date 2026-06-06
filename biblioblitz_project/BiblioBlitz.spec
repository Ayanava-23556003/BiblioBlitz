# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['G:\\My Drive\\biblioblitz_project\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('G:\\My Drive\\biblioblitz_project\\biblioblitz.ico', '.'), ('G:\\My Drive\\biblioblitz_project\\biblioblitz.png', '.'), ('C:\\Users\\ayanp\\Downloads\\states.csv', '.'), ('C:\\Users\\ayanp\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\customtkinter', 'customtkinter')],
    hiddenimports=['customtkinter', 'tkinter', 'tkinter.ttk', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg'],
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
    a.datas,
    [],
    name='BiblioBlitz',
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
    icon=['G:\\My Drive\\biblioblitz_project\\biblioblitz.ico'],
)
