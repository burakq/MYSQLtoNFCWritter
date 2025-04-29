# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nfc_writer_enhanced.py'],
    pathex=[],
    binaries=[],
    datas=[('venv/lib/python3.13/site-packages/smartcard', 'smartcard'), ('venv/lib/python3.13/site-packages/bcrypt', 'bcrypt'), ('venv/lib/python3.13/site-packages/PyMySQL', 'PyMySQL'), ('venv/lib/python3.13/site-packages/cryptography', 'cryptography'), ('venv/lib/python3.13/site-packages/cffi', 'cffi'), ('venv/lib/python3.13/site-packages/pycparser', 'pycparser')],
    hiddenimports=[],
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
    name='nfc_writer_enhanced',
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
    icon=['logo.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='nfc_writer_enhanced',
)
app = BUNDLE(
    coll,
    name='nfc_writer_enhanced.app',
    icon='logo.icns',
    bundle_identifier=None,
)
