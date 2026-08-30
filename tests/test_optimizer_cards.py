"""UI contract: factual projections, offline assets and real Tk orchestration."""

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pga_shootout.optimizer_cards import (
    ASSETS, GraphicAssets, club_projection, display_step, metric_changes, number, step_labels_for,
    secondary_summary, secondary_cautions,
)
from pga_shootout.strategy_optimizer import ClubStepResult, ContributionRecord, OptimizedClubResult
from pga_shootout.strategy_optimizer_gui import StrategyOptimizerApp


def shot(identifier, *, power=12, unresolved=()):
    return ClubStepResult(identifier, {}, {"power": 3, "control": 2, "spin": 1},
                          {"power": power, "control": 5, "spin": None}, {}, {}, {}, (), (), unresolved, (), ())


def club(*, active=("putt",), steps=None):
    return OptimizedClubResult(1, "sample", "Sample", "putter", 8, "active", active, (),
                               steps if steps is not None else (shot("attack", power=10), shot("putt", power=14)))


def candidate(item):
    return SimpleNamespace(clubs=(item,), active_assignments={"attack": "sample", "putt": "sample"})


def test_active_stats_are_final_and_shot_specific():
    item = club()
    data = club_projection(item, candidate(item), {"putt": "Putt"})
    assert data["stats"] == {"power": "14", "control": "5", "spin": "—"}
    assert data["step"] == "Putt"
    assert display_step(item).base_stats["power"] == 3


def test_support_stats_explicitly_use_first_evaluated_shot():
    item = replace(club(active=()), role="support")
    data = club_projection(item, candidate(item), {"attack": "Attaque"})
    assert data["stats"]["power"] == "10"
    assert data["step"] == "Attaque"


@pytest.mark.parametrize("value,expected", [(None, "—"), (0, "0"), (2.5, "2.5"), (-3, "-3")])
def test_no_invented_value_or_rounding(value, expected):
    assert number(value) == expected


def test_missing_evaluation_never_falls_back_to_base_stats():
    item = club(steps=())
    data = club_projection(item, candidate(item), {})
    assert set(data["stats"].values()) == {"—"}
    assert data["step"] == "Non évalué"


def test_contribution_target_units_and_unknowns_are_kept():
    effect = ContributionRecord("sample", "sample", "ability-1", "add_stat", {"wind_resistance_percent": 25})
    step = replace(shot("putt", unresolved=("ambiguous",)), contributions_sent=(effect,))
    item = club(steps=(step,))
    data = club_projection(item, candidate(item), {"putt": "Putt"})
    assert data["reasons"] == ("+25 % Wind Resistance → Sample · Putt",)
    assert data["unresolved"] == ("ambiguous",)


def test_metric_deltas_preserve_positive_negative_and_missing():
    item = SimpleNamespace(metric_deltas_from_power_max={"attack.power": -1, "attack.control": 2, "putt.spin": None, "putt.control": 0})
    assert metric_changes(item, {"attack": "Attaque"}) == ("-1 Power · Attaque", "+2 Control · Attaque")


def test_all_official_clubs_have_packaged_icons_and_brand_accents():
    catalog = json.loads(Path("data/normalized/clubs_official.json").read_text(encoding="utf-8"))
    assets = GraphicAssets(None, catalog)
    assert len(list((ASSETS / "club_icons").glob("*.png"))) == 88
    for identifier in catalog["clubs"]:
        assert (ASSETS / "club_icons" / f"{identifier}.png").is_file()
        assert assets.color(identifier).startswith("#")
    assert len(assets.colors) == 9


def test_missing_or_invalid_palette_has_neutral_fallback(tmp_path):
    assets = GraphicAssets(None, {"clubs": {}}, tmp_path)
    assert assets.color("not_in_catalog") == "#526862"
    assets.colors["invalid"] = "#xxxxxx"
    assets.brands["sample"] = "invalid"
    assert assets.color("sample") == "#526862"


@pytest.fixture
def app():
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display unavailable: {error}")
    root.withdraw()
    application = StrategyOptimizerApp(root=root)
    yield application
    for callback in root.tk.call("after", "info"):
        root.after_cancel(callback)
    root.destroy()


