@echo off
REM Prepare l'environnement local (venv + outils de build).
setlocal
chcp 65001 >nul
pushd "%~dp0"

where python >nul 2>&1 || (
  echo [edac] Python 3.10+ requis. Telechargez-le sur https://python.org/downloads
  pause & popd & endlocal & exit /b 1
)

echo [edac] verification de la version de Python...
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" || (
  echo [edac] Python 3.10 minimum requis.
  pause & popd & endlocal & exit /b 1
)

echo [edac] verification de tkinter...
python -c "import tkinter" 2>nul || (
  echo [edac] tkinter manquant : reinstallez Python en cochant "tcl/tk and IDLE".
  pause & popd & endlocal & exit /b 1
)

if not exist ".venv" (
  echo [edac] creation de l'environnement virtuel...
  python -m venv .venv || goto :fail
)

echo [edac] mise a jour de pip et installation des outils de build...
call .venv\Scripts\python.exe -m pip install --upgrade pip >nul || goto :fail
call .venv\Scripts\python.exe -m pip install pyinstaller || goto :fail

echo.
echo [edac] pret.
echo   run.bat           ouvrir la fenetre
echo   build-exe.bat     construire dist\EDAC-Console.exe
echo   run.bat config list   afficher la configuration
echo.
pause
popd & endlocal & exit /b 0

:fail
echo [edac] echec de l'installation.
pause
popd & endlocal & exit /b 1
