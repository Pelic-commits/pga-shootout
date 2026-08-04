@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
title PGA Shootout - Gerer mon inventaire

set "PYTHON_LAUNCHER="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_LAUNCHER=py -3"

if not defined PYTHON_LAUNCHER (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_LAUNCHER=python"
)

if not defined PYTHON_LAUNCHER (
    echo Python 3.11 ou une version plus recente est necessaire.
    echo Telechargez Python sur https://www.python.org/downloads/
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
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy()" >nul 2>&1
if errorlevel 1 goto :tk_error

".venv\Scripts\pythonw.exe" -m pga_shootout.inventory_editor
if errorlevel 1 goto :error
exit /b 0

:tk_error
echo.
echo L'interface graphique Tkinter n'est pas disponible dans cette installation Python.
echo Reinstallez Python depuis https://www.python.org/downloads/ avec l'option Tcl/Tk.
echo Aucune donnee n'a ete modifiee.
pause
exit /b 1

:venv_error
echo.
echo L'environnement Python existant est incompatible et n'a pas pu etre remplace.
echo Fermez les programmes Python ouverts, puis relancez ce fichier.
pause
exit /b 1

:error
echo.
echo L'editeur d'inventaire n'a pas pu demarrer.
echo Vos donnees existantes n'ont pas ete remplacees.
echo Consultez docs\FIRST_RUN.md si le probleme persiste.
pause
exit /b 1
