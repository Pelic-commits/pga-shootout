from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from pga_shootout.metric_semantics import MetricSemanticsRegistry
from pga_shootout.strategy import StrategyRegistry
from pga_shootout.strategy_optimizer import (
    StrategyCandidateGenerator,
    _metric_qualifies_support,
    _metric_relevance,
)


ROOT = Path(__file__).resolve().parents[1]


def test_registry_directions_and_safe_unknown_default():
    registry = MetricSemanticsRegistry.load(ROOT / "data/strategies/metric_semantics.json")
    assert registry.get("power").direction == "maximize"
    assert registry.get("loft_angle_degrees").direction == "descriptive"
    unknown = registry.get("future_metric")
    assert unknown.direction == "descriptive"
    assert not unknown.objective_allowed
    assert not unknown.support_qualifying_allowed


def test_par3_metric_relevance_is_function_specific():
    semantics = MetricSemanticsRegistry.load(ROOT / "data/strategies/metric_semantics.json")
    strategy = StrategyRegistry.load(ROOT / "data/strategies/strategies.json").get("par3")
    attack, putt = strategy.sequence
    assert _metric_relevance(attack, "power", semantics) == "objective"
    assert _metric_relevance(attack, "loft_angle_degrees", semantics) == "descriptive"
    for metric in ("bounce_reduction_percent", "wind_resistance_percent", "loft_angle_degrees", "spin"):
        assert _metric_relevance(putt, metric, semantics) == "descriptive"
        assert not _metric_qualifies_support(putt, metric, semantics)


def test_context_metric_requires_declared_matching_context():
    semantics = MetricSemanticsRegistry.load(ROOT / "data/strategies/metric_semantics.json")
    attack = StrategyRegistry.load(ROOT / "data/strategies/strategies.json").get("par3").sequence[0]
    assert _metric_relevance(attack, "wind_resistance_percent", semantics) == "descriptive"
    windy = replace(attack, context=replace(attack.context, values={**attack.context.values, "wind_relation": "head_or_crosswind"}))
    assert _metric_relevance(windy, "wind_resistance_percent", semantics) == "objective"


def test_order_modes_have_exact_and_diagnostic_cardinalities():
    generator = StrategyCandidateGenerator()
    clubs = ("a", "b", "c", "d", "e")
    insensitive = SimpleNamespace(order_sensitive_ids=set())
    sensitive = SimpleNamespace(order_sensitive_ids={"c"})
    assert len(generator._orders_for(clubs, insensitive, "structural_exact")) == 1
    assert len(generator._orders_for(clubs, sensitive, "structural_exact")) == 120
    assert len(generator._orders_for(clubs, sensitive, "full_120")) == 120
    assert len(generator._orders_for(clubs, sensitive, "legacy_reduced")) == 8
