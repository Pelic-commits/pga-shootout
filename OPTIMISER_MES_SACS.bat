@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
title PGA Shootout - Optimiser mes sacs

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows_gui_launcher.ps1" %*
if errorlevel 1 (
    echo.
    echo L'optimiseur n'a pas pu demarrer. Vos donnees n'ont pas ete modifiees.
    echo Consultez logs\gui_preflight.txt pour le diagnostic.
    pause
    exit /b 1
)
exit /b 0
