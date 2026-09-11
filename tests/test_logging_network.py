"""Tests des journaux, des options reseau et de la desinstallation."""

from __future__ import annotations

import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edac.config import Config, hosts_in, uses_network  # noqa: E402
from edac.logging_setup import (annotate, list_log_files, log_command_end,  # noqa: E402
                                log_command_start, read_tail, resolve_log_file,
                                setup_logging)
from edac.uninstall import collect_targets, human, size_of  # noqa: E402


def make_config(tmp: Path, **values) -> Config:
    config = Config(path=tmp / "config.json", use_env=False)
    config.set("logging.file", str(tmp / "logs" / "edac.log"))
    for key, value in values.items():
        config.set(key.replace("__", "."), value)
    return config


class LoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        for handler in list(logging.getLogger("edac").handlers):
            handler.close()
            logging.getLogger("edac").removeHandler(handler)
        self._tmp.cleanup()

    def test_file_created_and_annotated(self) -> None:
        config = make_config(self.tmp)
        setup_logging(config)
        annotate("verification du build", author="user")
        path = resolve_log_file(config)
        self.assertTrue(path.exists())
        self.assertIn("[user] verification du build", path.read_text(encoding="utf-8"))

    def test_command_lifecycle_recorded(self) -> None:
        config = make_config(self.tmp)
        setup_logging(config)
        log_command_start("npm run build")
        log_command_end("npm run build", 1, 2.5)
        content = resolve_log_file(config).read_text(encoding="utf-8")
        self.assertIn("commande demarree : npm run build", content)
        self.assertIn("code 1", content)
        self.assertIn("ERROR", content)

    def test_json_format(self) -> None:
        config = make_config(self.tmp, logging__format="json")
        setup_logging(config)
        annotate("json", author="agent")
        line = resolve_log_file(config).read_text(encoding="utf-8").strip().splitlines()[-1]
        payload = json.loads(line)
        self.assertEqual(payload["level"], "INFO")
        self.assertIn("json", payload["message"])

    def test_rotation_keeps_backups(self) -> None:
        config = make_config(self.tmp, logging__max_size_mb=1, logging__backup_count=2)
        setup_logging(config)
        logger = logging.getLogger("edac")
        for index in range(4000):
            logger.info("ligne de remplissage %s %s", index, "x" * 300)
        files = list_log_files(config)
        self.assertGreater(len(files), 1)
        self.assertLessEqual(len(files), 3)

    def test_level_filters_debug(self) -> None:
        config = make_config(self.tmp, logging__level="WARNING")
        setup_logging(config)
        logging.getLogger("edac").debug("invisible")
        logging.getLogger("edac").warning("visible")
        content = resolve_log_file(config).read_text(encoding="utf-8")
        self.assertNotIn("invisible", content)
        self.assertIn("visible", content)

    def test_disabled_file_logging(self) -> None:
        config = make_config(self.tmp, logging__to_file=False)
        setup_logging(config)
        annotate("rien sur disque")
        self.assertFalse(resolve_log_file(config).exists())

    def test_read_tail(self) -> None:
        config = make_config(self.tmp)
        setup_logging(config)
        for index in range(50):
            logging.getLogger("edac").info("ligne %s", index)
        tail = read_tail(resolve_log_file(config), 5)
        self.assertEqual(len(tail.splitlines()), 5)
        self.assertIn("ligne 49", tail)


class NetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.config = Config(path=Path(self._tmp.name) / "config.json", use_env=False)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_uses_network_detection(self) -> None:
        self.assertTrue(uses_network("npm install"))
        self.assertTrue(uses_network("curl https://example.com"))
        self.assertFalse(uses_network("npm run build"))

    def test_hosts_in(self) -> None:
        self.assertEqual(hosts_in("git clone https://github.com/a/b.git"), ["github.com"])
        self.assertEqual(hosts_in("echo local"), [])

    def test_offline_blocks_network_command(self) -> None:
        self.config.set("network.offline", True)
        allowed, reason = self.config.is_command_allowed("npm install")
        self.assertFalse(allowed)
        self.assertIn("hors-ligne", reason)
        self.assertTrue(self.config.is_command_allowed("npm run build")[0])

    def test_allowed_hosts(self) -> None:
        self.config.set("network.allowed_hosts", "npmjs.org")
        self.assertTrue(self.config.is_command_allowed("curl https://registry.npmjs.org/x")[0])
        allowed, reason = self.config.is_command_allowed("curl https://evil.test/x")
        self.assertFalse(allowed)
        self.assertIn("evil.test", reason)

    def test_protected_push(self) -> None:
        self.assertFalse(self.config.is_command_allowed("git push origin main")[0])
        self.config.set("git.push_protected", True)
        self.assertTrue(self.config.is_command_allowed("git push origin main")[0])
        self.assertTrue(self.config.is_command_allowed("git push origin feature")[0])

    def test_environment_exports_proxies(self) -> None:
        self.config.set("network.http_proxy", "http://proxy.local:3128")
        self.config.set("network.no_proxy", "localhost,127.0.0.1")
        self.config.set("network.verify_tls", False)
        env = self.config.environment()
        self.assertEqual(env["HTTP_PROXY"], "http://proxy.local:3128")
        self.assertEqual(env["NO_PROXY"], "localhost,127.0.0.1")
        self.assertEqual(env["GIT_SSL_NO_VERIFY"], "1")
        self.assertEqual(env["EDAC_NETWORK_TIMEOUT"], "60")

    def test_timeout_bounds(self) -> None:
        with self.assertRaises(Exception):
            self.config.set("network.timeout_seconds", 1)


class UninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.config = Config(path=self.tmp / "config.json", use_env=False)
        self.config.set("logging.file", str(self.tmp / "logs" / "edac.log"))
        self.config.save()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_keep_config_excludes_config_file(self) -> None:
        kept = [t.path for t in collect_targets(self.config, keep_config=True,
                                                keep_logs=True, keep_venv=True)]
        self.assertNotIn(self.config.path, kept)
        removed = [t.path for t in collect_targets(self.config, keep_config=False,
                                                   keep_logs=True, keep_venv=True)]
        self.assertIn(self.config.path, removed)

    def test_keep_venv_excludes_venv(self) -> None:
        kept = [t.path.name for t in collect_targets(self.config, keep_config=True,
                                                     keep_logs=True, keep_venv=True)]
        self.assertNotIn(".venv", kept)

    def test_size_and_human(self) -> None:
        sample = self.tmp / "sample.bin"
        sample.write_bytes(b"0" * 2048)
        self.assertEqual(size_of(sample), 2048)
        self.assertEqual(human(2048), "2.0 Ko")


if __name__ == "__main__":
    unittest.main()
