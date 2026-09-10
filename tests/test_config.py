import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edac.config import Config, ConfigError, env_var_name, parse_overrides  # noqa: E402
from edac.runner import build_command, redact, resolve_shell  # noqa: E402


class ConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"
        self.addCleanup(self.tmp.cleanup)
        for name in list(os.environ):
            if name.startswith("EDAC_"):
                del os.environ[name]

    def config(self, **kwargs) -> Config:
        return Config.load(self.path, use_env=kwargs.pop("use_env", False), **kwargs)

    def test_defaults(self):
        config = self.config()
        self.assertEqual(config.get("build.default_target"), "exe")
        self.assertTrue(config.get("autopilot.allow_all"))
        self.assertEqual(config.source("ui.theme"), "default")

    def test_unknown_key_raises(self):
        with self.assertRaises(ConfigError):
            self.config().get("nope.nope")

    def test_coercion_and_validation(self):
        config = self.config()
        self.assertIs(config.set("autopilot.enabled", "oui"), True)
        self.assertEqual(config.set("autopilot.max_retries", "5"), 5)
        self.assertEqual(config.set("build.extra_args", "--a, --b"), ["--a", "--b"])
        with self.assertRaises(ConfigError):
            config.set("autopilot.max_retries", 99)
        with self.assertRaises(ConfigError):
            config.set("ui.theme", "fluo")
        with self.assertRaises(ConfigError):
            config.set("autopilot.enabled", "peut-etre")

    def test_save_reload_and_backup(self):
        config = self.config()
        config.set("project.stack", "rust")
        config.save()
        self.assertTrue(self.path.exists())
        again = self.config()
        self.assertEqual(again.get("project.stack"), "rust")
        again.set("project.stack", "node")
        again.save()
        self.assertTrue(self.path.with_suffix(".json.bak").exists())
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)

    def test_layer_priority(self):
        config = self.config()
        config.set("ui.theme", "clair")             # fichier
        config.create_profile("nuit")
        config.use_profile("nuit")
        config.set("ui.theme", "sombre", scope="profile")
        self.assertEqual(config.get("ui.theme"), "sombre")
        self.assertEqual(config.source("ui.theme"), "profile")

        config.use_env = True
        os.environ[env_var_name("ui.theme")] = "clair"
        self.addCleanup(os.environ.pop, env_var_name("ui.theme"), None)
        self.assertEqual(config.get("ui.theme"), "clair")
        self.assertEqual(config.source("ui.theme"), "env")

        config.overrides = parse_overrides(["ui.theme=sombre"])
        self.assertEqual(config.get("ui.theme"), "sombre")
        self.assertEqual(config.source("ui.theme"), "cli")

    def test_profiles(self):
        config = self.config()
        config.create_profile("ci")
        config.use_profile("ci")
        config.set("build.default_target", "apk", scope="profile")
        config.use_profile("default")
        self.assertEqual(config.get("build.default_target"), "exe")
        with self.assertRaises(ConfigError):
            config.use_profile("inconnu")
        with self.assertRaises(ConfigError):
            config.delete_profile("default")
        config.use_profile("ci")
        config.delete_profile("ci")
        self.assertEqual(config.active_profile, "default")

    def test_export_import(self):
        config = self.config()
        config.set("project.stack", "flutter")
        target = Path(self.tmp.name) / "export.json"
        config.export_to(target)
        other = Config.load(Path(self.tmp.name) / "other.json", use_env=False)
        other.import_from(target)
        self.assertEqual(other.get("project.stack"), "flutter")

    def test_import_rejects_invalid(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text(json.dumps({"values": {"ui.font_size": 999}}), encoding="utf-8")
        with self.assertRaises(ConfigError):
            self.config().import_from(bad)

    def test_unknown_keys_reported_not_crashing(self):
        self.path.write_text(json.dumps({"values": {"vieille.cle": 1, "ui.theme": "sombre"}}),
                             encoding="utf-8")
        config = self.config()
        self.assertIn("vieille.cle", config.validate())
        self.assertEqual(config.get("ui.theme"), "sombre")

    def test_blocked_commands_guardrail(self):
        config = self.config()
        allowed, reason = config.is_command_allowed("sudo rm -rf / --no-preserve-root")
        self.assertFalse(allowed)
        self.assertIn("bloquee", reason)
        self.assertTrue(config.is_command_allowed("npm run build")[0])

    def test_environment_mapping(self):
        config = self.config()
        config.set("env.android_home", "/opt/android")
        env = config.environment()
        self.assertEqual(env["ANDROID_HOME"], "/opt/android")
        self.assertEqual(env["ANDROID_SDK_ROOT"], "/opt/android")

    def test_diff_and_as_dict(self):
        config = self.config()
        config.set("ui.font_size", 14)
        self.assertEqual(config.diff_from_defaults()["ui.font_size"], (10, 14))
        self.assertEqual(config.as_dict()["ui.font_size"], 14)

    def test_parse_overrides_errors(self):
        with self.assertRaises(ConfigError):
            parse_overrides(["sans_egal"])
        with self.assertRaises(ConfigError):
            parse_overrides(["cle.inconnue=1"])
        collected: list[str] = []
        self.assertEqual(parse_overrides(["mauvais"], on_error=collected.append), {})
        self.assertEqual(len(collected), 1)


class RunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Config.load(Path(self.tmp.name) / "c.json", use_env=False)
        self.config.set("project.path", self.tmp.name)

    def test_build_command_node_and_python(self):
        self.config.set("project.stack", "node")
        self.config.set("project.package_manager", "pnpm")
        self.assertEqual(build_command(self.config, "setup"), "pnpm install")
        self.config.set("project.stack", "python")
        self.assertIn("pytest", build_command(self.config, "test"))

    def test_build_command_packaging(self):
        self.config.set("project.stack", "node")
        self.assertIn("electron-builder --win nsis", build_command(self.config, "package:exe"))
        self.config.set("project.stack", "flutter")
        self.assertIn("flutter build apk", build_command(self.config, "package:apk"))

    def test_build_command_extra_args(self):
        self.config.set("project.stack", "node")
        self.config.set("build.extra_args", "--x64")
        self.assertTrue(build_command(self.config, "package:exe").endswith("--x64"))

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            build_command(self.config, "inconnue")

    def test_redact(self):
        self.assertEqual(redact("--token=abcd1234"), "--token=***")
        self.assertEqual(redact("npm run build"), "npm run build")

    def test_resolve_shell(self):
        self.assertIn("-lc", resolve_shell("bash"))
        self.assertIn("/c", resolve_shell("cmd"))
        self.assertIn("-Command", resolve_shell("powershell"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
