"""Execution de commandes cross-plateforme avec sortie en flux."""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import Config
from .logging_setup import annotate, get_logger, log_command_end, log_command_start, log_output

SECRET_HINTS = ("token", "secret", "password", "passwd", "apikey", "api_key", "keystore")


def host_os() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def resolve_shell(preference: str) -> list[str]:
    """Retourne le prefixe de commande du shell a utiliser."""
    if preference == "auto":
        preference = "cmd" if host_os() == "windows" else "bash"
    if preference == "cmd":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c"]
    if preference == "powershell":
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        return [exe, "-NoProfile", "-NonInteractive", "-Command"]
    return [shutil.which("bash") or "/bin/bash", "-lc"]


def redact(line: str) -> str:
    """Masque les valeurs qui ressemblent a des secrets."""
    lowered = line.lower()
    if not any(hint in lowered for hint in SECRET_HINTS):
        return line
    out = []
    for token in line.split(" "):
        if "=" in token and any(hint in token.lower() for hint in SECRET_HINTS):
            key, _, _ = token.partition("=")
            out.append(f"{key}=***")
        else:
            out.append(token)
    return " ".join(out)


@dataclass
class CommandResult:
    command: str
    exit_code: int
    duration_s: float


class CommandRunner:
    """Lance une commande dans un thread et pousse les lignes dans une file."""

    def __init__(self, config: Config, output: queue.Queue[tuple[str, str]]):
        self.config = config
        self.output = output
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def emit(self, kind: str, text: str) -> None:
        self.output.put((kind, text))

    def note(self, text: str, author: str = "agent") -> str:
        """Ajoute un commentaire horodate au journal fichier et a la fenetre."""
        line = annotate(text, author=author)
        self.emit("note", line)
        return line

    def start(self, command: str, on_done: Callable[[CommandResult], None] | None = None) -> bool:
        if self.running:
            self.emit("error", "une commande est deja en cours")
            return False
        allowed, reason = self.config.is_command_allowed(command)
        if not allowed:
            get_logger().warning("commande refusee (%s) : %s", reason, command,
                                 extra={"kind": "blocked", "command": command})
            self.emit("error", reason)
            return False
        if not self.config.get("network.verify_tls"):
            get_logger().warning("verification TLS desactivee pour : %s", command)
            self.emit("warn", "verification TLS desactivee (configuration Reseau)")
        cwd = self.config.get("project.path") or str(Path.cwd())
        if not Path(cwd).is_dir():
            self.emit("error", f"dossier de projet introuvable : {cwd}")
            return False
        self._thread = threading.Thread(
            target=self._run, args=(command, cwd, on_done), daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        process = self._process
        if process and process.poll() is None:
            self.emit("warn", "arret demande")
            try:
                if host_os() == "windows":
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), 15)
            except (ProcessLookupError, PermissionError, OSError) as exc:
                self.emit("error", f"arret impossible : {exc}")

    def _run(self, command: str, cwd: str, on_done: Callable[[CommandResult], None] | None) -> None:
        prefix = resolve_shell(self.config.get("env.shell"))
        redacting = self.config.get("security.block_secrets_in_logs")
        log_to_file = self.config.get("logging.log_output")
        annotating = self.config.get("logging.auto_annotate")
        if annotating:
            self.note(f"debut : {command}")
        log_command_start(command)
        self.emit("cmd", f"$ {command}")
        started = time.monotonic()
        code = -1
        try:
            self._process = subprocess.Popen(
                [*prefix, command],
                cwd=cwd,
                env=self.config.environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=host_os() != "windows",
            )
            assert self._process.stdout is not None
            for line in self._process.stdout:
                text = redact(line.rstrip()) if redacting else line.rstrip()
                self.emit("out", text)
                if log_to_file:
                    log_output(text)
            code = self._process.wait(timeout=self.config.get("autopilot.timeout_seconds"))
        except FileNotFoundError as exc:
            self.emit("error", f"shell introuvable : {exc}")
        except subprocess.TimeoutExpired:
            self.emit("error", "timeout depasse, processus interrompu")
            self.stop()
        except OSError as exc:
            self.emit("error", f"echec d'execution : {exc}")
        finally:
            duration = time.monotonic() - started
            self._process = None
            log_command_end(command, code, duration)
            self.emit("ok" if code == 0 else "error", f"code de sortie {code} ({duration:.1f}s)")
            if annotating:
                self.note(f"fin : code {code} en {duration:.1f}s")
            if on_done:
                on_done(CommandResult(command, code, duration))


