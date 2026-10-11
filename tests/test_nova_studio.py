import tempfile
import unittest
from pathlib import Path

from nova_studio import resolve_web_root


class NovaStudioPackagingTests(unittest.TestCase):
    def test_resolves_web_assets_from_source_tree(self):
        web_root = resolve_web_root()
        self.assertTrue((web_root / "index.html").is_file())
        self.assertTrue((web_root / "manifest.webmanifest").is_file())

    def test_reports_missing_bundled_assets(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(FileNotFoundError, "web assets were not found"):
                resolve_web_root(Path(temporary_directory))


if __name__ == "__main__":
    unittest.main()
