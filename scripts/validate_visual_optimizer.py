"""Real Windows/Tk acceptance: both workflows, cards, details, close/relaunch.

Uses a temporary SQLite backup, never edits the player's inventory.
Pass --capture-python with a Pillow-enabled interpreter to capture the window.
"""

import argparse
import gc
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import tkinter as tk

from pga_shootout.strategy_optimizer_gui import StrategyOptimizerApp
from pga_shootout.optimizer_cards import club_projection


def close(root):
    for callback in root.tk.call("after", "info"):
        root.after_cancel(callback)
    root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-python")
    args = parser.parse_args()
    output = Path("logs/visual-ux")
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix="pga-visual-") as temporary:
        database = Path(temporary) / "profile.sqlite"
        with sqlite3.connect("data/pga_shootout.sqlite") as source, sqlite3.connect(database) as target:
            source.backup(target)
        source.close()
        target.close()
        root = tk.Tk()
        app = StrategyOptimizerApp(root=root, user_data_path=database)
        errors = []
        root.report_callback_exception = lambda cls, value, tb: errors.append(f"{cls.__name__}: {value}")
        app._on_error = lambda message, technical: errors.append(message + " " + technical)
        app.controller.on_error = app._on_error
        root.geometry("1480x900+20+20")
        root.lift()
        root.update()

        def capture(name, window=root):
            window.update()
            if args.capture_python:
                subprocess.run([args.capture_python, "-c", "from PIL import ImageGrab; import sys; ImageGrab.grab(window=int(sys.argv[1])).save(sys.argv[2])", str(window.winfo_id()), str(output / f"{name}.png")], check=True)

        assert not app.advanced_frame.winfo_ismapped()
        assert app.detail_window.state() == "withdrawn"
        assert app.tools_window.state() == "withdrawn"
        capture("01-start")
        for strategy_id in ("par3", "par4_long"):
            label = next(name for name, value in app.strategy_by_label.items() if value == strategy_id)
            app.strategy_name.set(label)
            app.strategy_box.event_generate("<<ComboboxSelected>>")
            app.chosen_club_rows[0]["club_var"].set("Blacksmith")
            if strategy_id == "par4_long":
                app.add_club_button.invoke()
                app.chosen_club_rows[1]["club_var"].set("Jumpstart")
            options = app._options()
            assert options.search_mode == "build_from_scratch"
            assert options.target_bag_id is None and options.reference_bag_id is None
            started = time.monotonic()
            app.analyze_button.invoke()
            assert app.controller.running, errors
            responsive_ticks = 0
            while app.controller.running and time.monotonic() - started < 300:
                root.update()
                responsive_ticks += 1
                time.sleep(0.02)
            root.update()
            assert not errors, errors
            assert not app.controller.running, "Timeout"
            assert app.result and app.result.retained_results
            assert len(app.cards) == len(app.result.retained_results)
            assert app.detail_window.state() == "withdrawn"
            for candidate in app.result.retained_results:
                assert len(candidate.clubs) == 5
                assert "blacksmith" in candidate.composition
                for club in candidate.clubs:
                    projected = club_projection(club, candidate, {})
                    assert tuple(projected["stats"]) == ("power", "control", "spin")
            capture(strategy_id)
            # Inspect a second proposal and the supported compact window size.
            root.geometry("1280x800+20+20")
            root.update()
            for card in app.cards:
                tiles = card.children["clubs"].winfo_children()
                assert tiles[-1].winfo_rootx() + tiles[-1].winfo_width() <= app.cards_scroll.canvas.winfo_rootx() + app.cards_scroll.canvas.winfo_width(), "Last club clipped horizontally"
            capture(strategy_id + "-compact")
            root.geometry("1480x900+20+20")
            root.update()
            if len(app.cards) > 1:
                height = app.cards_scroll.body.winfo_height()
                app.cards_scroll.canvas.yview_moveto(app.cards[1].winfo_y() / height)
                capture(strategy_id + "-alternative")
                app.cards_scroll.canvas.yview_moveto(0)
            checks.append({"strategy": strategy_id, "seconds": round(time.monotonic() - started, 2),
                           "engine_seconds": app.result.search.total_seconds,
                           "cards": len(app.cards), "responsive_ticks": responsive_ticks,
                           "composition": app.result.retained_results[0].composition,
                           "final_stats": {club.club_name: club_projection(club, app.result.retained_results[0], {})["stats"] for club in app.result.retained_results[0].clubs}})
            app._show_detail(0)
            root.update()
            assert app.detail_window.state() == "normal"
            assert len(app.notebook.tabs()) >= 5
            app.notebook.select(app.notebook.tabs()[-1])
            capture(strategy_id + "-detail", app.detail_window)
            app.detail_window.withdraw()
        app.show_advanced.set(True)
        app._toggle_advanced()
        root.update()
        assert app.advanced_frame.winfo_ismapped()
        app.show_advanced.set(False)
        app._toggle_advanced()
        close(root)
        root = tk.Tk()
        restarted = StrategyOptimizerApp(root=root, user_data_path=database)
        root.update()
        assert restarted.result is None
        assert not restarted.show_advanced.get()
        assert restarted.detail_window.state() == "withdrawn"
        close(root)
        gc.collect()
    report = {"runs": checks, "close_relaunch": "passed", "callback_errors": errors}
    (output / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
