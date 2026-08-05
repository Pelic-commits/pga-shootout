"""Probe a Windows Python with an actual Tk window, emitting one JSON object."""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import sys


def _prepare_tcl() -> None:
    os.environ.pop("TCL_LIBRARY", None)
    os.environ.pop("TK_LIBRARY", None)
    if sys.platform != "win32":
        return
    dlls = sorted((Path(sys.base_prefix) / "DLLs").glob("tcl*.dll"), reverse=True)
    if not dlls:
        return
    library = ctypes.WinDLL(str(dlls[0]))
    function = library.Tcl_FindExecutable
    function.argtypes = (ctypes.c_char_p,)
    function.restype = None
    function(os.fsencode(sys.executable))


def probe() -> dict[str, object]:
    result: dict[str, object] = {
        "compatible": False,
        "executable": sys.executable,
        "version": sys.version.split()[0],
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "inherited_tcl_library": os.environ.get("TCL_LIBRARY"),
        "inherited_tk_library": os.environ.get("TK_LIBRARY"),
        "venv_available": importlib.util.find_spec("venv") is not None,
        "pip_available": importlib.util.find_spec("pip") is not None,
        "ensurepip_available": importlib.util.find_spec("ensurepip") is not None,
    }
    try:
        if sys.version_info < (3, 11):
            raise RuntimeError("Python 3.11 ou plus récent est requis")
        if not result["venv_available"]:
            raise RuntimeError("module venv absent")
        if not (result["pip_available"] or result["ensurepip_available"]):
            raise RuntimeError("pip et ensurepip absents")
        _prepare_tcl()
        result["effective_tcl_library"] = os.environ.get("TCL_LIBRARY")
        result["effective_tk_library"] = os.environ.get("TK_LIBRARY")
        import tkinter as tk

        result.update(
            tkinter_file=tk.__file__,
            tcl_version=str(tk.TclVersion),
            tk_version=str(tk.TkVersion),
        )
        root = tk.Tk()
        root.withdraw()
        root.update()
        result["info_library"] = root.tk.eval("info library")
        result["tcl_patchlevel"] = root.tk.eval("info patchlevel")
        root.destroy()
        result["tk_window_ok"] = True
        result["compatible"] = True
    except Exception as error:  # diagnostic boundary
        result["tk_window_ok"] = False
        result["error"] = f"{error.__class__.__name__}: {error}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-compatible", action="store_true")
    args = parser.parse_args()
    result = probe()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["compatible"] or not args.require_compatible else 1


if __name__ == "__main__":
    raise SystemExit(main())
