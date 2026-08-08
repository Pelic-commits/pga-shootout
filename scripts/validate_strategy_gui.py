"""Visible, real-Tk acceptance run for the Windows Par 3 GUI."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import tkinter as tk

from pga_shootout.strategy_optimizer_gui import (
    StrategyOptimizerApp,
    export_result_json,
    export_result_text,
)


def _wait(app: StrategyOptimizerApp, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while app.controller.running and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.02)
    app.root.update()
    if app.controller.running:
        raise TimeoutError("Le calcul GUI n'a pas fini dans le délai imparti")
    if app.result is None:
        raise AssertionError(app.last_technical_error or "La GUI n'a produit aucun résultat")


def _club_step(candidate, club_name: str, step_id: str):
    club = next(item for item in candidate.clubs if item.club_name == club_name)
    return next(item for item in club.steps if item.step_id == step_id)


def _candidate_for_family(result, family_id: str):
    return next(item for item in result.retained_results if family_id in item.result_family_ids)


def _close_root(root: tk.Tk) -> None:
    for callback_id in root.tk.call("after", "info"):
        root.after_cancel(callback_id)
    root.destroy()


def _validate_values(app: StrategyOptimizerApp) -> dict[str, object]:
    assert app.result is not None
    result = app.result
    family_ids = {item.identifier for item in result.result_families}
    assert family_ids == {
        "iron_max_power", "iron_power_control", "iron_stability", "all_types_competitor",
    }

    maximum = _candidate_for_family(result, "iron_max_power")
    divebomb = _club_step(maximum, "Divebomb", "attack")
    ember = _club_step(maximum, "Ember", "putt")
    assert divebomb.final_stats == {"power": 16.0, "control": 9.0, "spin": 9.0}
    assert ember.final_stats["power"] == 15.0 and ember.final_stats["control"] == 17.0

    competitor = _candidate_for_family(result, "all_types_competitor")
    high_flight_candidates = [
        item for item in result.retained_results
        if "all_types_competitor" in item.result_family_ids
        and any(club.club_name == "High Flight" for club in item.clubs)
    ]
    high_flight = _club_step(high_flight_candidates[0], "High Flight", "attack")
    assert high_flight.final_stats == {"power": 19.0, "control": 10.0, "spin": 13.0}
    assert maximum.order_audit["evaluated_permutations"] == 120
    assert maximum.order_audit["complete"] is True
    assert tuple(club.club_id for club in maximum.clubs) in maximum.order_audit["best_orders"]

    # Presentation is inspected through the real widgets, not only the domain result.
    assert len(app.candidate_tree.get_children()) == len(result.retained_results)
    visible_families = " ".join(str(app.candidate_tree.item(iid, "values")[2]) for iid in app.candidate_tree.get_children())
    for family in result.result_families:
        assert family.user_name in visible_families
    assert all(
        " · ".join(club.club_name for club in candidate.clubs) in detail.title
        for candidate, detail in zip(result.retained_results, app.presentation.details, strict=True)
    )
    assert "Contributions reçues" in "\n".join(detail.synergies for detail in app.presentation.details)

    return {
        "families": sorted(family_ids),
        "divebomb": divebomb.final_stats,
        "ember_putt": ember.final_stats,
        "high_flight": high_flight.final_stats,
        "permutations": maximum.order_audit["evaluated_permutations"],
    }


def _validate_strategy(app: StrategyOptimizerApp, strategy_id: str) -> dict[str, object]:
    assert app.result is not None and app.presentation is not None
    assert app.result.strategy_id == strategy_id
    expected_steps = 2 if strategy_id in {"par3", "par4_short"} else 3
    assert app.result.retained_results
    assert all(len(item.active_assignments) == expected_steps for item in app.result.retained_results)
    first = app.presentation.details[0]
    assert len(first.steps) == expected_steps
    assert first.overview.count("Club :") == expected_steps
    assert "SUPPORTS" in first.overview and "ORDRE" in first.overview
    tabs = tuple(app.notebook.tab(tab, "text") for tab in app.notebook.tabs())
    assert tabs[0] == "Résumé"
    assert len(tabs) == expected_steps + 3
    return {
        "steps": expected_steps,
        "families": [item.identifier for item in app.result.result_families],
        "candidates": len(app.result.retained_results),
        "total_seconds": app.result.search.total_seconds,
    }


def main() -> int:
    export_dir = Path(tempfile.mkdtemp(prefix="pga-shootout-gui-validation-"))
    root = tk.Tk()
    app = StrategyOptimizerApp(root=root)
    app.root.update()
    app.strategy_name.set(next(label for label, identifier in app.strategy_by_label.items() if identifier == "par3"))
    app.real_mode.set(True)
    app.reference_name.set("Aucun")
    app.limit.set("20")
    app.max_evaluations.set("2000")
    improve_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "improve_bag")
    around_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "around_club")
    app.search_mode_name.set(improve_label)
    app._toggle_search_mode()
    assert str(app.target_bag_box.cget("state")) == "readonly"
    assert app._options().target_bag_id in app.target_bag_by_label.values()
    app.search_mode_name.set(around_label)
    app._toggle_search_mode()
    assert str(app.fixed_club_box.cget("state")) == "readonly"
    assert app._options().fixed_club_id in app.fixed_club_by_label.values()
    global_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "global")
    app.search_mode_name.set(global_label)
    app._toggle_search_mode()
    app._start()
    _wait(app)
    evidence = _validate_values(app)
    json_path = export_result_json(app.result, export_dir / "par3_sans_reference.json")
    text_path = export_result_text(app.result, export_dir / "par3_sans_reference.txt")

    reference_label = next(label for label, identifier in app.reference_by_label.items() if identifier == "par3_divebomb")
    app.reference_name.set(reference_label)
    app._start()
    _wait(app)
    assert app.result.empirical_reference is not None
    assert app.result.empirical_reference.final_power == 16.0
    evidence["reference_power"] = app.result.empirical_reference.final_power
    evidence["reference_statement"] = app.result.empirical_reference.statement
    evidence["exports"] = [str(json_path), str(text_path)]

    evidence["strategies"] = {}
    app.reference_name.set("Aucun")
    app.max_evaluations.set("600")
    app.limit.set("5")
    for strategy_id in ("par3", "par4_short", "par4_long", "par5"):
        app.strategy_name.set(next(label for label, identifier in app.strategy_by_label.items() if identifier == strategy_id))
        app._refresh_variants()
        app._start()
        _wait(app)
        evidence["strategies"][strategy_id] = _validate_strategy(app, strategy_id)
    _close_root(app.root)

    # A second real root proves normal closure and relaunch in the same launcher path.
    second_root = tk.Tk()
    second_app = StrategyOptimizerApp(root=second_root)
    second_root.update()
    _close_root(second_root)
    evidence["relaunch"] = True
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
