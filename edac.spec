# PyInstaller spec — executable Windows fenetre, fichier unique.
# Build : pyinstaller --noconfirm --clean edac.spec

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT))

from tools.win_version import write_version_file  # noqa: E402

block_cipher = None
icon_file = ROOT / "assets" / "icon.ico"
version_file = write_version_file() if sys.platform == "win32" else None

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
    # True : une erreur n'ouvre pas de boite de dialogue modale (bloquerait la CI)
    disable_windowed_traceback=True,
    icon=str(icon_file) if icon_file.exists() else None,
    version=str(version_file) if version_file else None,
)
