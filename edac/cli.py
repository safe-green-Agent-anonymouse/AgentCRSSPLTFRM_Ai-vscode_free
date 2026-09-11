"""Interface en ligne de commande : meme configuration que la fenetre."""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading

from .config import SETTINGS, Config, ConfigError, env_var_name, parse_overrides
from .logging_setup import (annotate, list_log_files, read_tail, resolve_log_file,
                            setup_logging)
from .runner import ACTIONS, CommandRunner, build_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edac",
        description="Expert Dev Autopilot Console — fenetre, configuration et build.",
    )
    parser.add_argument("--config", help="chemin du fichier de configuration")
    parser.add_argument("--profile", help="profil a utiliser")
    parser.add_argument("--set", dest="overrides", action="append", default=[],
                        metavar="CLE=VALEUR", help="override temporaire (repetable)")
    parser.add_argument("--no-env", action="store_true", help="ignorer les variables EDAC_*")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui", help="ouvrir la fenetre (defaut)")

    run = sub.add_parser("run", help="executer une action")
    run.add_argument("action", choices=[name for name, _ in ACTIONS])

    exec_cmd = sub.add_parser("exec", help="executer une commande brute")
    exec_cmd.add_argument("shell_command", nargs=argparse.REMAINDER)

    config_cmd = sub.add_parser("config", help="gerer la configuration")
    config_sub = config_cmd.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("list", help="lister les valeurs effectives et leur origine")
    config_sub.add_parser("path", help="afficher le chemin du fichier")
    config_sub.add_parser("schema", help="afficher le schema en JSON")
    get_cmd = config_sub.add_parser("get")
    get_cmd.add_argument("key")
    set_cmd = config_sub.add_parser("set")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value")
    set_cmd.add_argument("--profile-scope", action="store_true",
                         help="ecrire dans le profil actif plutot qu'en global")
    unset_cmd = config_sub.add_parser("unset")
    unset_cmd.add_argument("key")
    export_cmd = config_sub.add_parser("export")
    export_cmd.add_argument("path")
    import_cmd = config_sub.add_parser("import")
    import_cmd.add_argument("path")
    import_cmd.add_argument("--replace", action="store_true")
    config_sub.add_parser("reset")

    profile_cmd = sub.add_parser("profile", help="gerer les profils")
    profile_sub = profile_cmd.add_subparsers(dest="profile_command", required=True)
    profile_sub.add_parser("list")
    create_cmd = profile_sub.add_parser("create")
    create_cmd.add_argument("name")
    create_cmd.add_argument("--copy", action="store_true")
    use_cmd = profile_sub.add_parser("use")
    use_cmd.add_argument("name")
    delete_cmd = profile_sub.add_parser("delete")
    delete_cmd.add_argument("name")

    log_cmd = sub.add_parser("log", help="journal : lecture, commentaires, rotation")
    log_sub = log_cmd.add_subparsers(dest="log_command", required=True)
    tail_cmd = log_sub.add_parser("tail", help="afficher la fin du journal")
    tail_cmd.add_argument("-n", "--lines", type=int, default=200)
    log_sub.add_parser("path", help="afficher le chemin du journal")
    log_sub.add_parser("list", help="lister les fichiers de rotation")
    note_cmd = log_sub.add_parser("annotate", help="ajouter un commentaire horodate")
    note_cmd.add_argument("text", nargs=argparse.REMAINDER)
    note_cmd.add_argument("--author", default="user")
    clear_cmd = log_sub.add_parser("clear", help="vider les journaux")
    clear_cmd.add_argument("--yes", "-y", action="store_true")

    uninstall_cmd = sub.add_parser("uninstall", help="desinstaller proprement")
    uninstall_cmd.add_argument("--dry-run", action="store_true", help="afficher le plan sans supprimer")
    uninstall_cmd.add_argument("--yes", "-y", action="store_true", help="sans confirmation")
    uninstall_cmd.add_argument("--keep-config", action="store_true")
    uninstall_cmd.add_argument("--keep-logs", action="store_true")
    uninstall_cmd.add_argument("--keep-venv", action="store_true")

    sub.add_parser("doctor", help="diagnostiquer les toolchains disponibles")
    return parser


def _run_command(config: Config, command: str) -> int:
    output: queue.Queue[tuple[str, str]] = queue.Queue()
    runner = CommandRunner(config, output)
    done = threading.Event()
    code = {"value": 1}

    if not runner.start(command, on_done=lambda result: (code.update(value=result.exit_code), done.set())):
        while not output.empty():
            _, text = output.get()
            print(text, file=sys.stderr)
        return 1
    while not done.is_set() or not output.empty():
        try:
            level, text = output.get(timeout=0.1)
        except queue.Empty:
            continue
        print(text, file=sys.stderr if level == "error" else sys.stdout, flush=True)
    return code["value"]


def _ensure_streams() -> None:
    """Executable fenetre (PyInstaller --windowed) : stdout/stderr valent None.

    Sans ce garde-fou, le premier `print` d'une commande CLI leve AttributeError.
    """
    devnull = None
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            devnull = devnull or open(os.devnull, "w", encoding="utf-8")
            setattr(sys, name, devnull)