# --------------------------------------------------------------------------- #
# Catalogue d'actions
# --------------------------------------------------------------------------- #


def detect_stack(project_path: str) -> str:
    root = Path(project_path or ".")
    markers = {
        "node": ("package.json",),
        "python": ("pyproject.toml", "requirements.txt"),
        "rust": ("Cargo.toml",),
        "dotnet": ("global.json",),
        "flutter": ("pubspec.yaml",),
        "godot": ("project.godot",),
    }
    for stack, files in markers.items():
        if any((root / name).exists() for name in files):
            return stack
    return "node"


def package_manager(config: Config) -> str:
    manager = config.get("project.package_manager")
    if manager != "auto":
        return manager
    root = Path(config.get("project.path") or ".")
    for lockfile, name in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
        ("poetry.lock", "poetry"),
        ("uv.lock", "uv"),
        ("Cargo.lock", "cargo"),
    ):
        if (root / lockfile).exists():
            return name
    return "npm"


def build_command(config: Config, action: str) -> str:
    """Traduit une action logique en commande shell selon la stack detectee."""
    stack = config.get("project.stack")
    if stack == "auto":
        stack = detect_stack(config.get("project.path"))
    manager = package_manager(config)
    extra = " ".join(config.get("build.extra_args"))
    release_dir = config.get("build.release_dir") or "release"

    node_scripts = {
        "setup": f"{manager} install",
        "dev": f"{manager} run dev",
        "lint": f"{manager} run lint",
        "test": f"{manager} test",
        "build": f"{manager} run build",
    }
    python_scripts = {
        "setup": "python -m pip install -r requirements.txt",
        "dev": "python -m app",
        "lint": "ruff check .",
        "test": "python -m pytest -q",
        "build": "python -m build",
    }
    rust_scripts = {
        "setup": "cargo fetch",
        "dev": "cargo run",
        "lint": "cargo clippy --all-targets",
        "test": "cargo test",
        "build": "cargo build --release",
    }
    table = {"python": python_scripts, "rust": rust_scripts}.get(stack, node_scripts)

    if action in table:
        return table[action]
    if action == "package:exe":
        if stack == "python":
            return f"pyinstaller --noconfirm --onefile --windowed --distpath {release_dir} app.py {extra}".strip()
        if stack == "rust":
            return f"cargo tauri build --bundles nsis {extra}".strip()
        return f"npx --yes electron-builder --win nsis --publish never {extra}".strip()
    if action == "package:apk":
        if stack == "flutter":
            return f"flutter build apk --release {extra}".strip()
        return "cd android && ./gradlew assembleRelease"
    if action == "package:dmg":
        if host_os() != "macos":
            return "echo '.dmg necessite macOS - utiliser le job CI macos-latest' && exit 1"
        return f"npx --yes electron-builder --mac dmg --publish never {extra}".strip()
    if action == "verify":
        if host_os() == "windows":
            return (
                f"powershell -NoProfile -Command \"Get-ChildItem -Recurse -File '{release_dir}' | "
                "ForEach-Object { [pscustomobject]@{ Nom=$_.Name; Octets=$_.Length; "
                "SHA256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash } } | Format-Table -AutoSize\""
            )
        return f"ls -lh {release_dir} && find {release_dir} -type f -exec sha256sum {{}} +"
    if action == "clean":
        if host_os() == "windows":
            return f"if exist dist rmdir /s /q dist & if exist {release_dir} rmdir /s /q {release_dir}"
        return f"rm -rf dist build {release_dir}"
    if action == "doctor":
        checks = "node -v; npm -v; python --version; java -version; cargo --version; dotnet --version"
        return checks if host_os() != "windows" else checks.replace(";", "&")
    raise ValueError(f"action inconnue: {action}")


ACTIONS: tuple[tuple[str, str], ...] = (
    ("setup", "Installer les dependances"),
    ("dev", "Lancer le serveur de dev"),
    ("lint", "Lint"),
    ("test", "Tests"),
    ("build", "Build"),
    ("package:exe", "Packager .exe"),
    ("package:apk", "Packager .apk"),
    ("package:dmg", "Packager .dmg"),
    ("verify", "Verifier les artefacts"),
    ("clean", "Nettoyer"),
    ("doctor", "Diagnostic des toolchains"),
)
