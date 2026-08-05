param([switch]$Validate)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot
$logDirectory = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDirectory "gui_preflight.txt"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Write-Diagnostic([string]$message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value "[$timestamp] $message"
}

function Fail-Friendly([string]$message) {
    Write-Host ""
    Write-Host $message
    Write-Host "Interpréteur détecté : $script:selectedPython"
    Write-Host "Détails techniques : $logPath"
    Write-Diagnostic "ECHEC: $message"
    exit 1
}

function Test-Python([string]$python) {
    try {
        $output = & $python (Join-Path $projectRoot "scripts\windows_python_probe.py") --require-compatible 2>&1
        $exitCode = $LASTEXITCODE
        Write-Diagnostic "Probe $python : $output"
        return $exitCode -eq 0
    } catch {
        Write-Diagnostic "Probe $python : $($_.Exception.Message)"
        return $false
    }
}

$inheritedTclLibrary = $env:TCL_LIBRARY
$inheritedTkLibrary = $env:TK_LIBRARY
Remove-Item Env:TCL_LIBRARY -ErrorAction SilentlyContinue
Remove-Item Env:TK_LIBRARY -ErrorAction SilentlyContinue
Set-Content -LiteralPath $logPath -Encoding UTF8 -Value "Diagnostic du lanceur PGA Shootout"
Write-Diagnostic "Projet : $projectRoot"
Write-Diagnostic "TCL_LIBRARY hérité : $inheritedTclLibrary"
Write-Diagnostic "TK_LIBRARY hérité : $inheritedTkLibrary"
Write-Diagnostic "Variables Tcl/Tk effectives : neutralisées"

$venvRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot ".venv"))
$expectedVenv = [System.IO.Path]::GetFullPath((Join-Path $projectRoot ".venv"))
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$candidates = [System.Collections.Generic.List[string]]::new()

$localPythonRoot = Join-Path $env:LocalAppData "Programs\Python"
if (Test-Path -LiteralPath $localPythonRoot) {
    Get-ChildItem -LiteralPath $localPythonRoot -Directory -Filter "Python*" |
        Sort-Object Name -Descending |
        ForEach-Object {
            $candidate = Join-Path $_.FullName "python.exe"
            if (Test-Path -LiteralPath $candidate) { $candidates.Add($candidate) }
        }
}
$launcher = Join-Path $localPythonRoot "Launcher\py.exe"
if (Test-Path -LiteralPath $launcher) {
    Write-Diagnostic "Lanceur Windows : $(& $launcher -0p 2>&1)"
}
Get-Command python.exe -All -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Source -and $_.Source -notlike "*WindowsApps*" -and -not $candidates.Contains($_.Source)) {
        $candidates.Add($_.Source)
    }
}

$script:selectedPython = "aucun"
$selectedPython = $null
foreach ($candidate in $candidates) {
    if (Test-Python $candidate) {
        $selectedPython = $candidate
        $script:selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    Fail-Friendly "Aucun Python 3.11+ avec une fenêtre Tk, pip et venv fonctionnels n'a été trouvé. Réinstallez Python depuis python.org avec Tcl/Tk."
}

$recreate = -not (Test-Path -LiteralPath $venvPython)
if (-not $recreate) {
    $cfg = Join-Path $venvRoot "pyvenv.cfg"
    if (Test-Path -LiteralPath $cfg) { Write-Diagnostic "Ancien pyvenv.cfg : $((Get-Content -Raw $cfg).Trim())" }
    $base = & $venvPython -c "import sys; print(sys.base_prefix)" 2>$null
    $recreate = ($LASTEXITCODE -ne 0) -or ([System.IO.Path]::GetFullPath($base.Trim()) -ne [System.IO.Path]::GetFullPath((Split-Path $selectedPython)))
}

if ($recreate) {
    if ($venvRoot -ne $expectedVenv -or (Split-Path $venvRoot -Leaf) -ne ".venv") {
        Fail-Friendly "Le chemin de l'environnement local n'est pas sûr."
    }
    if (Test-Path -LiteralPath $venvRoot) {
        Write-Diagnostic "Suppression du seul environnement recréable : $venvRoot"
        Remove-Item -LiteralPath $venvRoot -Recurse -Force
    }
    Write-Host "Préparation de l'environnement Python validé..."
    & $selectedPython -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { Fail-Friendly "L'environnement Python n'a pas pu être créé." }
}

$sitePackages = & $venvPython -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
if ($LASTEXITCODE -ne 0) { Fail-Friendly "L'environnement Python est incomplet." }
Copy-Item -LiteralPath (Join-Path $projectRoot "scripts\pga_tk_sitecustomize.py") -Destination (Join-Path $sitePackages.Trim() "sitecustomize.py") -Force

& $venvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) { & $venvPython -m ensurepip --upgrade | Out-Null }
& $venvPython -c "import pathlib, pga_shootout; raise SystemExit(0 if pathlib.Path(pga_shootout.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve()) else 1)" *> $null
if ($LASTEXITCODE -ne 0) {
    & $venvPython -m pip install -e $projectRoot | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail-Friendly "L'installation locale de PGA Shootout n'a pas pu se terminer." }
}

$preflight = & $venvPython -m pga_shootout.gui_preflight --json 2>&1
Write-Diagnostic "Pré-vérification : $preflight"
if ($LASTEXITCODE -ne 0) { Fail-Friendly "Tkinter, la base SQLite, le registre de stratégies ou l'inventaire n'est pas utilisable." }
Write-Host "Pré-vérification réussie. Ouverture de l'optimiseur..."

if ($Validate) {
    & $venvPython (Join-Path $projectRoot "scripts\validate_strategy_gui.py")
    exit $LASTEXITCODE
}

$pythonw = Join-Path $venvRoot "Scripts\pythonw.exe"
Start-Process -FilePath $pythonw -ArgumentList "-m", "pga_shootout.strategy_optimizer_gui" -WorkingDirectory $projectRoot
exit 0
