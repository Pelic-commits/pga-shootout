from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pga_shootout.bag_evaluation import evaluate_saved_bag
from pga_shootout.models import EvaluationMode
from pga_shootout.storage import PgaDatabase
from pga_shootout.strategy_optimizer import (
    StrategyOptimizationError, StrategyOptimizationRequest, StrategyOptimizer,
    render_strategy_optimization, render_strategy_optimization_json,
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
    current = next(item for item in result.retained_results if "current_bag" in item.result_family_ids)
    expected = {"skyfury": (14, 6, 13), "windstrike": (14, 10, 11)}[club_id]
    assert tuple(
        current.metric_values_from_reference[f"attack.{metric}"]["before"]
        for metric in ("power", "control", "spin")
    ) == expected
    assert any(
        item.result_status == "partially_evaluated_tradeoff"
        for item in result.retained_results if item is not current
    )
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


def _club_types() -> dict[str, str]:
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {club_id: club["club_type"]["id"] for club_id, club in document["clubs"].items()}


def _best_power(result, step_id: str) -> float:
    values = []
    for candidate in result.retained_results:
        club_id = candidate.active_assignments[step_id]
        club = next(item for item in candidate.clubs if item.club_id == club_id)
        step = next(item for item in club.steps if item.step_id == step_id)
        if step.final_stats.get("power") is not None:
            values.append(step.final_stats["power"])
    return max(values)


def test_reference_superior_to_every_new_result_is_named_current_best(reference_database):
    path, ids = reference_database
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id=ids["Par 3"],
        club_roles={"divebomb": "attack"}, primary_step_id="attack", limit=8, max_evaluations=300,
    ))
    current = next(item for item in result.retained_results if "current_bag" in item.result_family_ids)
    assert current.result_status == "current_best_known"
    assert not result.improvement_without_loss_found
    assert any("Aucune amélioration sans perte calculable" in item for item in result.warnings)
    assert all(item.result_status != "strictly_inferior" for item in result.retained_results)
    assert any(
        item.result_status in {"tradeoff", "partially_evaluated_tradeoff"}
        for item in result.retained_results if item is not current
    )
    assert "Aucune amélioration sans perte calculable trouvée" in render_strategy_optimization(result)


def test_nonconforming_reference_uses_best_admissible_terminology(reference_database):
    path, ids = reference_database
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id=ids["Par 3"],
        club_roles={"divebomb": "attack"}, primary_step_id="attack",
        allowed_brands=("corvid", "palo", "ryusei", "willoughsby"),
        limit=5, max_evaluations=200,
    ))
    assert not result.reference_is_admissible
    assert any(
        item.result_status.startswith("best_admissible")
        for item in result.retained_results if item.origin != "reference_bag"
    )
    assert "Meilleurs sacs admissibles sous la restriction" in render_strategy_optimization(result)


def test_targeted_replacement_defaults_to_same_type_and_all_types_is_explicit(reference_database):
    path, ids = reference_database
    types = _club_types()
    same = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
        replace_club_id="xlr8r", replacement_depth=1, limit=12, max_evaluations=100,
    ))
    same_added = {
        club_id for item in same.retained_results if item.origin != "reference_bag"
        for club_id in item.added_club_ids
    }
    assert same.replacement_type_policy == "same_type" and same.replacement_type == "driver"
    assert same_added and {types[item] for item in same_added} == {"driver"}

    all_types = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
        replace_club_id="xlr8r", replacement_type_policy="all_types",
        replacement_depth=1, limit=12, max_evaluations=100,
    ))
    all_added = {
        club_id for item in all_types.retained_results if item.origin != "reference_bag"
        for club_id in item.added_club_ids
    }
    assert any(types[item] != "driver" for item in all_added)
    assert all_types.replacement_type is None


def test_same_type_supports_putter_brand_combination_and_explicit_conflict(reference_database):
    path, ids = reference_database
    types = _club_types()
    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par3", search_mode="replace_club", target_bag_id=ids["Par 3"],
        replace_club_id="ember", replacement_depth=1,
        allowed_brands=("corvid", "phoenix", "ryusei", "willoughsby"),
        limit=8, max_evaluations=80,
    ))
    assert all(
        types[club_id] == "putter"
        for item in result.retained_results if item.origin != "reference_bag"
        for club_id in item.added_club_ids
    )
    with pytest.raises(StrategyOptimizationError, match="Tous les types admissibles"):
        optimizer(path).optimize(StrategyOptimizationRequest(
            "par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
            replace_club_id="xlr8r", required_club_ids=("homecoming",),
            replacement_depth=1, limit=3, max_evaluations=30,
        ))