def test_primary_workflow_has_no_legacy_or_advanced_controls(app):
    assert app.search_mode_name.get() == "Construire mon sac"
    assert not app.show_advanced.get()
    assert not app.advanced_frame.winfo_manager()
    assert app.tools_window.state() == "withdrawn"
    assert app.detail_window.state() == "withdrawn"
    assert not app.brand_list.winfo_manager()


def test_club_choice_required_no_silent_default(app):
    assert app.chosen_club_rows[0]["club_var"].get() == ""
    with pytest.raises(ValueError, match="Choisissez un club"):
        app._options()


def test_add_remove_and_duplicate_validation(app):
    app.chosen_club_rows[0]["club_var"].set("Blacksmith")
    app.add_club_button.invoke()
    app.chosen_club_rows[1]["club_var"].set("Blacksmith")
    with pytest.raises(ValueError, match="plusieurs fois"):
        app._options()
    app._remove_chosen_club(app.chosen_club_rows[1])
    assert app._options().club_roles == {"blacksmith": "auto"}
    assert app._options().scenario_level is None


def test_legacy_reference_never_leaks_into_build_from_scratch(app):
    app.chosen_club_rows[0]["club_var"].set("Blacksmith")
    app.target_bag_name.set(next(label for label in app.target_bag_by_label if label != "Aucun"))
    app.reference_name.set(next(label for label in app.reference_by_label if label != "Aucun"))
    options = app._options()
    assert options.target_bag_id is None
    assert options.reference_bag_id is None


def test_advanced_and_brand_filters_toggle_without_reset(app):
    app.show_advanced.set(True)
    app._toggle_advanced()
    assert app.advanced_frame.winfo_manager() == "grid"
    app.chosen_club_rows[0]["position_var"].set("2")
    app.show_advanced.set(False)
    app._toggle_advanced()
    assert app.chosen_club_rows[0]["position_var"].get() == "2"
    app._clear_all_brands()
    assert app.brand_list.winfo_manager() == "pack"
    app.brand_list.selection_set(0)
    app.chosen_club_rows[0]["club_var"].set("Blacksmith")
    assert len(app._options().allowed_brands) == 1
    app._select_all_brands()
    assert app._options().allowed_brands == ()


def test_missing_image_is_cached_fallback(app):
    for identifier in app.assets.brands:
        assert app.assets.photo(identifier) is not None
    assert app.assets.photo("missing_asset") is None
    assert "missing_asset" in app.assets.photos
    assert app.assets.photo("../outside") is None


def test_short_step_labels_follow_functions_not_strategy_names(app):
    strategy = app.presenter.registry.get("par3")
    assert step_labels_for(strategy) == {"attack": "Attaque du green", "putt": "Putt"}
    assert step_labels_for(app.presenter.registry.get("par4_long")) == {"drive": "Départ", "approach": "Approche", "putt": "Putt"}


@pytest.fixture(scope="module")
def result():
    from pga_shootout.strategy_optimizer import StrategyOptimizer, StrategyOptimizationRequest
    return StrategyOptimizer().optimize(StrategyOptimizationRequest(
        "par3", search_mode="build_from_scratch", club_roles={"blacksmith": "auto"},
        primary_step_id="attack", limit=5, max_evaluations=20,
    ))


def widget_texts(widget):
    texts = []
    if "text" in widget.keys():
        texts.append(str(widget.cget("text")))
    for child in widget.winfo_children():
        texts.extend(widget_texts(child))
    return texts


def test_result_renders_five_ordered_clubs_without_opening_details(app, result):
    app._on_success(result, 1.0)
    assert len(app.cards) == len(result.retained_results) > 0
    assert app.detail_window.state() == "withdrawn"
    for card, retained in zip(app.cards, result.retained_results):
        tiles = card.children["clubs"].winfo_children()
        assert len(tiles) == 5
        for tile, expected in zip(tiles, retained.clubs):
            assert expected.club_name in widget_texts(tile)
            projection = club_projection(expected, retained, {})
            assert all(value in widget_texts(tile) for value in projection["stats"].values())


