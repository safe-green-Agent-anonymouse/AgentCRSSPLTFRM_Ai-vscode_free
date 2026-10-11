"""Desktop launcher for the bundled Nova Studio web application."""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def resolve_web_root(bundle_dir: Path | None = None) -> Path:
    """Find the bundled web assets in development and PyInstaller builds."""
    if bundle_dir is not None:
        base = bundle_dir
    else:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    web_root = base / "web"
    if not (web_root / "index.html").is_file():
        raise FileNotFoundError(f"Nova Studio web assets were not found in {web_root}")
    return web_root


def show_startup_error(error: Exception) -> None:
    message = (
        "Nova Studio n'a pas pu démarrer. Vérifiez que Microsoft Edge WebView2 Runtime "
        "est installé, puis réessayez.\n\n"
        "Téléchargement : https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
        f"Détail : {error}"
    )
    ctypes.windll.user32.MessageBoxW(None, message, "Nova Studio", 0x10)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lance Nova Studio sur Windows.")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        web_root = resolve_web_root()
    except FileNotFoundError as error:
        show_startup_error(error)
        return 1

    if args.self_test:
        print(f"Nova Studio assets OK ({platform.architecture()[0]})")
        return 0

    server = None
    server_thread = None
    try:
        from webview import create_window, start

        storage_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        storage_path = storage_root / "NovaStudio" / "WebView2"
        storage_path.mkdir(parents=True, exist_ok=True)

        handler = partial(SimpleHTTPRequestHandler, directory=str(web_root))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        create_window(
            "Nova Studio",
            url=f"http://127.0.0.1:{server.server_port}/index.html",
            width=1440,
            height=920,
            min_size=(900, 620),
            text_select=True,
            storage_path=str(storage_path),
        )
        start(gui="edgechromium", debug=False)
        return 0
    except Exception as error:
        show_startup_error(error)
        return 1
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None:
            server_thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
