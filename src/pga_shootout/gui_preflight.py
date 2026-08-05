"""Read-only preflight for the Windows strategy optimizer GUI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from .strategy import StrategyRegistry
from .user_data import load_user_data


@dataclass(frozen=True)
class GuiPreflightReport:
    ok: bool
    interpreter: str
    python_version: str
    tcl_version: str | None
    tk_version: str | None
    tcl_library: str | None
    database: str
    strategy_count: int
    inventory_count: int
    owned_count: int
    message: str


def run_preflight(
    database: str | Path = "data/pga_shootout.sqlite",
    registry: str | Path = "data/strategies/strategies.json",
) -> GuiPreflightReport:
    database_path = Path(database).resolve()
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.update()
        tcl_library = root.tk.eval("info library")
        tcl_version = str(root.tk.eval("info patchlevel"))
        tk_version = str(tk.TkVersion)
        root.destroy()

        if not database_path.is_file():
            raise FileNotFoundError(f"base SQLite absente : {database_path}")
        with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as connection:
            connection.execute("PRAGMA quick_check").fetchone()
        bundle = load_user_data(database_path)
        strategy_catalog = StrategyRegistry.load(registry)
        inventory_count = len(bundle.inventory.entries)
        owned_count = sum(item.unlocked for item in bundle.inventory.entries)
        if not strategy_catalog.strategies:
            raise RuntimeError("registre de stratégies vide")
        if not inventory_count:
            raise RuntimeError("inventaire vide")
        return GuiPreflightReport(
            True, sys.executable, sys.version.split()[0], tcl_version, tk_version,
            tcl_library, str(database_path), len(strategy_catalog.strategies),
            inventory_count, owned_count, "Pré-vérification réussie.",
        )
    except Exception as error:
        return GuiPreflightReport(
            False, sys.executable, sys.version.split()[0], None, None, None,
            str(database_path), 0, 0, 0,
            f"Pré-vérification impossible : {error}. Consultez logs/gui_preflight.txt.",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_preflight()
    print(json.dumps(asdict(report), ensure_ascii=False) if args.json else report.message)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
