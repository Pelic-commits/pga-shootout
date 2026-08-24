"""Visible, real-Tk acceptance run for the Windows Par 3 GUI."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import tkinter as tk

from pga_shootout.models import EvaluationMode
from pga_shootout.strategy_optimizer import (
    CandidateSpec, StrategyOptimizationError, StrategyOptimizationRequest, _RuntimeEvaluator,
)
from pga_shootout.strategy_optimizer_gui import (
    StrategyOptimizerApp,
    export_result_json,
    export_result_text,
)
from pga_shootout.user_data import load_user_data


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


def _direct_stats(
    app: StrategyOptimizerApp,
    composition: tuple[str, ...],
    active_assignments: dict[str, str],
    club_id: str,
) -> dict[str, float]:
    """Replay the real-inventory shot sequence directly through the Rule Engine."""
    bundle = load_user_data(app.user_data_path)
    runtime = _RuntimeEvaluator(app.catalog_path, bundle.inventory.entries, None)
    spec = CandidateSpec("gui-validation", composition, active_assignments, "gui-validation")
    pending = ()
    previous = None
    for step_id, active_club_id in active_assignments.items():
        summary = runtime.evaluate(
            spec,
            active_club_id,
            mode=EvaluationMode.PARTIAL,
            terrain=_step_terrain(step_id),
            pending_effects=pending,
            previous_club_id=previous,
        )
        if active_club_id == club_id:
            return summary.evaluation.result.final_stats.as_dict()
        pending = summary.evaluation.result.pending_effects
        previous = active_club_id
    raise AssertionError(f"Club actif absent de la séquence : {club_id}")


def _step_terrain(step_id: str) -> str | None:
    return {
        "attack": "tee",
        "drive": "tee",
        "approach": "fairway",
        "putt": "green",
    }.get(step_id)


def _stats_match(displayed: dict[str, float | None], direct: dict[str, float]) -> bool:
    expected = {
        metric: None if value is None else direct.get(metric)
        for metric, value in displayed.items()
    }
    return displayed == expected


def _close_root(root: tk.Tk) -> None:
    for callback_id in root.tk.call("after", "info"):
        root.after_cancel(callback_id)
    root.destroy()


def _clear_chosen(app: StrategyOptimizerApp) -> None:
    for row in tuple(app.chosen_club_rows):
        app._remove_chosen_club(row)


def _select_brands(app: StrategyOptimizerApp, *labels: str) -> None:
    app._clear_all_brands()
    for index in range(app.brand_list.size()):
        if app.brand_list.get(index) in labels:
            app.brand_list.selection_set(index)
    app._brand_selection_changed()


def _run_builder(app: StrategyOptimizerApp, roles: tuple[tuple[str, str], ...]) -> dict[str, object]:
    _clear_chosen(app)
    for club_id, role in roles:
        app._add_chosen_club(club_id, role)
    app._start()
    assert app.controller.running  # the real Tk window remains responsive while the worker runs
    app.root.update()
    _wait(app)
    assert app.result is not None and app.result.retained_results
    first = app.result.retained_results[0]
    active_values = {}
    for step_id, club_id in first.active_assignments.items():
        club = next(item for item in first.clubs if item.club_id == club_id)
        step = next(item for item in club.steps if item.step_id == step_id)
        active_values[step_id] = dict(step.final_stats)
        assert _stats_match(
            active_values[step_id],
            _direct_stats(app, first.composition, dict(first.active_assignments), club_id),
        )
    return {
        "badges": first.optimization_badges,
        "composition": first.composition,
        "active_assignments": dict(first.active_assignments),
        "active_values": active_values,
        "seconds": app.result.search.total_seconds,
        "optimality_status": app.result.search.optimality_status,
        "saved_candidates_injected": app.result.search.saved_bag_candidates_injected,
        "known_candidates_injected": app.result.search.known_candidates_injected,
    }


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
    assert _stats_match(
        divebomb.final_stats,
        _direct_stats(app, maximum.composition, dict(maximum.active_assignments), "divebomb"),
    )
    ember_direct = _direct_stats(app, maximum.composition, dict(maximum.active_assignments), "ember")
    assert _stats_match(ember.final_stats, ember_direct), (
        ember.final_stats, ember_direct, maximum.active_assignments, maximum.composition,
    )

    competitor = _candidate_for_family(result, "all_types_competitor")
    high_flight_candidates = [
        item for item in result.retained_results
        if "all_types_competitor" in item.result_family_ids
        and any(club.club_name == "High Flight" for club in item.clubs)
    ]
    high_flight = _club_step(high_flight_candidates[0], "High Flight", "attack")
    assert _stats_match(
        high_flight.final_stats,
        _direct_stats(
            app,
            high_flight_candidates[0].composition,
            dict(high_flight_candidates[0].active_assignments),
            "high_flight",
        ),
    )
    assert 0 < maximum.order_audit["evaluated_permutations"] <= 120
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
    assert app.all_brands.get() and app._options().allowed_brands == ()
    assert tuple(app.brand_id_by_label) == (
        "Corvid", "Forester", "Mythical", "Nautilus", "PALO",
        "Phoenix", "Ryusei", "Stanchion", "Willoughsby",
    )
    _select_brands(app, "Corvid")
    assert app._options().allowed_brands == ("corvid",)
    _select_brands(app, "Corvid", "Willoughsby")
    assert set(app._options().allowed_brands) == {"corvid", "willoughsby"}
    app._select_all_brands()
    assert app._options().allowed_brands == ()
    improve_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "improve_bag")
    around_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "around_club")
    test_new_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "test_new_club")
    app.search_mode_name.set(improve_label)
    app._toggle_search_mode()
    assert str(app.target_bag_box.cget("state")) == "readonly"
    assert app._options().target_bag_id in app.target_bag_by_label.values()
    app.search_mode_name.set(around_label)
    app._toggle_search_mode()
    assert str(app.fixed_club_box.cget("state")) == "readonly"
    assert app._options().fixed_club_id in app.fixed_club_by_label.values()
    assert {"gearshift", "wave"}.issubset(app.fixed_club_by_label.values())
    assert str(app.fixed_step_box.cget("state")) == "readonly"
    app.search_mode_name.set(test_new_label)
    app._toggle_search_mode()
    assert str(app.target_bag_box.cget("state")) == "readonly"
    assert str(app.fixed_club_box.cget("state")) == "readonly"
    assert str(app.fixed_step_box.cget("state")) == "disabled"
    replace_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "replace_club")
    app.search_mode_name.set(replace_label)
    app._toggle_search_mode()
    assert str(app.target_bag_box.cget("state")) == "readonly"
    assert str(app.fixed_club_box.cget("state")) == "readonly"
    app.target_bag_name.set(next(
        label for label, bag_id in app.target_bag_by_label.items() if bag_id == "par3_divebomb"
    ))
    assert app._options().replace_club_id in app.fixed_club_by_label.values()
    app.target_bag_name.set("Aucun")
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
    reference_stats = _direct_stats(
        app,
        ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
        {"attack": "divebomb", "putt": "ember"},
        "divebomb",
    )
    assert app.result.empirical_reference.final_power == reference_stats["power"]
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

    builder_label = next(label for label, identifier in app.search_mode_by_label.items() if identifier == "interactive_builder")
    app.search_mode_name.set(builder_label)
    app.strategy_name.set(next(label for label, identifier in app.strategy_by_label.items() if identifier == "par3"))
    app._refresh_variants()
    app._toggle_search_mode()
    app.max_evaluations.set("1000")
    evidence["interactive_builder"] = {}
    evidence["interactive_builder"]["high_flight"] = _run_builder(app, (("high_flight", "attack"),))
    app.step_minimum_vars["attack"]["control"][0].set("10")
    evidence["interactive_builder"]["high_flight_control_min"] = _run_builder(app, (("high_flight", "attack"),))
    app.step_minimum_vars["attack"]["control"][0].set("Aucun")
    app.step_minimum_vars["attack"]["spin"][0].set("7")
    evidence["interactive_builder"]["high_flight_spin_min"] = _run_builder(app, (("high_flight", "attack"),))
    app.step_minimum_vars["attack"]["spin"][0].set("Aucun")
    evidence["interactive_builder"]["high_flight_ember"] = _run_builder(
        app, (("high_flight", "attack"), ("ember", "putt")),
    )
    evidence["interactive_builder"]["high_flight_ember_maelstrom"] = _run_builder(
        app, (("high_flight", "attack"), ("ember", "putt"), ("maelstrom", "support")),
    )
    assert any(
        item.composition == ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm")
        and _stats_match(
            _club_step(item, "High Flight", "attack").final_stats,
            _direct_stats(app, item.composition, dict(item.active_assignments), "high_flight"),
        )
        for item in app.result.retained_results
    )
    par3_reference_label = next(
        label for label, bag_id in app.target_bag_by_label.items() if bag_id == "par3_divebomb"
    )
    app.target_bag_name.set(par3_reference_label)
    evidence["interactive_builder"]["divebomb"] = _run_builder(app, (("divebomb", "attack"),))
    assert app.result.comparison_reference is not None
    assert app.result.comparison_reference.bag_id == "par3_divebomb"
    assert "RÉFÉRENCE" in app.reference_summary.get()
    evidence["interactive_builder"]["divebomb_ember"] = _run_builder(
        app, (("divebomb", "attack"), ("ember", "putt")),
    )
    app.target_bag_name.set("Aucun")
    assert (
        evidence["interactive_builder"]["high_flight_ember_maelstrom"]["active_values"]["attack"]["power"]
        <= evidence["interactive_builder"]["high_flight_ember"]["active_values"]["attack"]["power"]
    )
    evidence["interactive_builder"]["gearshift"] = _run_builder(app, (("gearshift", "auto"),))
    evidence["interactive_builder"]["wave"] = _run_builder(app, (("wave", "auto"),))
    app.strategy_name.set(next(label for label, identifier in app.strategy_by_label.items() if identifier == "par5"))
    app._refresh_variants()
    evidence["interactive_builder"]["three_steps"] = _run_builder(
        app, (("high_flight", "drive"), ("divebomb", "approach"), ("ember", "putt")),
    )

    # Real tournament-constrained paths: mono-brand, multi-brand, a conflicting
    # imposed club and a nonconforming reference kept only as comparison.
    app.strategy_name.set(next(label for label, identifier in app.strategy_by_label.items() if identifier == "par3"))
    app._refresh_variants()
    app.search_mode_name.set(global_label)
    app._toggle_search_mode()
    app.max_evaluations.set("300")
    _select_brands(app, "Corvid")
    app._start()
    _wait(app)
    catalog = json.loads(app.catalog_path.read_text(encoding="utf-8"))["clubs"]
    assert all(
        catalog[club_id]["brand"]["id"] == "corvid"
        for candidate in app.result.retained_results if candidate.origin != "reference_bag"
        for club_id in candidate.composition
    )
    evidence["brands"] = {
        "single": app.result.allowed_brand_names,
        "single_candidates": len(app.result.retained_results),
    }

    _select_brands(app, "Corvid", "Ryusei", "Willoughsby", "PALO")
    app.search_mode_name.set(builder_label)
    app._toggle_search_mode()
    app.target_bag_name.set(par3_reference_label)
    constrained_reference = _run_builder(app, (("divebomb", "attack"),))
    assert set(app.result.reference_brand_violations) == {"Ember", "Sunstorm"}
    assert "hors marques autorisées" in app.presentation.warning_text
    assert all(
        candidate.origin == "reference_bag" or all(
            catalog[club_id]["brand"]["id"] in app.result.allowed_brands
            for club_id in candidate.composition
        )
        for candidate in app.result.retained_results
    )
    restricted_json = export_result_json(app.result, export_dir / "par3_marques.json")
    restricted_text = export_result_text(app.result, export_dir / "par3_marques.txt")
    evidence["brands"].update({
        "multiple": app.result.allowed_brand_names,
        "reference_violations": app.result.reference_brand_violations,
        "comparison": constrained_reference,
        "exports": [str(restricted_json), str(restricted_text)],
    })

    try:
        app.optimizer.optimize(StrategyOptimizationRequest(
            "par3", search_mode="interactive_builder", club_roles={"high_flight": "attack"},
            allowed_brands=("willoughsby",), max_evaluations=20,
        ))
    except StrategyOptimizationError as error:
        assert "High Flight ne fait pas partie des marques autorisées" in str(error)
        evidence["brands"]["forbidden_required_club"] = str(error)
    else:
        raise AssertionError("Un club imposé hors marques aurait dû être refusé")

    app._select_all_brands()
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
