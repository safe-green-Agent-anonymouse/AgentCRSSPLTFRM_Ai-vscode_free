#!/usr/bin/env bash
# Entrée de build unifiée (bash / zsh / Git Bash).
# Usage: ./scripts/build.sh <setup|dev|test|lint|build|package|verify|clean> [cible]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CMD="${1:-help}"
TARGET="${2:-}"
RELEASE_DIR="release"

log() { printf '\033[36m[build]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[build] %s\033[0m\n' "$*" >&2; exit 1; }
has() { command -v "$1" >/dev/null 2>&1; }

host_os() {
  case "$(uname -s 2>/dev/null || echo unknown)" in
    Linux*) echo linux ;;
    Darwin*) echo macos ;;
    MINGW*|MSYS*|CYGWIN*) echo windows ;;
    *) echo unknown ;;
  esac
}

require() { has "$1" || die "outil manquant: $1"; }

package_exe() {
  [ "$(host_os)" = "windows" ] || log "ATTENTION: build .exe hors Windows, resultat non signable ici"
  require npm
  npm run build
  npx --yes electron-builder --win nsis --publish never
}

package_apk() {
  require java
  [ -n "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ] || die "ANDROID_HOME/ANDROID_SDK_ROOT non defini"
  if [ -x ./android/gradlew ]; then
    (cd android && ./gradlew assembleRelease)
  elif has flutter; then
    flutter build apk --release
  else
    die "ni android/gradlew ni flutter trouves"
  fi
}

package_dmg() {
  [ "$(host_os)" = "macos" ] || die ".dmg necessite macOS (utiliser le job CI macos-latest)"
  require npm
  npm run build
  npx --yes electron-builder --mac dmg --publish never
}

verify() {
  [ -d "$RELEASE_DIR" ] || die "aucun dossier $RELEASE_DIR"
  ls -lh "$RELEASE_DIR"
  find "$RELEASE_DIR" -type f -print0 | while IFS= read -r -d '' f; do
    if has file; then file "$f"; fi
    if has sha256sum; then sha256sum "$f"; else shasum -a 256 "$f"; fi
    case "$f" in
      *.apk) if has aapt; then aapt dump badging "$f" | head -3 || log "apk illisible par aapt"
             elif has unzip; then unzip -l "$f" | head -5 || log "apk illisible (zip invalide)"; fi ;;
      *.dmg) if has hdiutil; then hdiutil verify "$f"; fi ;;
    esac
  done
}

case "$CMD" in
  setup)  if has npm && [ -f package.json ]; then npm ci; else log "pas de package.json npm"; fi ;;
  dev)    npm run dev ;;
  test)   npm test ;;
  lint)   npm run lint ;;
  build)  npm run build ;;
  clean)  rm -rf dist build "$RELEASE_DIR" ;;
  verify) verify ;;
  package)
    case "$TARGET" in
      exe) package_exe ;;
      apk) package_apk ;;
      dmg) package_dmg ;;
      *) die "cible inconnue: '$TARGET' (exe|apk|dmg)" ;;
    esac
    verify
    ;;
  help|*)
    echo "usage: $0 <setup|dev|test|lint|build|package|verify|clean> [exe|apk|dmg]"
    ;;
esac
