@echo off
REM Desinstalle proprement Expert Dev Autopilot Console.
REM Usage: uninstall.bat [--dry-run] [--yes] [--keep-config] [--keep-logs] [--keep-venv]
setlocal
chcp 65001 >nul
pushd "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

where %PY% >nul 2>&1 || (
  echo [edac] Python introuvable : suppression manuelle des dossiers
  echo   .venv, build, dist, release
  echo   %%APPDATA%%\ExpertDevAutopilot
  echo   %%LOCALAPPDATA%%\ExpertDevAutopilot\logs
  pause & popd & endlocal & exit /b 1
)

"%PY%" -m edac uninstall %*
set "CODE=%ERRORLEVEL%"

REM Le venv ne peut pas se supprimer lui-meme s'il execute le script :
REM on repasse dessus une fois python termine.
if exist ".venv" if "%CODE%"=="0" (
  echo [edac] suppression finale de .venv
  rmdir /s /q ".venv" 2>nul
)

echo.
echo [edac] termine (code %CODE%^).
pause
popd
endlocal
exit /b %CODE%
