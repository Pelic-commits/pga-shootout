"""Windows Tcl bootstrap installed as ``sitecustomize`` in the local venv.

Some Windows launch contexts do not call Tcl_FindExecutable before tkinter
creates its first interpreter.  Paths are derived from the active Python; no
machine-specific Tcl path is stored here.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


def initialize_tcl() -> None:
    if sys.platform != "win32":
        return

    # Never inherit library paths belonging to another Python installation.
    os.environ.pop("TCL_LIBRARY", None)
    os.environ.pop("TK_LIBRARY", None)

    dll_dir = Path(sys.base_prefix) / "DLLs"
    candidates = sorted(dll_dir.glob("tcl*.dll"), reverse=True)
    if not candidates:
        return
    library = ctypes.WinDLL(str(candidates[0]))
    find_executable = library.Tcl_FindExecutable
    find_executable.argtypes = (ctypes.c_char_p,)
    find_executable.restype = None
    find_executable(os.fsencode(sys.executable))


initialize_tcl()
