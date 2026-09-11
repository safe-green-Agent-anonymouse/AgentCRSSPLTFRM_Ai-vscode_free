@echo off
REM Entree de build unifiee (cmd.exe).
REM Usage: scripts\build.cmd <setup^|dev^|test^|lint^|build^|package^|verify^|clean> [exe^|apk^|dmg]
setlocal enabledelayedexpansion
chcp 65001 >nul
pushd "%~dp0.."

set "CMD=%~1"
set "TARGET=%~2"
set "RELEASE_DIR=release"
if "%CMD%"=="" set "CMD=help"

if /i "%CMD%"=="setup"   ( call npm ci & goto :end )
if /i "%CMD%"=="dev"     ( call npm run dev & goto :end )
if /i "%CMD%"=="test"    ( call npm test & goto :end )
if /i "%CMD%"=="lint"    ( call npm run lint & goto :end )
if /i "%CMD%"=="build"   ( call npm run build & goto :end )
if /i "%CMD%"=="clean"   ( rmdir /s /q dist 2>nul & rmdir /s /q build 2>nul & rmdir /s /q "%RELEASE_DIR%" 2>nul & goto :end )
if /i "%CMD%"=="verify"  ( call :verify & goto :end )
if /i "%CMD%"=="package" ( call :package & goto :end )

echo usage: %~nx0 ^<setup^|dev^|test^|lint^|build^|package^|verify^|clean^> [exe^|apk^|dmg]
goto :end

:package
if /i "%TARGET%"=="exe" (
  call npm run build || goto :fail
  call npx --yes electron-builder --win nsis --publish never || goto :fail
) else if /i "%TARGET%"=="apk" (
  if "%ANDROID_HOME%"=="" if "%ANDROID_SDK_ROOT%"=="" ( echo [build] ANDROID_HOME non defini & goto :fail )
  if exist android\gradlew.bat (
    pushd android & call gradlew.bat assembleRelease & popd
  ) else (
    where flutter >nul 2>&1 && call flutter build apk --release || ( echo [build] ni gradlew ni flutter & goto :fail )
  )
) else if /i "%TARGET%"=="dmg" (
  echo [build] .dmg necessite macOS - utiliser le job CI macos-latest
  goto :fail
) else (
  echo [build] cible inconnue: "%TARGET%" ^(exe^|apk^|dmg^)
  goto :fail
)
call :verify
exit /b 0

:verify
if not exist "%RELEASE_DIR%" ( echo [build] aucun dossier %RELEASE_DIR% & exit /b 1 )
dir /b /s "%RELEASE_DIR%"
for /r "%RELEASE_DIR%" %%F in (*) do (
  echo --- %%~nxF ^(%%~zF octets^)
  certutil -hashfile "%%F" SHA256 | findstr /v ":"
)
exit /b 0

:fail
echo [build] echec
popd
endlocal
exit /b 1

:end
popd
endlocal
