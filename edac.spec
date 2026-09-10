# PyInstaller spec — executable Windows fenetre, fichier unique.
# Build : pyinstaller --noconfirm --clean edac.spec

block_cipher = None

a = Analysis(
    ["edac/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["edac.gui", "edac.cli", "edac.config", "edac.runner"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "numpy", "pandas", "matplotlib"],
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
    name="EDAC-Console",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # application fenetree : pas de console noire
    disable_windowed_traceback=False,
    icon=None,              # remplacer par "assets/icon.ico" si disponible
)
