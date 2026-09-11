"""Point d'entree de l'executable PyInstaller.

`edac/__main__.py` utilise des imports relatifs : embarque tel quel, il est
execute sous le nom `__main__` sans paquet parent et leve ImportError.
Ce script importe le paquet normalement.
"""
from __future__ import annotations

import multiprocessing
import sys

from edac.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
