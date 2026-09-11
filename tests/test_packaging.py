"""Tests du packaging Windows : icone, ressource de version, spec, installeur."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.win_version import read_version, version_tuple, write_version_file

import edac

ROOT = Path(__file__).resolve().parent.parent


class VersionResourceTests(unittest.TestCase):
    def test_version_matches_package(self) -> None:
        self.assertEqual(read_version(), edac.__version__)

    def test_version_tuple_is_padded(self) -> None:
        self.assertEqual(version_tuple("1.2"), (1, 2, 0, 0))
        self.assertEqual(version_tuple("1.2.3.4"), (1, 2, 3, 4))

    def test_written_resource_contains_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_version_file(Path(tmp) / "version_info.txt")
            content = path.read_text(encoding="utf-8")
        self.assertIn("VSVersionInfo", content)
        self.assertIn("EDAC-Console.exe", content)
        self.assertIn(edac.__version__, content)


class WindowedStreamsTests(unittest.TestCase):
    def test_missing_stdout_is_replaced(self) -> None:
        """Sous PyInstaller --windowed, sys.stdout vaut None : la CLI doit tenir."""
        from edac import cli

        original = sys.stdout
        sys.stdout = None  # type: ignore[assignment]
        try:
            cli._ensure_streams()
            self.assertIsNotNone(sys.stdout)
            print("sortie ignoree")
        finally:
            sys.stdout = original


class PackagingFilesTests(unittest.TestCase):
    def test_icon_is_a_multi_size_ico(self) -> None:
        icon = ROOT / "assets" / "icon.ico"
        self.assertTrue(icon.exists(), "assets/icon.ico manquant")
        self.assertEqual(icon.read_bytes()[:4], b"\x00\x00\x01\x00")

    def test_spec_uses_icon_and_version(self) -> None:
        spec = (ROOT / "edac.spec").read_text(encoding="utf-8")
        self.assertIn("icon=", spec)
        self.assertIn("version=", spec)

    def test_spec_entry_point_is_importable_as_script(self) -> None:
        """L'entree gelee ne doit pas utiliser d'import relatif (ImportError)."""
        spec = (ROOT / "edac.spec").read_text(encoding="utf-8")
        self.assertIn('["app.py"]', spec)
        entry = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("from edac.cli import main", entry)

    def test_frozen_entry_point_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "app.py"), "config", "get", "ui.theme"],
            capture_output=True, text=True, timeout=60, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_signing_is_optional_and_secret_based(self) -> None:
        script = (ROOT / "tools" / "sign_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("WINDOWS_CERT_PFX_BASE64", script)
        self.assertIn("Remove-Item $pfx", script)
        workflow = (ROOT / ".github" / "workflows" / "windows-exe.yml").read_text(encoding="utf-8")
        self.assertIn("tools/sign_windows.ps1", workflow)
        self.assertIn("if: env.WINDOWS_CERT_PFX_BASE64 != ''", workflow)

    def test_workflow_attests_provenance(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-exe.yml").read_text(encoding="utf-8")
        self.assertIn("actions/attest-build-provenance", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)

    def test_no_certificate_is_tracked(self) -> None:
        for pattern in ("*.pfx", "*.p12", "*.key"):
            self.assertFalse(list(ROOT.rglob(pattern)), f"certificat present : {pattern}")
            self.assertIn(pattern, (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_installer_declares_uninstall_cleanup(self) -> None:
        iss = (ROOT / "installer.iss").read_text(encoding="utf-8")
        for expected in ("UninstallDisplayIcon", "SetupIconFile", "[UninstallDelete]", "AppId"):
            self.assertIn(expected, iss)


if __name__ == "__main__":
    unittest.main()