def test_details_reuse_presenter_and_are_reset_between_searches(app, result):
    app._on_success(result, 1)
    app._show_detail(0)
    assert app._selected_candidate() == result.retained_results[0]
    assert app.detail_window.state() == "normal"
    final_tab = app.notebook.nametowidget(app.notebook.tabs()[-1])
    text = next(child for child in final_tab.winfo_children() if child.winfo_class() == "Text")
    assert text.get("1.0", "end-1c") == app.presentation.details[0].technical_details
    app._show_detail(0)
    assert len(app.notebook.winfo_children()) == len(app.notebook.tabs())
    app._on_success(result, 1)
    assert app.detail_window.state() == "withdrawn"
    assert app._selected_index() is None


def test_empty_results_explain_how_to_relax_constraints(app, result):
    empty = replace(result, retained_results=())
    app._on_success(empty, 1)
    assert app.cards == []
    assert any("Aucun sac retenu" in text for text in widget_texts(app.cards_scroll.body))


def test_partial_result_is_visible_without_explain(app, result):
    first = replace(result.retained_results[0], unresolved_abilities=("unknown-capacity",))
    app._on_success(replace(result, retained_results=(first,)), 1)
    assert any("Partiellement évalué" in text for text in widget_texts(app.cards[0]))
    assert "1 sac(s) partiel(s)" in app.warning_summary.get()


def test_unsatisfied_minimums_are_not_hidden_behind_details(app, result):
    app._on_success(replace(result, criteria_satisfied=False), 1)
    assert "Minimums non satisfaits" in app.warning_summary.get()


def test_projection_golden_contains_only_existing_facts():
    item = club()
    assert club_projection(item, candidate(item), {"putt": "Putt"}) == {
        "id": "sample", "name": "Sample", "type": "putter", "level": "8", "position": 1,
        "role": "Actif", "step": "Putt", "stats": {"power": "14", "control": "5", "spin": "—"},
        "reasons": (), "unresolved": (),
    }


def test_secondary_axes_remain_hidden_without_relevance_and_cumul_is_warned():
    contributions = tuple(ContributionRecord(source, "sample", source + "__wind", "dsl_pipeline",
                                             {"wind_resistance_percent": 20}) for source in ("a", "b"))
    step = replace(shot("attack"), additional_metrics={"wind_resistance_percent": 40},
                   metric_relevance={"wind_resistance_percent": "descriptive"}, contributions_received=contributions)
    assert secondary_summary(step, complete=True) == ()
    assert secondary_cautions(step) == ()
    active = replace(step, metric_relevance={"wind_resistance_percent": "objective"})
    assert secondary_summary(active, complete=True) == ("Wind Resistance 40 %",)
    assert secondary_cautions(active) == ("Wind Resistance : plusieurs sources additionnées ; cumul en jeu à valider.",)


def test_cards_show_secondary_axes_without_opening_technical_details(app, result):
    first = result.retained_results[0]
    active_id = first.active_assignments["attack"]
    clubs = tuple(replace(club, steps=tuple(replace(step,
        additional_metrics={"bounce_reduction_percent": 30, "wind_resistance_percent": 25},
        metric_relevance={"bounce_reduction_percent": "objective", "wind_resistance_percent": "objective"},
    ) if step.step_id == "attack" else step for step in club.steps)) if club.club_id == active_id else club for club in first.clubs)
    first = replace(first, clubs=clubs, result_family_ids=("power_max", "landing_profile", "wind_profile"),
                    optimization_badges=("MEILLEURE PUISSANCE TROUVÉE", "MEILLEUR ATTERRISSAGE", "STABILITÉ AU VENT"))
    app._on_success(replace(result, retained_results=(first,)), 1)
    assert len(app.cards) == 1
    texts = "\n".join(widget_texts(app.cards[0]))
    assert "Bounce Reduction 30 %" in texts and "Wind Resistance 25 %" in texts
    assert "atterrissage" in texts and "vent" in texts
    assert app.detail_window.state() == "withdrawn"
