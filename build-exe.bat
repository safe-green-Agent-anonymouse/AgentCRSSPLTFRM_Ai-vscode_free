@echo off
REM Construit l'executable Windows fenetre dist\EDAC-Console.exe via PyInstaller,
REM puis affiche taille et empreinte SHA-256 de l'artefact.
setlocal
chcp 65001 >nul
pushd "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

"%PY%" -c "import PyInstaller" 2>nul || (
  echo [edac] installation de PyInstaller...
  "%PY%" -m pip install pyinstaller || goto :fail
)

echo [edac] nettoyage...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [edac] construction de l'executable...
"%PY%" -m PyInstaller --noconfirm --clean edac.spec || goto :fail

if not exist "dist\EDAC-Console.exe" (
  echo [edac] artefact introuvable apres le build.
  goto :fail
)

echo.
echo [edac] artefact produit :
for %%F in ("dist\EDAC-Console.exe") do echo   %%~fF  (%%~zF octets^)
certutil -hashfile "dist\EDAC-Console.exe" SHA256 | findstr /v ":"
echo.
echo [edac] signature optionnelle :
echo   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f cert.pfx dist\EDAC-Console.exe
echo.
pause
popd & endlocal & exit /b 0

:fail
echo [edac] echec du build.
pause
popd & endlocal & exit /b 1
