import contextlib
import io
import json
from pathlib import Path

import pytest

from pga_shootout.cli import main
from pga_shootout.optimization_contract import OptimizationRequest
from pga_shootout.strategy import (
    StrategyDefinition,
    StrategyError,
    StrategyRegistry,
    StrategyVariant,
    to_optimization_request,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "strategies" / "strategies.json"


def structure_signature(strategy):
    return tuple(
        (
            step.identifier,
            step.active_role,
            step.function.identifier,
            tuple(sorted(step.function.parameters)),
            tuple(objective.operation for objective in step.local_objectives),
        )
        for step in strategy.sequence
    )


def test_registry_loads_the_four_data_driven_strategies_and_variant():
    registry = StrategyRegistry.load(CATALOG)
    assert tuple(item.identifier for item in registry.strategies) == (
        "par3",
        "par4_short",
        "par4_long",
        "par5",
    )
    assert tuple(item.identifier for item in registry.variants) == ("head_crosswind",)
    assert registry.get("par3").available_support_clubs == 3
    assert registry.get("par5").available_support_clubs == 2


def test_definitions_and_variants_round_trip_through_json():
    registry = StrategyRegistry.load(CATALOG)
    for strategy in registry.strategies:
        payload = json.loads(json.dumps(strategy.to_dict()))
        assert StrategyDefinition.from_dict(payload) == strategy
    for variant in registry.variants:
        payload = json.loads(json.dumps(variant.to_dict()))
        assert StrategyVariant.from_dict(payload) == variant


def test_direct_and_three_step_presets_share_exact_generic_architectures():
    registry = StrategyRegistry.load(CATALOG)
    par3 = registry.get("par3")
    short = registry.get("par4_short")
    long = registry.get("par4_long")
    par5 = registry.get("par5")

    assert structure_signature(par3) == structure_signature(short)
    assert structure_signature(long) == structure_signature(par5)
    assert par3.sequence[0].requirements == short.sequence[0].requirements
    assert long.sequence[0].requirements == par5.sequence[0].requirements
    assert len(long.sequence[1].requirements) == 1
    assert len(par5.sequence[1].requirements) == 2


def test_no_preset_imposes_a_club_type_or_global_score():
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    serialized = json.dumps(document)
    assert "club_type" not in serialized
    assert "global_score" not in serialized
    assert all(
        objective["metric"] == "all_comparable_metrics"
        for strategy in document["strategies"]
        for step in strategy["sequence"]
        for objective in step["local_objectives"]
    )


def test_variant_is_a_delta_and_does_not_mutate_or_duplicate_its_base():
    registry = StrategyRegistry.load(CATALOG)
    base = registry.resolve("par4_long")
    resolved = registry.resolve("par4_long", ("head_crosswind",))

    assert base.definition.sequence[0].context.values == {"terrain": "tee"}
    assert resolved.definition.sequence[0].context.values["wind_relation"] == "head_or_crosswind"
    assert len(resolved.definition.sequence) == len(base.definition.sequence)
    assert resolved.definition.sequence[2] == base.definition.sequence[2]
    assert "validated_wind_direction_context" in resolved.missing_evaluation_data
    assert "wind_speed" in resolved.missing_evaluation_data

    raw_variant = json.loads(CATALOG.read_text(encoding="utf-8"))["variants"][0]
    assert set(raw_variant) == {
        "identifier", "version", "user_name", "description", "compatible_strategy_ids", "patches"
    }
    assert all(
        set(patch) == {
            "step_id", "context_updates", "required_context_data", "add_requirements", "add_local_objectives"
        }
        for patch in raw_variant["patches"]
    )


def test_incompatible_unknown_and_duplicate_variants_are_rejected():
    registry = StrategyRegistry.load(CATALOG)
    with pytest.raises(StrategyError, match="not compatible"):
        registry.resolve("par3", ("head_crosswind",))
    with pytest.raises(StrategyError, match="Unknown strategy variant"):
        registry.resolve("par5", ("unknown",))
    with pytest.raises(StrategyError, match="more than once"):
        registry.resolve("par5", ("head_crosswind", "head_crosswind"))


def test_registry_is_extensible_with_a_second_catalog(tmp_path):
    registry = StrategyRegistry.load(CATALOG)
    custom = registry.get("par3").to_dict()
    custom.update(identifier="user_custom", user_name="Ma stratégie", origin="user")
    extension = tmp_path / "custom.json"
    extension.write_text(
        json.dumps({"schema_version": "1.0.0", "strategies": [custom], "variants": []}),
        encoding="utf-8",
    )

    merged = StrategyRegistry.load(CATALOG, extension)
    assert len(merged.strategies) == 5
    assert merged.get("user_custom").origin == "user"


def test_strategy_compiles_to_the_existing_optimization_request_contract():
    registry = StrategyRegistry.load(CATALOG)
    resolved = registry.resolve("par5", ("head_crosswind",))
    request = to_optimization_request(
        resolved,
        request_id="strategy-test",
        catalog_version="catalog-v1",
    )

    assert tuple(item["step_id"] for item in request.scope.scenarios) == ("drive", "approach", "putt")
    assert all("step_id" in item.subject for item in request.constraints)
    assert {item.scenario_selector["step_id"] for item in request.objectives} == {
        "drive", "approach", "putt"
    }
    assert any(item.metric == "wind_resistance_percent" for item in request.objectives)
    assert request.comparison_policy == "constraints_then_local_pareto"
    assert request.uncertainty_policy == "report_indeterminate"
    assert OptimizationRequest.from_dict(json.loads(json.dumps(request.to_dict()))) == request


def test_strategy_code_contains_no_identifier_specific_branching():
    source = (ROOT / "src" / "pga_shootout" / "strategy.py").read_text(encoding="utf-8")
    assert "if par3" not in source.lower()
    assert "if par4" not in source.lower()
    assert "if long_drive" not in source.lower()
    for identifier in ("par3", "par4_short", "par4_long", "par5", "head_crosswind"):
        assert identifier not in source


def test_consultation_cli_lists_and_shows_roles_variants_and_missing_data():
    listed = io.StringIO()
    with contextlib.redirect_stdout(listed):
        assert main(["strategy-list", "--registry", str(CATALOG)]) == 0
    assert "Sac Par 3" in listed.getvalue()
    assert "head_crosswind" in listed.getvalue()

    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        assert main([
            "strategy-show", "par4_long", "--variant", "head_crosswind",
            "--registry", str(CATALOG),
        ]) == 0
    assert "Rôles actifs: drive_club, approach_club, putter" in shown.getvalue()
    assert "Clubs support disponibles: 2" in shown.getvalue()
    assert "validated_carry_model" in shown.getvalue()
    assert "validated_wind_direction_context" in shown.getvalue()


def test_consultation_json_is_stable_and_structured():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main([
            "strategy-show", "par3", "--json", "--registry", str(CATALOG)
        ]) == 0
    payload = json.loads(output.getvalue())
    assert payload["strategy"]["identifier"] == "par3"
    assert payload["strategy"]["expected_active_roles"] == ["attack_club", "putter"]
    assert payload["missing_evaluation_data"] == [
        "validated_carry_model", "target_distance", "validated_putt_model"
    ]
