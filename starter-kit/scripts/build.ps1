#!/usr/bin/env pwsh
# Entree de build unifiee (PowerShell 7+, Windows/macOS/Linux).
# Usage: pwsh ./scripts/build.ps1 <setup|dev|test|lint|build|package|verify|clean> [exe|apk|dmg]
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet('setup', 'dev', 'test', 'lint', 'build', 'package', 'verify', 'clean', 'help')]
  [string]$Command = 'help',

  [Parameter(Position = 1)]
  [ValidateSet('exe', 'apk', 'dmg', '')]
  [string]$Target = ''
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$ReleaseDir = 'release'

function Write-Log([string]$Message) { Write-Host "[build] $Message" -ForegroundColor Cyan }
function Test-Tool([string]$Name) { $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }
function Get-HostOs {
  if ($IsWindows) { 'windows' } elseif ($IsMacOS) { 'macos' } elseif ($IsLinux) { 'linux' } else { 'unknown' }
}

function Invoke-Verify {
  if (-not (Test-Path $ReleaseDir)) { throw "aucun dossier $ReleaseDir" }
  Get-ChildItem -Recurse -File $ReleaseDir | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    [pscustomobject]@{ Nom = $_.Name; Octets = $_.Length; SHA256 = $hash }
  } | Format-Table -AutoSize
}

function Invoke-Package([string]$Kind) {
  switch ($Kind) {
    'exe' {
      if ((Get-HostOs) -ne 'windows') { Write-Log 'ATTENTION: build .exe hors Windows, non signable ici' }
      npm run build
      npx --yes electron-builder --win nsis --publish never
    }
    'apk' {
      if (-not (Test-Tool 'java')) { throw 'java manquant' }
      if (-not ($env:ANDROID_HOME -or $env:ANDROID_SDK_ROOT)) { throw 'ANDROID_HOME/ANDROID_SDK_ROOT non defini' }
      if (Test-Path './android') {
        Push-Location './android'
        try { if ($IsWindows) { ./gradlew.bat assembleRelease } else { ./gradlew assembleRelease } }
        finally { Pop-Location }
      }
      elseif (Test-Tool 'flutter') { flutter build apk --release }
      else { throw 'ni android/gradlew ni flutter trouves' }
    }
    'dmg' {
      if ((Get-HostOs) -ne 'macos') { throw '.dmg necessite macOS (job CI macos-latest)' }
      npm run build
      npx --yes electron-builder --mac dmg --publish never
    }
    default { throw "cible inconnue: '$Kind' (exe|apk|dmg)" }
  }
  Invoke-Verify
}

switch ($Command) {
  'setup' { npm ci }
  'dev' { npm run dev }
  'test' { npm test }
  'lint' { npm run lint }
  'build' { npm run build }
  'clean' { 'dist', 'build', $ReleaseDir | Where-Object { Test-Path $_ } | Remove-Item -Recurse -Force }
  'verify' { Invoke-Verify }
  'package' { Invoke-Package $Target }
  default { Write-Host 'usage: build.ps1 <setup|dev|test|lint|build|package|verify|clean> [exe|apk|dmg]' }
}
