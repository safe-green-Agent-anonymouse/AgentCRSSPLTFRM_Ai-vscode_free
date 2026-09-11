# Signature Authenticode d'un binaire Windows.
#
# Le certificat n'est jamais stocke dans le depot : il provient des secrets
# GitHub WINDOWS_CERT_PFX_BASE64 et WINDOWS_CERT_PASSWORD, est ecrit dans un
# fichier temporaire puis efface, y compris en cas d'erreur.
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string[]]$Path,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not $env:WINDOWS_CERT_PFX_BASE64 -or -not $env:WINDOWS_CERT_PASSWORD) {
  throw "secrets WINDOWS_CERT_PFX_BASE64 / WINDOWS_CERT_PASSWORD absents"
}

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match '\\x64\\' } |
  Sort-Object FullName -Descending |
  Select-Object -First 1
if (-not $signtool) { throw "signtool.exe introuvable (Windows SDK)" }

$pfx = Join-Path ([System.IO.Path]::GetTempPath()) ("edac-" + [guid]::NewGuid().ToString("N") + ".pfx")
try {
  [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64))
  foreach ($file in $Path) {
    if (-not (Test-Path $file)) { throw "fichier a signer introuvable : $file" }
    & $signtool.FullName sign /fd SHA256 /td SHA256 /tr $TimestampUrl `
      /f $pfx /p $env:WINDOWS_CERT_PASSWORD $file
    if ($LASTEXITCODE -ne 0) { throw "echec de la signature de $file" }
    & $signtool.FullName verify /pa /v $file
    if ($LASTEXITCODE -ne 0) { throw "signature invalide pour $file" }
  }
}
finally {
  if (Test-Path $pfx) { Remove-Item $pfx -Force }
}
