"""Ressource de version Windows (onglet Proprietes > Details de l'explorateur).

Le fichier est genere depuis `edac.__version__` pour eviter une double source
de verite entre le code, l'executable et l'installeur.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COMPANY = "Expert Dev Autopilot"
PRODUCT = "Expert Dev Autopilot Console"
DESCRIPTION = "Console de developpement autonome (fenetre + CLI)"
COPYRIGHT = "Domaine public (The Unlicense)"
EXE_NAME = "EDAC-Console.exe"

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tup},
    prodvers={tup},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040C04B0',
        [StringStruct('CompanyName', {company!r}),
         StringStruct('FileDescription', {description!r}),
         StringStruct('FileVersion', {version!r}),
         StringStruct('InternalName', 'EDAC-Console'),
         StringStruct('LegalCopyright', {copyright!r}),
         StringStruct('OriginalFilename', {exe!r}),
         StringStruct('ProductName', {product!r}),
         StringStruct('ProductVersion', {version!r})])
    ]),
    VarFileInfo([VarStruct('Translation', [1036, 1200])])
  ]
)
"""


def read_version() -> str:
    """Lit __version__ dans edac/__init__.py sans importer le paquet."""
    source = (ROOT / "edac" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', source)
    return match.group(1) if match else "0.0.0"


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in re.findall(r"\d+", version)][:4]
    parts += [0] * (4 - len(parts))
    return tuple(parts)  # type: ignore[return-value]


def write_version_file(target: Path | None = None) -> Path:
    """Ecrit la ressource de version et retourne son chemin."""
    version = read_version()
    path = target or ROOT / "build" / "version_info.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        TEMPLATE.format(
            tup=version_tuple(version),
            company=COMPANY,
            description=DESCRIPTION,
            version=version,
            copyright=COPYRIGHT,
            exe=EXE_NAME,
            product=PRODUCT,
        ),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    print(write_version_file())
