from __future__ import annotations

import json
from pathlib import Path

import pytest

from pga_shootout.cli import build_parser
from pga_shootout.strategy_optimizer import (
    StrategyOptimizationError,
    StrategyOptimizationRequest,
    StrategyOptimizer,
    render_strategy_optimization,
    render_strategy_optimization_json,
)
from pga_shootout.strategy_optimizer_gui import OptimizationGuiOptions, StrategyOptimizerPresenter


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


def optimizer() -> StrategyOptimizer:
    return StrategyOptimizer(
        user_data_path=DATABASE,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    )


def brand_map() -> dict[str, str]:
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {club_id: club["brand"]["id"] for club_id, club in document["clubs"].items()}


def canonical_brands() -> dict[str, str]:
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {
        club["brand"]["id"]: club["brand"]["name"]
        for club in document["clubs"].values()
    }


def assert_candidates_use_only(result, allowed: set[str]) -> None:
    brands = brand_map()
    for candidate in result.retained_results:
        if candidate.origin == "reference_bag":
            continue
        assert {brands[club_id] for club_id in candidate.composition} <= allowed


def test_all_brands_is_the_default_and_explicit_all_is_equivalent():
    unrestricted = optimizer().optimize(StrategyOptimizationRequest("par3", limit=3, max_evaluations=120))
    all_ids = tuple(sorted(canonical_brands()))
    explicit = optimizer().optimize(StrategyOptimizationRequest(
        "par3", limit=3, max_evaluations=120, allowed_brands=all_ids,
    ))

    assert unrestricted.allowed_brands == ()
    assert [item.composition for item in explicit.retained_results] == [
        item.composition for item in unrestricted.retained_results
    ]


@pytest.mark.parametrize(
    ("strategy_id", "allowed"),
    (("par3", ("corvid",)), ("par3", ("corvid", "willoughsby")), ("par5", ("corvid",))),
)
def test_one_or_multiple_brands_filter_two_and_three_step_searches(strategy_id, allowed):
    result = optimizer().optimize(StrategyOptimizationRequest(
        strategy_id, limit=4, max_evaluations=160, allowed_brands=allowed,
    ))

    assert result.retained_results
    assert result.allowed_brand_names == tuple(canonical_brands()[item] for item in sorted(allowed))
    assert_candidates_use_only(result, set(allowed))


def test_catalog_is_the_only_source_of_canonical_brand_names_and_gui_transmits_ids():
    brands = canonical_brands()
    request = OptimizationGuiOptions("par3", allowed_brands=("nautilus", "palo")).to_request()

    assert brands["palo"] == "PALO"
    assert set(brands) == {"corvid", "forester", "mythical", "nautilus", "palo", "phoenix", "ryusei", "stanchion", "willoughsby"}
    assert request.allowed_brands == ("nautilus", "palo")


def test_cli_accepts_a_repeatable_allowed_brand_constraint():
    args = build_parser().parse_args([
        "optimize-strategy", "par3", "--allowed-brand", "nautilus", "--allowed-brand", "palo",
    ])
    assert args.allowed_brand == ["nautilus", "palo"]


def test_unknown_brand_is_rejected_before_search():
    with pytest.raises(StrategyOptimizationError, match="Marques inconnues : inconnue"):
        optimizer().optimize(StrategyOptimizationRequest("par3", allowed_brands=("inconnue",)))


@pytest.mark.parametrize(
    ("club_roles", "expected_names"),
    (
        ({"high_flight": "attack"}, ("High Flight",)),
        ({"high_flight": "attack", "ember": "putt"}, ("High Flight", "Ember")),
        ({"ember": "putt"}, ("Ember",)),
    ),
)
def test_imposed_active_or_putter_brand_conflicts_are_all_reported(club_roles, expected_names):
    with pytest.raises(StrategyOptimizationError) as captured:
        optimizer().optimize(StrategyOptimizationRequest(
            "par3", search_mode="interactive_builder", club_roles=club_roles,
            allowed_brands=("willoughsby",), limit=2, max_evaluations=40,
        ))

    assert all(name in str(captured.value) for name in expected_names)
    assert str(captured.value).count("ne fait pas partie des marques autorisées") == len(expected_names)


def test_nonconforming_reference_is_comparison_only_and_reports_every_violation():
    allowed = {"corvid", "ryusei", "willoughsby", "palo"}
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id="par3_divebomb",
        club_roles={"divebomb": "attack"}, primary_step_id="attack",
        allowed_brands=tuple(sorted(allowed)), limit=5, max_evaluations=180,
    ))

    current = next(item for item in result.retained_results if "current_bag" in item.result_family_ids)
    assert current.origin == "reference_bag"
    assert set(result.reference_brand_violations) == {"Ember", "Sunstorm"}
    assert any("uniquement pour la comparaison" in warning for warning in result.warnings)
    assert result.comparison_reference is not None
    assert_candidates_use_only(result, allowed)
    presenter = StrategyOptimizerPresenter.load(REGISTRY).present(result)
    assert "hors marques autorisées" in presenter.warning_text


def test_targeted_replacement_obeys_brands_and_rejects_an_impossible_one_change_conversion():
    allowed = {"corvid", "ryusei", "willoughsby", "phoenix"}
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par3", search_mode="replace_club", target_bag_id="par3_divebomb",
        replace_club_id="ember", replacement_depth=1,
        allowed_brands=tuple(sorted(allowed)), limit=8, max_evaluations=100,
    ))
    assert result.search.optimality_status == "maximum_proven"
    assert_candidates_use_only(result, allowed)

    with pytest.raises(StrategyOptimizationError, match="ne peut pas devenir conforme") as captured:
        optimizer().optimize(StrategyOptimizationRequest(
            "par3", search_mode="replace_club", target_bag_id="par3_divebomb",
            replace_club_id="divebomb", replacement_depth=1,
            allowed_brands=("willoughsby",), limit=3, max_evaluations=30,
        ))
    assert "Jumpstart" in str(captured.value)


def test_two_support_replacements_never_introduce_a_forbidden_brand():
    allowed = {"corvid", "ryusei", "willoughsby", "phoenix"}
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par3", search_mode="replace_club", target_bag_id="par3_divebomb",
        replace_club_id="ember", replacement_depth=2,
        allowed_brands=tuple(sorted(allowed)), limit=5, max_evaluations=100,
    ))
    assert_candidates_use_only(result, allowed)


def test_text_and_json_exports_keep_constraint_provenance_and_reference_violations():
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id="par3_divebomb",
        club_roles={"divebomb": "attack"}, allowed_brands=("corvid", "ryusei", "willoughsby", "palo"),
        limit=2, max_evaluations=80,
    ))
    payload = json.loads(render_strategy_optimization_json(result))
    text = render_strategy_optimization(result)

    assert payload["allowed_brands"] == ["corvid", "palo", "ryusei", "willoughsby"]
    assert payload["admissibility_provenance"] == "user_constraint"
    assert set(payload["reference_brand_violations"]) == {"Ember", "Sunstorm"}
    assert "Marques autorisées : Corvid, PALO, Ryusei, Willoughsby" in text
    assert "Sac de référence hors restriction" in text
