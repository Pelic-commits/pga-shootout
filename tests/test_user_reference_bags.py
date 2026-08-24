from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pga_shootout.bag_evaluation import evaluate_saved_bag
from pga_shootout.models import EvaluationMode
from pga_shootout.storage import PgaDatabase
from pga_shootout.strategy_optimizer import (
    StrategyOptimizationRequest, StrategyOptimizer, render_strategy_optimization_json,
)
from pga_shootout.strategy_optimizer_gui import StrategyOptimizerPresenter
from pga_shootout.user_data import BagReferenceProfile, load_user_data


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


@pytest.fixture(scope="module")
def reference_database(tmp_path_factory):
    path = tmp_path_factory.mktemp("references") / "user.sqlite"
    shutil.copy2(ROOT / "data" / "pga_shootout.sqlite", path)
    database = PgaDatabase(path)
    definitions = (
        ("par3_divebomb", "Par 3", None, ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
         "Par 3", "divebomb", "stable", "", {"attack": {"power": 17, "control": 10, "spin": 9}, "putt": {"power": 11, "control": 16}}),
        (None, "Sac longueur", "Longueur max", ("xlr8r", "jumpstart", "divebomb", "sparky", "sunstorm"),
         "Longs Par 5", "xlr8r", "experimental", "Driver variable", {"drive": {"power": 15, "control": 8, "spin": 10}}),
        (None, "Sac Skyfury", "Longue portée Skyfury", ("gearshift", "skyfury", "jumpstart", "maelstrom", "divebomb"),
         "Longue portée", "skyfury", "stable", "Capacité connue utile en jeu", {"attack": {"power": 14, "control": 6, "spin": 13}}),
        (None, "Sac confort", "Confort Par 4/5", ("homestead", "kinship", "steadfast", "cyclotron", "jumpstart"),
         "Par 4 et Par 5", "cyclotron", "stable", "Polyvalent", {"drive": {"power": 16, "control": 9, "spin": 12}, "approach": {"power": 13, "control": 9, "spin": 9}}),
        (None, "Sac Windstrike", "Test Windstrike", ("windstrike", "jumpstart", "steadfast", "ember", "sunstorm"),
         "Test de portée", "windstrike", "experimental", "14 Power reste trop court pour l’usage recherché", {"attack": {"power": 14, "control": 10, "spin": 11}}),
    )
    ids = {}
    for existing_id, name, label, clubs, usage, primary, role, note, observed in definitions:
        bag_id = existing_id
        if bag_id is None:
            _, bag_id = database.save_bag(name, clubs)
        database.mark_bag_reference(bag_id, BagReferenceProfile(
            label=label or name, usage=usage, strategy_id="par3", primary_club_id=primary,
            role=role, note=note, club_notes={primary: note} if note else {}, observed_metrics=observed,
        ))
        ids[label or name] = bag_id
    return path, ids


def optimizer(path):
    return StrategyOptimizer(user_data_path=path, catalog_path=CATALOG, strategy_registry_path=REGISTRY)


def test_five_user_references_are_loaded_without_recreating_the_real_database(reference_database):
    path, _ = reference_database
    references = [bag for bag in load_user_data(path).bags if bag.reference]
    assert [bag.reference.label for bag in references] == [
        "Par 3", "Longueur max", "Longue portée Skyfury", "Confort Par 4/5", "Test Windstrike",
    ]
    assert references[-1].reference.club_notes["windstrike"].startswith("14 Power")


def test_reference_note_has_no_effect_on_rule_engine(reference_database):
    path, ids = reference_database
    before = evaluate_saved_bag(ids["Par 3"], level=8, mode=EvaluationMode.PARTIAL, user_dir=path)
    database = PgaDatabase(path)
    bag = next(item for item in database.load_user_bundle().bags if item.identifier == ids["Par 3"])
    database.mark_bag_reference(bag.identifier, BagReferenceProfile(
        **{**bag.reference.__dict__, "note": "Nouvelle note purement utilisateur"}
    ))
    after = evaluate_saved_bag(ids["Par 3"], level=8, mode=EvaluationMode.PARTIAL, user_dir=path)
    assert before.result == after.result


def test_par3_builder_compares_to_observed_divebomb_reference(reference_database):
    path, ids = reference_database
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id=ids["Par 3"],
        club_roles={"divebomb": "attack"}, primary_step_id="attack", limit=5, max_evaluations=300,
    ))
    assert result.comparison_reference.label == "Par 3"
    current = next(item for item in result.retained_results if "current_bag" in item.result_family_ids)
    assert current.metric_values_from_reference["attack.power"]["before"] == 17
    candidate = next(item for item in result.retained_results if item is not current)
    assert candidate.metric_values_from_reference["attack.control"]["before"] == 10
    presentation = StrategyOptimizerPresenter.load(REGISTRY).present(result)
    assert "COMPARAISON AVANT / APRÈS" in presentation.details[1].overview
    assert "RÉFÉRENCE — Par 3" in presentation.reference_text
    payload = json.loads(render_strategy_optimization_json(result))
    assert payload["comparison_reference"]["observed_metrics"]["attack"]["power"] == 17


def test_targeted_driver_replacement_keeps_four_clubs_and_can_expand_to_supports(reference_database):
    path, ids = reference_database
    base = {"jumpstart", "divebomb", "sparky", "sunstorm"}
    one = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
        replace_club_id="xlr8r", replacement_depth=1, limit=10, max_evaluations=100,
    ))
    changed = [item for item in one.retained_results if item.origin != "reference_bag"]
    assert changed and all(base.issubset(item.composition) for item in changed)
    assert one.search.optimality_status == "maximum_proven"
    expanded = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
        replace_club_id="xlr8r", replacement_depth=2, limit=5, max_evaluations=100,
    ))
    assert expanded.search.stage_counts["paires_generees"] > 0


@pytest.mark.parametrize(("label", "club_id"), (("Longue portée Skyfury", "skyfury"), ("Test Windstrike", "windstrike")))
def test_imposed_club_remains_usable_with_factual_warning(reference_database, label, club_id):
    path, ids = reference_database
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id=ids[label],
        club_roles={club_id: "attack"}, primary_step_id="attack", limit=3, max_evaluations=200,
    ))
    assert result.retained_results and all(club_id in item.composition for item in result.retained_results)
    if club_id == "skyfury":
        assert any("non entièrement simulée" in warning for warning in result.warnings)


def test_three_step_comparison_and_confirmed_reference_replacement(reference_database):
    path, ids = reference_database
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="interactive_builder", target_bag_id=ids["Confort Par 4/5"],
        club_roles={"kinship": "drive", "steadfast": "approach", "homestead": "putt"},
        primary_step_id="drive", limit=5, max_evaluations=300,
    ))
    compared = [item for item in result.retained_results if item.metric_values_from_reference]
    assert compared, [(item.origin, item.composition, item.result_family_ids) for item in result.retained_results]
    candidate = compared[0]
    assert {key.split(".", 1)[0] for key in candidate.metric_values_from_reference} == {"drive", "approach", "putt"}
    database = PgaDatabase(path)
    with pytest.raises(ValueError, match="confirmation explicite"):
        database.replace_reference_bag(ids["Confort Par 4/5"], candidate.composition)
    _, bag_id = database.replace_reference_bag(ids["Confort Par 4/5"], candidate.composition, confirmed=True)
    assert bag_id == ids["Confort Par 4/5"]
    assert next(item for item in database.load_user_bundle().bags if item.identifier == bag_id).reference is not None
