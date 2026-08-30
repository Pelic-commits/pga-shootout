"""Actual Windows/Tk acceptance for the separate Landing/Wind result axes.

Runs the real asynchronous UI against a temporary backup of the user database.
Screenshots capture only this application's windows, never the whole desktop.
"""

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import tkinter as tk

from pga_shootout.strategy_optimizer_gui import StrategyOptimizerApp


def texts(widget):
    result = [str(widget.cget("text"))] if "text" in widget.keys() else []
    for child in widget.winfo_children():
        result.extend(texts(child))
    return result


def close(root):
    for callback in root.tk.call("after", "info"):
        root.after_cancel(callback)
    root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-python")
    args = parser.parse_args()
    output = Path("logs/context-variants/windows")
    output.mkdir(parents=True, exist_ok=True)
    original = Path("data/pga_shootout.sqlite")
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="pga-context-ui-") as temporary:
        database = Path(temporary) / "user.sqlite"
        with sqlite3.connect(f"file:{original.resolve().as_posix()}?mode=ro", uri=True) as source, sqlite3.connect(database) as target:
            source.backup(target)
        source.close()
        target.close()
        root = tk.Tk()
        app = StrategyOptimizerApp(root=root, user_data_path=database)
        root.report_callback_exception = lambda cls, value, tb: errors.append(f"{cls.__name__}: {value}")
        app.controller.on_error = lambda message, technical: errors.append(message + " " + technical)
        root.geometry("1480x900+20+20")
        root.lift()
        root.update()

        def capture(name, window=None):
            window = root if window is None else window
            window.update()
            if args.capture_python:
                subprocess.run([args.capture_python, "-c",
                    "from PIL import ImageGrab; import sys; ImageGrab.grab(window=int(sys.argv[1])).save(sys.argv[2])",
                    str(window.winfo_id()), str(output / (name + ".png"))], check=True)

        for strategy_id, name, wind in (
            ("par3", "High Flight", False), ("par4_long", "High Flight", True),
            ("par3", "Meteor", False), ("par3", "Flashpoint", False),
        ):
            app.strategy_name.set(next(label for label, value in app.strategy_by_label.items() if value == strategy_id))
            app.strategy_box.event_generate("<<ComboboxSelected>>")
            app.chosen_club_rows[0]["club_var"].set(name)
            app.max_evaluations.set("400")
            if wind:
                app.show_advanced.set(True)
                app._toggle_advanced()
                app.variant_name.set(next(label for label, value in app.variant_by_label.items() if value == "head_crosswind"))
            else:
                app.show_advanced.set(False)
                app._toggle_advanced()
            started = time.monotonic()
            app.analyze_button.invoke()
            assert app.controller.running, errors
            ticks = 0
            while app.controller.running and time.monotonic() - started < 360:
                root.update()
                ticks += 1
                time.sleep(0.02)
            root.update()
            assert not errors and not app.controller.running, errors
            assert app.result and app.result.retained_results
            assert app.detail_window.state() == "withdrawn"
            candidates = app.result.retained_results
            families = {family for candidate in candidates for family in candidate.result_family_ids}
            assert "power_max" in families
            assert ("wind_profile" in families) == wind
            if name in {"High Flight", "Flashpoint"} and not wind:
                assert "landing_profile" in families
            if name in {"Meteor", "Flashpoint"}:
                assert all(candidate.unresolved_abilities for candidate in candidates)
            assert len({candidate.composition for candidate in candidates}) == len(candidates)
            prefix = strategy_id + "-" + name.replace(" ", "-").lower()
            capture(prefix + "-power")
            preferred = "wind_profile" if wind else "landing_profile"
            index = next((index for index, item in enumerate(candidates) if preferred in item.result_family_ids), 0)
            card = app.cards[index]
            visible = "\n".join(texts(card))
            if preferred in families:
                assert ("Wind Resistance" if wind else "Bounce Reduction") in visible
                assert "→" in visible
            app.cards_scroll.canvas.yview_moveto(card.winfo_y() / app.cards_scroll.body.winfo_height())
            capture(prefix + "-variant")
            root.geometry("1280x800+20+20")
            root.update()
            for rendered in app.cards:
                tiles = rendered.children["clubs"].winfo_children()
                assert len(tiles) == 5
                assert tiles[-1].winfo_rootx() + tiles[-1].winfo_width() <= app.cards_scroll.canvas.winfo_rootx() + app.cards_scroll.canvas.winfo_width()
            capture(prefix + "-compact")
            root.geometry("1480x900+20+20")
            app._show_detail(index)
            root.update()
            assert app.detail_window.state() == "normal"
            app.notebook.select(app.notebook.tabs()[-1])
            capture(prefix + "-detail", app.detail_window)
            app.detail_window.withdraw()
            checks.append({"strategy": strategy_id, "club": name, "wind": wind,
                           "seconds": round(time.monotonic() - started, 2), "responsive_ticks": ticks,
                           "families": sorted(families), "cards": len(candidates), "variant_text": visible})
            print(f"Validated {strategy_id} / {name} / wind={wind}", flush=True)
            app.cards_scroll.canvas.yview_moveto(0)
        close(root)
        root = tk.Tk()
        restarted = StrategyOptimizerApp(root=root, user_data_path=database)
        root.update()
        assert restarted.result is None and restarted.detail_window.state() == "withdrawn"
        assert not restarted.show_advanced.get()
        capture("relaunch")
        close(root)
        gc.collect()
    after = hashlib.sha256(original.read_bytes()).hexdigest()
    assert before == after, "User database changed"
    report = {"runs": checks, "callback_errors": errors, "close_relaunch": "passed", "user_database_sha256": after}
    (output / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Windows validation passed; original user database unchanged.")


if __name__ == "__main__":
    main()
