# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = [('C:\\ProgramData\\anaconda3\\DLLs\\_tkinter.pyd', '.'), ('C:\\ProgramData\\anaconda3\\Library\\bin\\tcl86t.dll', '.'), ('C:\\ProgramData\\anaconda3\\Library\\bin\\tk86t.dll', '.')]
hiddenimports = ['tkinter', 'tkinter.ttk', '_tkinter']
tmp_ret = collect_all('tkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['reversi\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['C:\\Users\\tubas\\python_uv\\def\\rt_tk_path.py'],
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
    name='Reversi',
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
)
