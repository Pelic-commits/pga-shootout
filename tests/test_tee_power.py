import json
from pathlib import Path
import shutil

from pga_shootout.bag_comparison import ability_contributions, compare_saved_bags
from pga_shootout.bag_evaluation import evaluate_bag, render_bag_evaluation
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
USER_DIR = ROOT / "data" / "user"


def bag(source: str) -> SavedBag:
    return SavedBag(
        "tee-test",
        "Tee test",
        "test_fixture",
        (source, "homestead", "commonlaw", "steadfast", "jumpstart"),
        (),
    )


def evaluate(source="blacksmith", *, level=9, terrain="tee", mode=EvaluationMode.PARTIAL):
    return evaluate_bag(
        bag(source),
        level=level,
        mode=mode,
        catalog_path=CATALOG,
        current_club_id=source,
        terrain=terrain,
    )


def test_texas_tee_uses_official_level_value_and_generic_dsl_pipeline():
    evaluation = evaluate(level=9, terrain="tee", mode=EvaluationMode.STRICT)
    assert not evaluation.strict_failed
    assert evaluation.result.base_stats.power == 10
    assert evaluation.result.final_stats.power == 15
    journal = [entry for entry in evaluation.result.explain if entry.source.startswith("Blacksmith /")]
    assert [entry.mechanism for entry in journal] == [
        "SELECT_SELF",
        "READ_LEVEL_VALUE",
        "ADD_STAT",
        "dsl_pipeline",
    ]
    assert journal[0].outputs == {"club": "Blacksmith"}
    assert journal[1].inputs == {"level": 9}
    assert journal[1].outputs == {"value": 5.0}
    assert journal[2].outputs == {"before": 10.0, "after": 15.0}
    assert journal[-1].condition == "shot terrain is tee"
    contribution = next(
        item for item in ability_contributions(evaluation) if item.ability_id == "blacksmith__texas_tee"
    )
    assert contribution.modification == {"power": 5.0, "control": 0.0, "spin": 0.0}
    assert contribution.applied


def test_tee_power_does_not_apply_off_the_tee():
    evaluation = evaluate(terrain="fairway", mode=EvaluationMode.STRICT)
    assert not evaluation.strict_failed
    assert evaluation.result.final_stats.power == evaluation.result.base_stats.power
    entry = next(entry for entry in evaluation.result.explain if entry.source.startswith("Blacksmith /"))
    assert not entry.applied
    assert entry.condition == "shot terrain is tee"
    assert entry.message == "condition not satisfied"


def test_missing_tee_context_is_unresolved_in_partial_and_blocking_in_strict():
    partial = evaluate(terrain=None, mode=EvaluationMode.PARTIAL)
    assert not partial.strict_failed
    assert not partial.result.complete
    assert len(partial.result.unresolved) == 1
    assert "Missing required scenario context: terrain" in partial.result.unresolved[0]
    assert partial.result.final_stats.power == partial.result.base_stats.power

    strict = evaluate(terrain=None, mode=EvaluationMode.STRICT)
    assert strict.strict_failed
    assert not strict.result.complete
    assert "Missing required scenario context: terrain" in strict.result.unresolved[0]


def test_texas_tee_recalculates_from_level_data():
    level_9 = evaluate(level=9, terrain="tee", mode=EvaluationMode.STRICT)
    level_10 = evaluate(level=10, terrain="tee", mode=EvaluationMode.STRICT)
    assert level_9.result.final_stats.power - level_9.result.base_stats.power == 5
    assert level_10.result.final_stats.power - level_10.result.base_stats.power == 6


def test_sidewinder_tee_off_power_reuses_the_same_pipeline_in_partial_mode():
    evaluation = evaluate(source="sidewinder", level=6, terrain="tee")
    tee = next(
        item for item in ability_contributions(evaluation) if item.ability_id == "sidewinder__tee_off_power"
    )
    assert tee.modification == {"power": 5.0, "control": 0.0, "spin": 0.0}
    assert tee.applied
    groundspin = next(
        item for item in ability_contributions(evaluation) if item.ability_id == "sidewinder__groundspin_x3"
    )
    assert groundspin.modification["groundspin_multiplier"] == 3


def test_compare_bags_propagates_terrain_and_attributes_tee_contribution(tmp_path):
    user_dir = tmp_path / "user"
    shutil.copytree(USER_DIR, user_dir)
    bags_path = user_dir / "bags.json"
    document = json.loads(bags_path.read_text(encoding="utf-8"))
    document["bags"].extend(
        [
            {
                "id": "blacksmith-tee",
                "name": "Blacksmith Tee",
                "status": "test_fixture",
                "club_ids": list(bag("blacksmith").club_ids),
            },
            {
                "id": "sidewinder-tee",
                "name": "Sidewinder Tee",
                "status": "test_fixture",
                "club_ids": list(bag("sidewinder").club_ids),
            },
        ]
    )
    bags_path.write_text(json.dumps(document), encoding="utf-8")
    comparison = compare_saved_bags(
        "blacksmith-tee",
        "sidewinder-tee",
        level=9,
        current_position=1,
        mode=EvaluationMode.PARTIAL,
        user_dir=user_dir,
        catalog_path=CATALOG,
        terrain="tee",
    )
    assert comparison.terrain == "tee"
    blacksmith = next(
        item for item in comparison.left.ability_contributions if item.ability_id == "blacksmith__texas_tee"
    )
    sidewinder = next(
        item for item in comparison.right.ability_contributions if item.ability_id == "sidewinder__tee_off_power"
    )
    assert blacksmith.modification["power"] == 5
    assert sidewinder.modification["power"] == 6


def test_rendered_explain_names_scenario_condition_and_power_change():
    rendered = render_bag_evaluation(evaluate(level=9, terrain="tee", mode=EvaluationMode.STRICT))
    assert "Terrain scenario: tee" in rendered
    assert "Condition: shot terrain is tee" in rendered
    assert "Effect: ADD_STAT" in rendered
    assert "'before': 10.0, 'after': 15.0" in rendered


def test_engine_execution_contains_no_club_specific_logic():
    engine_sources = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8").casefold()
        for relative in (
            "src/pga_shootout/bag_evaluation.py",
            "src/pga_shootout/conditions.py",
            "src/pga_shootout/dsl.py",
            "src/pga_shootout/engine.py",
        )
    )
    assert "blacksmith" not in engine_sources
    assert "sidewinder" not in engine_sources
    assert "texas tee" not in engine_sources
