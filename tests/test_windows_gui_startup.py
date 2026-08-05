from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pga_shootout.gui_preflight import run_preflight


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "win32", reason="validation Windows uniquement")
def test_active_venv_creates_and_destroys_a_real_tk_window():
    completed = subprocess.run(
        [sys.executable, "-c", "import tkinter as tk; r=tk.Tk(); r.withdraw(); r.update(); print(r.tk.eval('info library')); r.destroy()"],
        cwd=ROOT, text=True, capture_output=True, timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "tcl" in completed.stdout.casefold()


@pytest.mark.skipif(sys.platform != "win32", reason="validation Windows uniquement")
def test_probe_neutralizes_incoherent_tcl_environment_and_requires_real_window():
    environment = os.environ.copy()
    environment["TCL_LIBRARY"] = r"Z:\ancien-python\tcl8.6"
    environment["TK_LIBRARY"] = r"Z:\ancien-python\tk8.6"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "windows_python_probe.py"), "--require-compatible"],
        cwd=ROOT, env=environment, text=True, capture_output=True, timeout=20,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, payload.get("error")
    # sitecustomize runs before this script and must already have neutralized them.
    assert payload["inherited_tcl_library"] is None
    assert payload["inherited_tk_library"] is None
    assert payload["effective_tcl_library"] is None
    assert payload["effective_tk_library"] is None
    assert payload["tk_window_ok"] is True


@pytest.mark.skipif(sys.platform != "win32", reason="validation Windows uniquement")
def test_probe_rejects_importable_tkinter_when_real_window_creation_fails(tmp_path):
    (tmp_path / "tkinter.py").write_text(
        "TclVersion = TkVersion = 8.6\n"
        "class Tk:\n"
        "    def __init__(self):\n"
        "        raise RuntimeError('fenêtre indisponible')\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "windows_python_probe.py"), "--require-compatible"],
        cwd=ROOT, env=environment, text=True, capture_output=True, timeout=20,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["tk_window_ok"] is False
    assert "fenêtre indisponible" in payload["error"]


def test_launcher_deletes_only_the_exact_recreatable_venv_and_preserves_user_data():
    script = (ROOT / "scripts" / "windows_gui_launcher.ps1").read_text(encoding="utf-8")
    remove_lines = [line.strip() for line in script.splitlines() if "Remove-Item" in line]
    assert "Remove-Item -LiteralPath $venvRoot -Recurse -Force" in remove_lines
    assert all("sqlite" not in line.casefold() and "data" not in line.casefold() for line in remove_lines)
    assert '(Split-Path $venvRoot -Leaf) -ne ".venv"' in script
    batch = (ROOT / "OPTIMISER_MES_SACS.bat").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in batch
    assert '-File "%~dp0scripts\\windows_gui_launcher.ps1"' in batch


@pytest.mark.skipif(sys.platform != "win32", reason="validation Windows uniquement")
def test_read_only_preflight_validates_tk_sqlite_registry_and_inventory():
    database = ROOT / "data" / "pga_shootout.sqlite"
    before = database.read_bytes()
    report = run_preflight()
    after = database.read_bytes()
    assert report.ok, report.message
    assert report.strategy_count >= 4
    assert report.inventory_count >= report.owned_count > 0
    assert report.tcl_library
    assert before == after
