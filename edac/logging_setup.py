"""Systeme de journalisation : fichier rotatif, niveaux, annotations.

Trois destinations possibles pour chaque evenement :

* le fichier de log (rotation par taille, N sauvegardes) ;
* la console (CLI) ;
* la fenetre (via la file du runner).

Une *annotation* est un commentaire ecrit par l'utilisateur ou par l'agent au
milieu du journal (`# 22:31:07 [note] on teste le build signe`). Elle sert a
relire une session : chaque commande, son code de sortie et sa duree sont
encadres par des annotations.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER_NAME = "edac"
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

_TEXT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def default_log_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "ExpertDevAutopilot" / "logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ExpertDevAutopilot"
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "ExpertDevAutopilot" / "logs"


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par evenement, pour ingestion par un collecteur."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("kind", "command", "exit_code", "duration_s", "note"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def resolve_log_file(config) -> Path:
    configured = config.get("logging.file")
    if configured:
        return Path(configured).expanduser()
    return default_log_dir() / "edac.log"


def setup_logging(config) -> logging.Logger:
    """(Re)configure le logger racine de l'application depuis la config."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, config.get("logging.level"), logging.INFO))
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    if config.get("logging.to_file"):
        path = resolve_log_file(config)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = logging.handlers.RotatingFileHandler(
                path,
                maxBytes=max(1, config.get("logging.max_size_mb")) * 1024 * 1024,
                backupCount=config.get("logging.backup_count"),
                encoding="utf-8",
            )
            handler.setFormatter(
                JsonFormatter() if config.get("logging.format") == "json"
                else logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT)
            )
            logger.addHandler(handler)
        except OSError as exc:  # disque plein, droits insuffisants…
            fallback = logging.StreamHandler(sys.stderr)
            fallback.setFormatter(logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT))
            logger.addHandler(fallback)
            logger.error("journal fichier indisponible (%s) : %s", path, exc)

    if config.get("logging.to_console"):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT))
        logger.addHandler(console)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


# --------------------------------------------------------------------------- #
# Annotations
# --------------------------------------------------------------------------- #


def annotate(text: str, *, author: str = "user") -> str:
    """Ecrit un commentaire dans le journal et retourne la ligne affichable."""
    line = f"# {datetime.now().strftime('%H:%M:%S')} [{author}] {text}"
    get_logger().info(line, extra={"kind": "note", "note": text})
    return line


def log_command_start(command: str) -> None:
    get_logger().info("commande demarree : %s", command,
                      extra={"kind": "command_start", "command": command})


def log_command_end(command: str, exit_code: int, duration_s: float) -> None:
    logger = get_logger()
    level = logging.INFO if exit_code == 0 else logging.ERROR
    logger.log(level, "commande terminee (code %s en %.1fs) : %s", exit_code, duration_s, command,
               extra={"kind": "command_end", "command": command,
                      "exit_code": exit_code, "duration_s": round(duration_s, 3)})


def log_output(line: str) -> None:
    get_logger().debug(line, extra={"kind": "output"})


def read_tail(path: Path, lines: int = 200) -> str:
    """Retourne les dernieres lignes d'un fichier de log (lecture robuste)."""
    if not path.is_file():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            block = min(size, 64 * 1024 * max(1, lines // 500 + 1))
            handle.seek(size - block)
            data = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(data.splitlines()[-lines:])


def list_log_files(config) -> list[Path]:
    """Fichier courant + fichiers de rotation existants."""
    base = resolve_log_file(config)
    if not base.parent.is_dir():
        return []
    return sorted(base.parent.glob(base.name + "*"))
