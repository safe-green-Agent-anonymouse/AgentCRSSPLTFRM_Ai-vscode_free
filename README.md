# Expert Dev Autopilot — Console (.exe + .bat)

Application **fenetree Windows** (Tkinter, aucune dependance externe) qui pilote
l'agent `expert-dev-autopilot` : actions de build et de packaging, module de
configuration complet, journal en flux. Utilisable aussi en ligne de commande
et sous Linux/macOS.

## Demarrage rapide (Windows)

```bat
setup.bat        :: verifie Python 3.10+, cree .venv, installe PyInstaller
run.bat          :: ouvre la fenetre (sans console noire)
build-exe.bat    :: produit dist\EDAC-Console.exe + taille + SHA-256
```

Linux / macOS : `./run.sh` (necessite `python3-tk`).

## Fenetre

| Onglet | Contenu |
| --- | --- |
| Tableau de bord | 11 actions (setup, dev, lint, test, build, package .exe/.apk/.dmg, verify, clean, doctor), commande personnalisee, bouton Stop, chaine autopilot complete |
| Configuration | formulaire genere depuis le schema, 6 sections, profils, appliquer/enregistrer/recharger/defauts/exporter/importer |
| Journal | sortie en flux, coloree par niveau, secrets masques, export `.log` |
| A propos | chemin de config, plateforme, rappel des garde-fous |

Raccourcis : `Ctrl+S` enregistrer · `Ctrl+L` vider le journal · `Echap` stopper
la commande en cours.

## Module de configuration

Priorite croissante :

```
defauts  <  fichier  <  profil actif  <  variables EDAC_*  <  --set cle=valeur
```

- Fichier : `%APPDATA%\ExpertDevAutopilot\config.json` (Windows),
  `~/.config/ExpertDevAutopilot/config.json` (Linux),
  `~/Library/Application Support/...` (macOS). Ecriture atomique + `.bak`.
- 30 reglages types (`bool`, `int`, `choice`, `path`, `list`) valides et
  convertis a la lecture comme a l'ecriture ; les cles inconnues d'anciennes
  versions sont signalees, pas fatales.
- Profils nommes (`default`, `ci`, `perso`, …) avec heritage des valeurs
  globales.
- Chaque cle a une variable d'environnement dediee : `project.stack` →
  `EDAC_PROJECT_STACK`.

### CLI

```bash
python -m edac config list        # valeurs effectives + origine (cli/env/profile/file/default)
python -m edac config schema      # schema JSON complet
python -m edac config set build.default_target apk
python -m edac profile create ci --copy
python -m edac --set ui.theme=sombre run build
python -m edac exec "npm run lint"
python -m edac doctor
```

Sous Windows, `run.bat` accepte les memes arguments : `run.bat config list`.

## Journal avec commentaires

Chaque commande est encadree dans un fichier de log rotatif par une annotation
horadatee (`# 22:31:07 [agent] debut : npm run build`), et vous pouvez inserer
vos propres commentaires depuis la fenetre (onglet **Journal**, champ
« Commentaire », `Ctrl+M`) ou en ligne de commande.

```bash
python -m edac log path                       # emplacement du fichier
python -m edac log tail -n 100                # dernieres lignes
python -m edac log annotate "on teste le build signe"
python -m edac log list                       # fichiers de rotation
python -m edac log clear --yes                # purge
```

Emplacement par defaut : `%LOCALAPPDATA%\ExpertDevAutopilot\logs\` (Windows),
`~/.local/state/ExpertDevAutopilot/logs/` (Linux),
`~/Library/Logs/ExpertDevAutopilot/` (macOS).

Section **Journalisation** de la configuration : niveau (`DEBUG`…`ERROR`),
format `texte` ou `json` (une ligne JSON par evenement), taille max par
fichier, nombre de fichiers de rotation, sortie console, journalisation de la
sortie des commandes, annotation automatique.

## Options reseau

Section **Reseau** : mode hors-ligne, proxy HTTP/HTTPS, `NO_PROXY`, timeout,
nombre de tentatives, registre npm, index pip, hotes autorises, verification
TLS. Les valeurs sont exportees vers les commandes enfants (`HTTP_PROXY`,
`HTTPS_PROXY`, `NO_PROXY`, `NPM_CONFIG_REGISTRY`, `PIP_INDEX_URL`,
`EDAC_NETWORK_TIMEOUT`, `EDAC_NETWORK_RETRIES`).

```bash
python -m edac config set network.http_proxy http://proxy.interne:3128
python -m edac config set network.allowed_hosts registry.npmjs.org,github.com
python -m edac --set network.offline=true run build
```

En mode hors-ligne, une commande reseau (`npm install`, `git clone`, `curl`,
toute URL) est refusee avant execution. Si `network.allowed_hosts` est non
vide, seules les URL de ces domaines passent.

## Desinstallation

```bat
uninstall.bat --dry-run          :: plan detaille, rien n'est supprime
uninstall.bat --keep-config      :: garde la configuration
uninstall.bat --yes              :: sans confirmation
```

```bash
./uninstall.sh --dry-run
python -m edac uninstall --keep-logs
```

Sont retires : `.venv`, `build`, `dist`, `release`, les caches `__pycache__`,
le fichier et le dossier de configuration, les journaux et leurs rotations,
et les raccourcis bureau / menu Demarrer. Le dossier source du projet n'est
jamais supprime, et une confirmation est demandee sauf avec `--yes`. Si
l'application a ete installee via `EDAC-Console-Setup.exe`, desinstallez-la
aussi depuis *Parametres > Applications*.

## Garde-fous

`Securite > Commandes bloquees` refuse toute commande contenant un motif
interdit (`rm -rf /`, `git push --force origin main`, `DROP DATABASE`,
`format c:`), y compris quand « Allow all » est actif. Les valeurs qui
ressemblent a des secrets (`token=`, `password=`, `keystore=`) sont masquees
dans le journal. Un `git push` vers `main`/`master` est refuse tant que
`git.push_protected` reste desactive.

## Construction du .exe

`build-exe.bat` appelle PyInstaller avec `edac.spec` (`console=False`,
`--onefile`) puis verifie l'artefact et affiche son empreinte SHA-256.
Signature optionnelle :

```bat
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f cert.pfx dist\EDAC-Console.exe
```

Installateur optionnel : `iscc installer.iss` (Inno Setup 6) → 
`release\EDAC-Console-Setup-1.0.0.exe`.

Le workflow `.github/workflows/windows-exe.yml` execute les tests sur Ubuntu
puis construit et publie le `.exe` sur `windows-latest`.

## Tests

```bash
python -m unittest discover -s tests -v   # 36 tests : config, profils, garde-fous, journaux, reseau, desinstallation
```

## Limite verifiee

Le `.exe` ne peut pas etre produit sur Linux : PyInstaller ne fait pas de
compilation croisee. Utilisez `build-exe.bat` sur Windows ou le job CI
`windows-latest`. Le code Python, la CLI et la fenetre ont ete executes et
valides sous Linux.
