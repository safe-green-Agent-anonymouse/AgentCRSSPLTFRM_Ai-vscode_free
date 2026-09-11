"""Module de configuration de Expert Dev Autopilot Console.

Couches, de la plus faible a la plus forte priorite :

    defaults  <  fichier de config  <  profil actif  <  variables d'env  <  overrides CLI

Le fichier de configuration est un JSON unique contenant les valeurs globales,
les profils nommes et le profil actif. Toutes les valeurs sont validees et
converties selon le schema declare dans SETTINGS.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

APP_NAME = "ExpertDevAutopilot"
ENV_PREFIX = "EDAC_"
CONFIG_VERSION = 1


class ConfigError(ValueError):
    """Valeur invalide ou cle inconnue."""


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Setting:
    key: str
    type: str  # str | bool | int | path | choice | list
    default: Any
    section: str
    label: str
    help: str = ""
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    secret: bool = False

    def coerce(self, value: Any) -> Any:
        if value is None:
            return self.default
        try:
            if self.type == "bool":
                return _to_bool(value)
            if self.type == "int":
                number = int(str(value).strip())
                if self.minimum is not None and number < self.minimum:
                    raise ConfigError(f"{self.key}: {number} < minimum {self.minimum}")
                if self.maximum is not None and number > self.maximum:
                    raise ConfigError(f"{self.key}: {number} > maximum {self.maximum}")
                return number
            if self.type == "list":
                if isinstance(value, str):
                    return [item.strip() for item in value.split(",") if item.strip()]
                return [str(item) for item in value]
            if self.type == "choice":
                text = str(value)
                if text not in self.choices:
                    raise ConfigError(f"{self.key}: '{text}' hors de {list(self.choices)}")
                return text
            if self.type == "path":
                text = str(value).strip()
                return str(Path(text).expanduser()) if text else ""
            return str(value)
        except ConfigError:
            raise
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{self.key}: valeur invalide ({value!r}) : {exc}") from exc


NETWORK_PATTERNS: tuple[str, ...] = (
    "npm install", "npm ci", "npm publish", "pnpm install", "yarn install", "bun install",
    "pip install", "poetry install", "uv sync", "cargo fetch", "cargo publish",
    "gradle", "gradlew", "flutter pub", "dotnet restore", "go mod",
    "git clone", "git fetch", "git pull", "git push", "npx", "curl", "wget",
    "docker pull", "docker push", "apt-get", "brew install", "choco install",
)


def uses_network(command: str) -> bool:
    """Heuristique : la commande a-t-elle besoin du reseau ?"""
    lowered = command.lower()
    return any(pattern in lowered for pattern in NETWORK_PATTERNS) or "://" in lowered


def hosts_in(command: str) -> list[str]:
    """Extrait les hotes des URL presentes dans une commande."""
    hosts: list[str] = []
    for match in re.findall(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s'\"]+", command):
        host = urlparse(match).hostname
        if host:
            hosts.append(host.lower())
    return hosts


def _is_protected_push(lowered_command: str) -> bool:
    if "git push" not in lowered_command:
        return False
    return any(branch in lowered_command for branch in (" main", " master", ":main", ":master"))


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "oui", "vrai"}:
        return True
    if text in {"0", "false", "no", "off", "non", "faux"}:
        return False
    raise ConfigError(f"booleen attendu, recu {value!r}")


SETTINGS: tuple[Setting, ...] = (
    # --- Projet ---
    Setting("project.path", "path", "", "Projet", "Dossier du projet",
            "Racine du projet sur lequel l'agent travaille."),
    Setting("project.stack", "choice", "auto", "Projet", "Stack",
            "Stack cible ; 'auto' detecte via les manifestes presents.",
            choices=("auto", "node", "python", "rust", "dotnet", "flutter", "godot", "unity")),
    Setting("project.package_manager", "choice", "auto", "Projet", "Gestionnaire de paquets",
            choices=("auto", "npm", "pnpm", "yarn", "bun", "pip", "poetry", "uv", "cargo")),
    # --- Autopilot ---
    Setting("autopilot.enabled", "bool", True, "Autopilot", "Activer l'autopilot",
            "Enchaine plan -> generation -> execution -> correction sans confirmation."),
    Setting("autopilot.allow_all", "bool", True, "Autopilot", "Allow all (non destructif)",
            "Autorise toutes les actions non destructives sans demander."),
    Setting("autopilot.confirm_destructive", "bool", True, "Autopilot", "Confirmer les actions destructives",
            "Garde-fou : suppressions massives, force-push, secrets, deploiements."),
    Setting("autopilot.max_retries", "int", 3, "Autopilot", "Tentatives max par etape",
            minimum=1, maximum=10),
    Setting("autopilot.timeout_seconds", "int", 1800, "Autopilot", "Timeout par commande (s)",
            minimum=10, maximum=86400),
    Setting("autopilot.learn", "bool", True, "Autopilot", "Apprentissage continu",
            "Ecrit conventions, echecs et correctifs dans le dossier memoire."),
    Setting("autopilot.memory_dir", "path", ".agent/memory", "Autopilot", "Dossier memoire"),
    # --- Build ---
    Setting("build.default_target", "choice", "exe", "Build", "Cible par defaut",
            choices=("exe", "apk", "dmg", "web")),
    Setting("build.release_dir", "path", "release", "Build", "Dossier des artefacts"),
    Setting("build.verify_artifacts", "bool", True, "Build", "Verifier les artefacts",
            "Affiche taille, type et SHA-256 apres chaque packaging."),
    Setting("build.clean_before", "bool", False, "Build", "Nettoyer avant build"),
    Setting("build.extra_args", "list", [], "Build", "Arguments supplementaires",
            "Liste separee par des virgules, passee au packager."),
    # --- Environnement ---
    Setting("env.shell", "choice", "auto", "Environnement", "Shell",
            "Shell utilise pour executer les commandes.",
            choices=("auto", "bash", "cmd", "powershell")),
    Setting("env.node_path", "path", "", "Environnement", "Chemin Node"),
    Setting("env.java_home", "path", "", "Environnement", "JAVA_HOME"),
    Setting("env.android_home", "path", "", "Environnement", "ANDROID_HOME"),
    Setting("env.python_path", "path", "", "Environnement", "Interpreteur Python"),
    # --- Journalisation ---
    Setting("logging.to_file", "bool", True, "Journalisation", "Ecrire un fichier de log"),
    Setting("logging.file", "path", "", "Journalisation", "Fichier de log",
            "Vide = emplacement standard de la plateforme."),
    Setting("logging.level", "choice", "INFO", "Journalisation", "Niveau",
            choices=("DEBUG", "INFO", "WARNING", "ERROR")),
    Setting("logging.format", "choice", "texte", "Journalisation", "Format",
            "'json' produit une ligne JSON par evenement (ingestion machine).",
            choices=("texte", "json")),
    Setting("logging.max_size_mb", "int", 5, "Journalisation", "Taille max par fichier (Mo)",
            minimum=1, maximum=500),
    Setting("logging.backup_count", "int", 3, "Journalisation", "Fichiers de rotation conserves",
            minimum=0, maximum=50),
    Setting("logging.to_console", "bool", False, "Journalisation", "Aussi sur la console"),
    Setting("logging.log_output", "bool", True, "Journalisation", "Journaliser la sortie des commandes",
            "Chaque ligne produite par une commande est ecrite en DEBUG."),
    Setting("logging.auto_annotate", "bool", True, "Journalisation", "Annoter automatiquement",
            "Encadre chaque commande par un commentaire horodate (debut, code, duree)."),
    # --- Reseau ---
    Setting("network.offline", "bool", False, "Reseau", "Mode hors-ligne",
            "Refuse les commandes qui accedent au reseau (install, clone, curl…)."),
    Setting("network.http_proxy", "str", "", "Reseau", "Proxy HTTP",
            "Ex. http://proxy.interne:3128 ; exporte en HTTP_PROXY."),
    Setting("network.https_proxy", "str", "", "Reseau", "Proxy HTTPS"),
    Setting("network.no_proxy", "list", ["localhost", "127.0.0.1"], "Reseau", "Sans proxy (NO_PROXY)"),
    Setting("network.timeout_seconds", "int", 60, "Reseau", "Timeout reseau (s)",
            minimum=5, maximum=3600),
    Setting("network.retries", "int", 3, "Reseau", "Tentatives reseau", minimum=0, maximum=10),
    Setting("network.registry_npm", "str", "", "Reseau", "Registre npm",
            "Ex. https://registry.npmjs.org ; exporte en NPM_CONFIG_REGISTRY."),
    Setting("network.index_pip", "str", "", "Reseau", "Index pip",
            "Exporte en PIP_INDEX_URL."),
    Setting("network.allowed_hosts", "list", [], "Reseau", "Hotes autorises",
            "Si non vide, seules les commandes ciblant ces hotes passent."),
    Setting("network.verify_tls", "bool", True, "Reseau", "Verifier les certificats TLS",
            "Ne desactiver que pour un miroir interne : desactive, tout est journalise en WARNING."),
    # --- Git ---
    Setting("git.auto_commit", "bool", False, "Git", "Commit automatique apres une etape reussie"),
    Setting("git.branch_prefix", "str", "edac/", "Git", "Prefixe de branche"),
    Setting("git.commit_prefix", "str", "chore(edac): ", "Git", "Prefixe de message de commit"),
    Setting("git.push_protected", "bool", False, "Git", "Autoriser le push sur main/master",
            "Desactive par defaut : garde-fou contre les pushs directs."),
    # --- Interface ---
    Setting("ui.theme", "choice", "system", "Interface", "Theme",
            choices=("system", "clair", "sombre")),
    Setting("ui.font_size", "int", 10, "Interface", "Taille de police", minimum=8, maximum=24),
    Setting("ui.log_lines", "int", 5000, "Interface", "Lignes de journal conservees",
            minimum=200, maximum=100000),
    Setting("ui.confirm_exit", "bool", True, "Interface", "Confirmer la fermeture"),
    # --- Securite ---
    Setting("security.block_secrets_in_logs", "bool", True, "Securite", "Masquer les secrets dans le journal"),
    Setting("security.allow_network", "bool", True, "Securite", "Autoriser les commandes reseau"),
    Setting("security.blocked_commands", "list",
            ["rm -rf /", "git push --force origin main", "DROP DATABASE", "format c:"],
            "Securite", "Commandes bloquees",
            "Toute commande contenant l'un de ces motifs est refusee."),
)

SETTINGS_BY_KEY: dict[str, Setting] = {setting.key: setting for setting in SETTINGS}
SECTIONS: tuple[str, ...] = tuple(dict.fromkeys(setting.section for setting in SETTINGS))


# --------------------------------------------------------------------------- #
# Emplacements
# --------------------------------------------------------------------------- #


def config_dir() -> Path:
    """Dossier de configuration natif de la plateforme."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / APP_NAME