def main(argv: list[str] | None = None) -> int:
    _ensure_streams()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        overrides = parse_overrides(args.overrides)
        config = Config.load(args.config, profile=args.profile, overrides=overrides,
                             use_env=not args.no_env)
    except ConfigError as exc:
        print(f"erreur de configuration : {exc}", file=sys.stderr)
        return 2

    setup_logging(config)
    command = args.command or "gui"

    if command == "gui":
        from .gui import launch  # import tardif : tkinter non requis en CLI
        return launch(config)

    if command == "run":
        return _run_command(config, build_command(config, args.action))

    if command == "exec":
        raw = " ".join(args.shell_command).strip()
        if not raw:
            print("commande vide", file=sys.stderr)
            return 2
        return _run_command(config, raw)

    if command == "doctor":
        return _run_command(config, build_command(config, "doctor"))

    if command == "config":
        return _config_command(config, args)

    if command == "profile":
        return _profile_command(config, args)

    if command == "log":
        return _log_command(config, args)

    if command == "uninstall":
        from .uninstall import run as run_uninstall
        flags = [name for name, enabled in (
            ("--dry-run", args.dry_run), ("--yes", args.yes),
            ("--keep-config", args.keep_config), ("--keep-logs", args.keep_logs),
            ("--keep-venv", args.keep_venv)) if enabled]
        if args.config:
            flags += ["--config", args.config]
        return run_uninstall(flags)

    parser.print_help()
    return 0


def _config_command(config: Config, args: argparse.Namespace) -> int:
    action = args.config_command
    try:
        if action == "list":
            width = max(len(setting.key) for setting in SETTINGS)
            for setting in SETTINGS:
                value = config.get(setting.key)
                shown = "***" if setting.secret and value else value
                print(f"{setting.key:<{width}}  {shown!r:<28} [{config.source(setting.key)}]"
                      f"  env={env_var_name(setting.key)}")
            return 0
        if action == "path":
            print(config.path)
            return 0
        if action == "schema":
            print(json.dumps([
                {
                    "key": s.key, "type": s.type, "default": s.default, "section": s.section,
                    "label": s.label, "help": s.help, "choices": list(s.choices),
                    "env": env_var_name(s.key),
                }
                for s in SETTINGS
            ], indent=2, ensure_ascii=False))
            return 0
        if action == "get":
            print(config.get(args.key))
            return 0
        if action == "set":
            scope = "profile" if args.profile_scope else "global"
            value = config.set(args.key, args.value, scope=scope)
            config.save()
            print(f"{args.key} = {value!r} ({scope})")
            return 0
        if action == "unset":
            config.unset(args.key)
            config.save()
            print(f"{args.key} supprime")
            return 0
        if action == "export":
            print(config.export_to(args.path))
            return 0
        if action == "import":
            config.import_from(args.path, merge=not args.replace)
            config.save()
            print(f"importe depuis {args.path}")
            return 0
        if action == "reset":
            config.reset()
            config.save()
            print("valeurs par defaut restaurees")
            return 0
    except (ConfigError, OSError, ValueError) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 2
    return 2


def _log_command(config: Config, args: argparse.Namespace) -> int:
    path = resolve_log_file(config)
    action = args.log_command
    if action == "path":
        print(path)
        return 0
    if action == "list":
        files = list_log_files(config)
        if not files:
            print("aucun fichier de journal")
        for item in files:
            print(f"{item}  {item.stat().st_size} o")
        return 0
    if action == "tail":
        if not path.exists():
            print(f"journal absent : {path}", file=sys.stderr)
            return 1
        print(read_tail(path, args.lines))
        return 0
    if action == "annotate":
        text = " ".join(args.text).strip()
        if not text:
            print("commentaire vide", file=sys.stderr)
            return 2
        print(annotate(text, author=args.author))
        return 0
    if action == "clear":
        files = list_log_files(config)
        if not files:
            print("aucun fichier de journal")
            return 0
        if not args.yes:
            print("a supprimer :")
            for item in files:
                print(f"  {item}")
            if input("confirmer ? [o/N] ").strip().lower() not in {"o", "oui", "y", "yes"}:
                print("annule")
                return 1
        for item in files:
            try:
                item.unlink()
            except OSError as exc:
                print(f"erreur : {item} : {exc}", file=sys.stderr)
                return 1
        print(f"{len(files)} fichier(s) supprime(s)")
        return 0
    return 2


def _profile_command(config: Config, args: argparse.Namespace) -> int:
    try:
        if args.profile_command == "list":
            for name in config.profile_names():
                print(f"{'*' if name == config.active_profile else ' '} {name}")
            return 0
        if args.profile_command == "create":
            config.create_profile(args.name, copy_current=args.copy)
            config.save()
            print(f"profil cree : {args.name}")
            return 0
        if args.profile_command == "use":
            config.use_profile(args.name)
            config.save()
            print(f"profil actif : {args.name}")
            return 0
        if args.profile_command == "delete":
            config.delete_profile(args.name)
            config.save()
            print(f"profil supprime : {args.name}")
            return 0
    except (ConfigError, OSError) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
