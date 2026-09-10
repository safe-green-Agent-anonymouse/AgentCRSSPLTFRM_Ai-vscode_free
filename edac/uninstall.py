"""Desinstallation propre de Expert Dev Autopilot Console.

Supprime, au choix : l'environnement virtuel et les artefacts de build du
dossier d'installation, la configuration, les journaux et les raccourcis.
Rien n'est supprime en dehors de ces emplacements connus, et `--dry-run`
affiche le plan sans rien toucher.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import Config, config_dir
from .logging_setup import default_log_dir, resolve_log_file

INSTALL_ARTIFACTS = (".venv", "build", "dist", "release", "__pycache__",
                     "edac/__pycache__", "tests/__pycache__")


@dataclass
class Target:
    path: Path
    label: str
    optional: bool = False


def install_dir() -> Path:
    """Dossier du projet (ou dossier du .exe si execute depuis PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def shortcut_paths() -> list[Path]:
    """Raccourcis crees par l'installateur ou par l'utilisateur."""
    home = Path.home()
    if sys.platform.startswith("win"):
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return [
            home / "Desktop" / "Expert Dev Autopilot Console.lnk",
            appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            / "Expert Dev Autopilot Console",
        ]
    if sys.platform == "darwin":
        return [Path("/Applications/EDAC-Console.app")]
    return [
        home / ".local" / "share" / "applications" / "edac-console.desktop",
        home / "Desktop" / "edac-console.desktop",
    ]


def collect_targets(config: Config, *, keep_config: bool, keep_logs: bool,
                    keep_venv: bool) -> list[Target]:
    root = install_dir()
    targets: list[Target] = []
    for name in INSTALL_ARTIFACTS:
        if name == ".venv" and keep_venv:
            continue
        targets.append(Target(root / name, f"artefact d'installation ({name})", optional=True))
    if not keep_config:
        targets.append(Target(config.path, "fichier de configuration"))
        targets.append(Target(Path(str(config.path) + ".bak"), "sauvegarde de configuration",
                              optional=True))
        targets.append(Target(config_dir(), "dossier de configuration"))
    if not keep_logs:
        log_file = resolve_log_file(config)
        for path in sorted(log_file.parent.glob(log_file.name + "*")):
            targets.append(Target(path, "journal"))
        targets.append(Target(default_log_dir(), "dossier des journaux", optional=True))
    targets.extend(Target(path, "raccourci", optional=True) for path in shortcut_paths())
    return targets


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    return 0


def human(size: int) -> str:
    value = float(size)
    for unit in ("o", "Ko", "Mo", "Go"):
        if value < 1024 or unit == "Go":
            return f"{value:.0f} {unit}" if unit == "o" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} Go"


def remove(path: Path) -> tuple[bool, str]:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True, ""
    except OSError as exc:
        return False, str(exc)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="edac uninstall",
        description="Desinstalle proprement Expert Dev Autopilot Console.",
    )
    parser.add_argument("--dry-run", action="store_true", help="afficher le plan sans supprimer")
    parser.add_argument("--yes", "-y", action="store_true", help="ne pas demander de confirmation")
    parser.add_argument("--keep-config", action="store_true", help="conserver la configuration")
    parser.add_argument("--keep-logs", action="store_true", help="conserver les journaux")
    parser.add_argument("--keep-venv", action="store_true", help="conserver l'environnement virtuel")
    parser.add_argument("--config", help="chemin d'un fichier de configuration specifique")
    args = parser.parse_args(argv)

    config = Config.load(args.config, use_env=False)
    targets = [t for t in collect_targets(config, keep_config=args.keep_config,
                                          keep_logs=args.keep_logs, keep_venv=args.keep_venv)
               if t.path.exists()]

    print(f"Dossier d'installation : {install_dir()}")
    if not targets:
        print("Rien a supprimer : l'installation est deja propre.")
        return 0

    total = 0
    print("\nElements a supprimer :")
    for target in targets:
        size = size_of(target.path)
        total += size
        print(f"  - {target.path}  [{target.label}, {human(size)}]")
    print(f"\nEspace libere : {human(total)}")

    if args.dry_run:
        print("\n--dry-run : aucune suppression effectuee.")
        return 0

    if not args.yes:
        answer = input("\nConfirmer la suppression ? [o/N] ").strip().lower()
        if answer not in {"o", "oui", "y", "yes"}:
            print("Annule.")
            return 1

    failures: list[str] = []
    for target in targets:
        ok, error = remove(target.path)
        status = "supprime" if ok else f"ECHEC ({error})"
        print(f"  {status} : {target.path}")
        if not ok and not target.optional:
            failures.append(f"{target.path} : {error}")

    print("\nRappels :")
    print("  · Si l'application a ete installee via EDAC-Console-Setup.exe,")
    print("    desinstallez-la aussi depuis Parametres > Applications.")
    print("  · Le dossier source du projet n'est jamais supprime par ce script :")
    print(f"    supprimez {install_dir()} manuellement si vous le souhaitez.")

    if failures:
        print("\nEchecs :", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nDesinstallation terminee.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