def default_config_path() -> Path:
    override = os.environ.get(f"{ENV_PREFIX}CONFIG_FILE")
    return Path(override).expanduser() if override else config_dir() / "config.json"


def env_var_name(key: str) -> str:
    return ENV_PREFIX + key.replace(".", "_").upper()


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


@dataclass
class Config:
    path: Path = field(default_factory=default_config_path)
    values: dict[str, Any] = field(default_factory=dict)          # couche fichier
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_profile: str = "default"
    overrides: dict[str, Any] = field(default_factory=dict)       # couche CLI
    use_env: bool = True

    # -- chargement / sauvegarde ------------------------------------------- #

    @classmethod
    def load(
        cls,
        path: str | os.PathLike[str] | None = None,
        profile: str | None = None,
        overrides: dict[str, Any] | None = None,
        use_env: bool = True,
    ) -> "Config":
        target = Path(path).expanduser() if path else default_config_path()
        config = cls(path=target, overrides=dict(overrides or {}), use_env=use_env)
        if target.is_file():
            try:
                raw = json.loads(target.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ConfigError(f"config illisible ({target}) : {exc}") from exc
            config.values = dict(raw.get("values", {}))
            config.profiles = {name: dict(vals) for name, vals in raw.get("profiles", {}).items()}
            config.active_profile = str(raw.get("active_profile", "default"))
        if profile:
            config.active_profile = profile
        config.validate()
        return config

    def save(self) -> Path:
        """Ecriture atomique avec sauvegarde de la version precedente."""
        self.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CONFIG_VERSION,
            "active_profile": self.active_profile,
            "values": self.values,
            "profiles": self.profiles,
        }
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_suffix(self.path.suffix + ".bak"))
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=self.path.parent, suffix=".tmp"
        )
        try:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, self.path)
        return self.path

    # -- lecture / ecriture ------------------------------------------------- #

    def get(self, key: str) -> Any:
        setting = self._setting(key)
        for layer in self._layers():
            if key in layer:
                return setting.coerce(layer[key])
        return setting.default

    def source(self, key: str) -> str:
        """D'ou vient la valeur effective : cli | env | profile | file | default."""
        self._setting(key)
        for name, layer in zip(("cli", "env", "profile", "file"), self._layers()):
            if key in layer:
                return name
        return "default"

    def set(self, key: str, value: Any, *, scope: str = "global") -> Any:
        setting = self._setting(key)
        coerced = setting.coerce(value)
        if scope == "profile":
            self.profiles.setdefault(self.active_profile, {})[key] = coerced
        elif scope == "global":
            self.values[key] = coerced
        else:
            raise ConfigError(f"scope inconnu: {scope}")
        return coerced

    def unset(self, key: str, *, scope: str = "global") -> None:
        self._setting(key)
        target = self.profiles.get(self.active_profile, {}) if scope == "profile" else self.values
        target.pop(key, None)

    def reset(self, *, scope: str = "global") -> None:
        if scope == "profile":
            self.profiles[self.active_profile] = {}
        else:
            self.values = {}

    def as_dict(self, *, redact: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for setting in SETTINGS:
            value = self.get(setting.key)
            result[setting.key] = "***" if (redact and setting.secret and value) else value
        return result

    def diff_from_defaults(self) -> dict[str, tuple[Any, Any]]:
        return {
            setting.key: (setting.default, self.get(setting.key))
            for setting in SETTINGS
            if self.get(setting.key) != setting.default
        }

    # -- profils ------------------------------------------------------------ #

    def profile_names(self) -> list[str]:
        return sorted({"default", *self.profiles.keys(), self.active_profile})

    def create_profile(self, name: str, *, copy_current: bool = False) -> None:
        name = name.strip()
        if not name:
            raise ConfigError("nom de profil vide")
        if name in self.profiles:
            raise ConfigError(f"profil deja existant: {name}")
        self.profiles[name] = dict(self.profiles.get(self.active_profile, {})) if copy_current else {}

    def delete_profile(self, name: str) -> None:
        if name == "default":
            raise ConfigError("le profil 'default' ne peut pas etre supprime")
        self.profiles.pop(name, None)
        if self.active_profile == name:
            self.active_profile = "default"

    def use_profile(self, name: str) -> None:
        if name != "default" and name not in self.profiles:
            raise ConfigError(f"profil inconnu: {name}")
        self.active_profile = name

    # -- import / export ---------------------------------------------------- #

    def export_to(self, path: str | os.PathLike[str]) -> Path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "version": CONFIG_VERSION,
                    "active_profile": self.active_profile,
                    "values": self.values,
                    "profiles": self.profiles,
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return target

    def import_from(self, path: str | os.PathLike[str], *, merge: bool = True) -> None:
        source = Path(path).expanduser()
        raw = json.loads(source.read_text(encoding="utf-8"))
        incoming = dict(raw.get("values", {}))
        self.values = {**self.values, **incoming} if merge else incoming
        for name, vals in raw.get("profiles", {}).items():
            self.profiles[name] = {**self.profiles.get(name, {}), **vals} if merge else dict(vals)
        self.validate()

    # -- validation --------------------------------------------------------- #

    def validate(self) -> list[str]:
        """Valide chaque couche ; retourne les cles inconnues rencontrees."""
        unknown: list[str] = []
        for layer in (self.values, *self.profiles.values(), self.overrides):
            for key, value in list(layer.items()):
                setting = SETTINGS_BY_KEY.get(key)
                if setting is None:
                    unknown.append(key)
                    continue
                layer[key] = setting.coerce(value)
        return unknown

    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Garde-fous : commandes bloquees, reseau, push protege."""
        lowered = command.lower()
        for pattern in self.get("security.blocked_commands"):
            if str(pattern).lower() in lowered:
                return False, f"commande bloquee par la configuration : '{pattern}'"

        network = uses_network(command)
        if network and (self.get("network.offline") or not self.get("security.allow_network")):
            return False, "mode hors-ligne actif : commande reseau refusee"

        allowed_hosts = [str(host).lower() for host in self.get("network.allowed_hosts")]
        if allowed_hosts:
            hosts = hosts_in(command)
            forbidden = [host for host in hosts
                         if not any(host == allowed or host.endswith("." + allowed)
                                    for allowed in allowed_hosts)]
            if forbidden:
                return False, f"hote non autorise : {', '.join(forbidden)}"

        if not self.get("git.push_protected") and _is_protected_push(lowered):
            return False, "push direct sur main/master desactive (Git > Autoriser le push)"
        return True, ""

    def environment(self) -> dict[str, str]:
        """Variables d'environnement derivees de la configuration."""
        env = dict(os.environ)
        mapping = {
            "JAVA_HOME": "env.java_home",
            "ANDROID_HOME": "env.android_home",
            "ANDROID_SDK_ROOT": "env.android_home",
        }
        for name, key in mapping.items():
            value = self.get(key)
            if value:
                env[name] = str(value)
        node_path = self.get("env.node_path")
        if node_path:
            env["PATH"] = os.pathsep.join([str(node_path), env.get("PATH", "")])

        network_mapping = {
            "HTTP_PROXY": "network.http_proxy",
            "http_proxy": "network.http_proxy",
            "HTTPS_PROXY": "network.https_proxy",
            "https_proxy": "network.https_proxy",
            "NPM_CONFIG_REGISTRY": "network.registry_npm",
            "PIP_INDEX_URL": "network.index_pip",
        }
        for name, key in network_mapping.items():
            value = self.get(key)
            if value:
                env[name] = str(value)
        no_proxy = self.get("network.no_proxy")
        if no_proxy:
            env["NO_PROXY"] = env["no_proxy"] = ",".join(map(str, no_proxy))
        env["EDAC_NETWORK_TIMEOUT"] = str(self.get("network.timeout_seconds"))
        env["EDAC_NETWORK_RETRIES"] = str(self.get("network.retries"))
        if not self.get("network.verify_tls"):
            env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            env["GIT_SSL_NO_VERIFY"] = "1"
            env["PYTHONHTTPSVERIFY"] = "0"
        if self.get("network.offline"):
            env["EDAC_OFFLINE"] = "1"
        return env

    # -- interne ------------------------------------------------------------ #

    def _setting(self, key: str) -> Setting:
        setting = SETTINGS_BY_KEY.get(key)
        if setting is None:
            raise ConfigError(f"cle inconnue: {key}")
        return setting

    def _env_layer(self) -> dict[str, Any]:
        if not self.use_env:
            return {}
        found: dict[str, Any] = {}
        for setting in SETTINGS:
            raw = os.environ.get(env_var_name(setting.key))
            if raw is not None:
                found[setting.key] = raw
        return found

    def _layers(self) -> tuple[dict[str, Any], ...]:
        return (
            self.overrides,
            self._env_layer(),
            self.profiles.get(self.active_profile, {}),
            self.values,
        )


def settings_in(section: str) -> Iterable[Setting]:
    return (setting for setting in SETTINGS if setting.section == section)


def parse_overrides(pairs: Iterable[str], on_error: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Transforme ['cle=valeur', ...] en dictionnaire d'overrides valide."""
    result: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            message = f"override invalide (attendu cle=valeur) : {pair}"
            if on_error:
                on_error(message)
                continue
            raise ConfigError(message)
        key, _, value = pair.partition("=")
        key = key.strip()
        setting = SETTINGS_BY_KEY.get(key)
        if setting is None:
            message = f"cle inconnue: {key}"
            if on_error:
                on_error(message)
                continue
            raise ConfigError(message)
        result[key] = setting.coerce(value.strip())
    return result
