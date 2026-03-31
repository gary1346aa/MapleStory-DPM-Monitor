# -*- mode: python ; coding: utf-8 -*-
import os

# Manual path to torch lib to avoid runtime import errors during build
torch_lib_dir = r'C:\Users\gary1\MapleStory-DPM-Monitor\venv\lib\site-packages\torch\lib'

a = Analysis(
    ['maplestory_dps_gui.py'],
    pathex=[],
    binaries=[
        (os.path.join(torch_lib_dir, '*.dll'), 'torch/lib'),
    ],
    datas=[
        ('GoogleSans-VariableFont_GRAD,opsz,wght.ttf', '.'),
    ],
    hiddenimports=[
        'easyocr', 
        'torch', 
        'cv2', 
        'keyboard', 
        'mss', 
        'PIL', 
        'pandas', 
        'matplotlib', 
        'seaborn', 
        'scipy',
        'scipy.signal',
        'scipy.interpolate'
    ],
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
    [],
    exclude_binaries=True,
    name='MapleStory_DPM_v20260331.5',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MapleStory_DPM_v20260331.5',
)