def test_up_to_two_replacements_contains_depth_zero_and_one_and_never_regresses(reference_database):
    path, ids = reference_database
    common = dict(
        strategy_id="par5", search_mode="replace_club", target_bag_id=ids["Longueur max"],
        replace_club_id="xlr8r", replacement_type_policy="same_type", limit=12, max_evaluations=120,
    )
    one = optimizer(path).optimize(StrategyOptimizationRequest(**common, replacement_depth=1))
    two = optimizer(path).optimize(StrategyOptimizationRequest(**common, replacement_depth=2))
    assert {item.replacement_depth for item in two.retained_results} >= {0, 1}
    assert _best_power(two, "drive") >= _best_power(one, "drive")
    assert one.search.optimality_status == "maximum_proven"
    assert two.search.optimality_status == "best_found"
    assert two.search.local_search_completeness == "structurally_reduced_two_replacements"


def test_reference_roles_are_optional_per_bag_and_drive_function_to_function_comparison(reference_database, tmp_path):
    source, ids = reference_database
    path = tmp_path / "roles.sqlite"
    shutil.copy2(source, path)
    database = PgaDatabase(path)
    comfort = next(item for item in database.load_user_bundle().bags if item.identifier == ids["Confort Par 4/5"])
    before = evaluate_saved_bag(comfort.identifier, level=8, mode=EvaluationMode.PARTIAL, user_dir=path)
    roles = {
        "cyclotron": "drive", "kinship": "approach", "homestead": "putt",
        "steadfast": "support", "jumpstart": "variable",
    }
    backup = database.mark_bag_reference(comfort.identifier, BagReferenceProfile(
        **{**comfort.reference.__dict__, "strategy_id": "par5", "reference_roles": roles}
    ))
    assert backup.exists()
    loaded = next(item for item in database.load_user_bundle().bags if item.identifier == comfort.identifier)
    assert loaded.reference.reference_roles == roles
    after = evaluate_saved_bag(comfort.identifier, level=8, mode=EvaluationMode.PARTIAL, user_dir=path)
    assert before.result == after.result

    result = optimizer(path).optimize(StrategyOptimizationRequest(
        "par5", search_mode="interactive_builder", target_bag_id=comfort.identifier,
        club_roles={"cyclotron": "drive", "kinship": "approach", "homestead": "putt"},
        primary_step_id="drive", limit=5, max_evaluations=200,
    ))
    current = next(item for item in result.retained_results if "current_bag" in item.result_family_ids)
    assert current.active_assignments == {"drive": "cyclotron", "approach": "kinship", "putt": "homestead"}
    assert result.comparison_reference.reference_roles == roles
    assert set(current.metric_values_from_reference) >= {"drive.power", "approach.power", "putt.power"}
    payload = json.loads(render_strategy_optimization_json(result))
    assert payload["comparison_reference"]["reference_roles"] == roles


def test_old_reference_migrates_to_automatic_roles_without_database_rewrite(reference_database):
    path, ids = reference_database
    bag = next(item for item in load_user_data(path).bags if item.identifier == ids["Par 3"])
    assert dict(bag.reference.reference_roles or {}) == {}


def test_same_club_can_have_different_observed_roles_in_two_reference_bags(tmp_path):
    path = tmp_path / "roles-per-bag.sqlite"
    shutil.copy2(ROOT / "data" / "pga_shootout.sqlite", path)
    database = PgaDatabase(path)
    bags = {item.identifier: item for item in database.load_user_bundle().bags}
    first, second = bags["par3_divebomb"], bags["par3_high_flight"]
    database.mark_bag_reference(first.identifier, BagReferenceProfile(
        label="Premier", strategy_id="par3", reference_roles={"ember": "putt"},
    ))
    database.mark_bag_reference(second.identifier, BagReferenceProfile(
        label="Second", strategy_id="par3", reference_roles={"ember": "support"},
    ))
    loaded = {item.identifier: item for item in database.load_user_bundle().bags}
    assert loaded[first.identifier].reference.reference_roles["ember"] == "putt"
    assert loaded[second.identifier].reference.reference_roles["ember"] == "support"
