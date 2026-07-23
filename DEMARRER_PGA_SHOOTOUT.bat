@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
title PGA Shootout Assistant

set "PYTHON_LAUNCHER="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_LAUNCHER=py -3"

if not defined PYTHON_LAUNCHER (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_LAUNCHER=python"
)

if not defined PYTHON_LAUNCHER (
    echo.
    echo Python 3.11 ou une version plus recente est necessaire.
    echo Telechargez Python sur https://www.python.org/downloads/
    echo Pendant l'installation, cochez "Add Python to PATH".
    echo Relancez ensuite ce fichier.
    echo.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if errorlevel 1 (
        if exist ".venv_incompatible" goto :venv_error
        echo L'ancien environnement Python est conserve dans .venv_incompatible.
        move ".venv" ".venv_incompatible" >nul
        if errorlevel 1 goto :venv_error
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Preparation de l'environnement Python...
    %PYTHON_LAUNCHER% -m venv .venv
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import pathlib, pga_shootout; raise SystemExit(0 if pathlib.Path(pga_shootout.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve()) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Installation locale de PGA Shootout...
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 goto :install_error
)

echo.
".venv\Scripts\python.exe" -m pga_shootout.cli assistant
if errorlevel 1 goto :error
echo.
echo L'application s'est fermee normalement.
pause
exit /b 0

:install_error
echo.
echo L'installation n'a pas pu se terminer.
echo Verifiez votre connexion Internet, puis relancez ce fichier.
pause
exit /b 1

:venv_error
echo.
echo L'environnement .venv utilise une ancienne version de Python et n'a pas pu etre remplace.
echo Fermez les programmes Python ouverts, renommez .venv_incompatible si ce dossier existe, puis relancez.
pause
exit /b 1

:error
echo.
echo Une erreur a interrompu PGA Shootout.
echo Aucune donnee ne devrait avoir ete perdue : une sauvegarde est creee avant chaque modification.
echo Consultez docs\FIRST_RUN.md si le probleme persiste.
pause
exit /b 1
