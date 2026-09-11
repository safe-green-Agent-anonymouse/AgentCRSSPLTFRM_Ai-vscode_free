# Starter kit — expert-dev-autopilot

Squelette d'outillage cross-plateforme utilisé par l'agent
`expert-dev-autopilot` : mêmes verbes de build dans les trois shells, plus les
tâches et configurations de debug VS Code.

## Verbes disponibles

`setup` · `dev` · `test` · `lint` · `build` · `package <exe|apk|dmg>` ·
`verify` · `clean`

## Commandes

| Shell | Exemple |
| --- | --- |
| bash / zsh / Git Bash | `./scripts/build.sh package apk` |
| cmd.exe | `scripts\build.cmd package exe` |
| PowerShell 7+ | `pwsh ./scripts/build.ps1 package dmg` |

## VS Code

`Ctrl+Maj+P` → *Run Task* → `package: exe` / `package: apk` / `package: dmg`.
Les tâches sélectionnent automatiquement `build.sh` ou `build.cmd` selon l'OS.
`F5` lance les configurations de `launch.json` (frontend, backend Node ou
FastAPI, tests, compound full stack).

## Contraintes de packaging

- `.exe` : Electron/Tauri/PyInstaller/.NET — signature `signtool` sur Windows.
- `.apk` : JDK + SDK Android (`ANDROID_HOME`), Gradle ou Flutter — signature
  par keystore fourni via variables d'environnement.
- `.dmg` : **macOS obligatoire** pour la construction, la signature
  (`codesign`) et la notarisation (`notarytool`). Sur Linux/Windows, le script
  échoue explicitement et renvoie vers le job CI `macos-latest`.

`verify` affiche taille, type et empreinte SHA-256 de chaque artefact : un
build sans cette sortie est considéré comme non vérifié.
