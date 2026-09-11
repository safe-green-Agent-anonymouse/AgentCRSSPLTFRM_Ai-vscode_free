@echo off
REM Lance la fenetre Expert Dev Autopilot Console.
REM Usage: run.bat            -> fenetre
REM        run.bat run build  -> passe les arguments a la CLI
setlocal
chcp 65001 >nul
pushd "%~dp0"

set "PY="
if exist ".venv\Scripts\pythonw.exe" set "PY=.venv\Scripts\pythonw.exe"
if not defined PY (
  where pythonw >nul 2>&1 && set "PY=pythonw"
)
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [edac] Python introuvable. Installez Python 3.10+ depuis https://python.org
  echo [edac] puis relancez setup.bat.
  pause
  popd & endlocal & exit /b 1
)

REM Avec des arguments, on veut la sortie console : on force python.exe
if not "%~1"=="" (
  set "PY=%PY:pythonw=python%"
)

"%PY%" -m edac %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" if "%~1"=="" pause
popd
endlocal
exit /b %CODE%
