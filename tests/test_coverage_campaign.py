import json
from pathlib import Path
import shutil

import pytest

from pga_shootout.bag_comparison import ability_contributions, compare_saved_bags
from pga_shootout.bag_evaluation import evaluate_bag
from pga_shootout.inventory_status import ABILITY_STATUSES, analyze_inventory_status
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
RAW = ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"


def bag(*clubs: str) -> SavedBag:
    return SavedBag("campaign", "Campaign", "test_fixture", tuple(clubs), ())


def evaluate(clubs, current, *, level=9, terrain=None, mode=EvaluationMode.PARTIAL, pending=()):
    return evaluate_bag(
        bag(*clubs),
        level=level,
        mode=mode,
        catalog_path=CATALOG,
        current_club_id=current,
        terrain=terrain,
        pending_effects=pending,
    )


def contribution(evaluation, occurrence_id):
    return next(item for item in ability_contributions(evaluation) if item.ability_id == occurrence_id)


def test_existing_chain_scheduler_accepts_multiple_declared_club_types():
    clubs = ("navigator", "high_flight", "jumpstart", "homestead", "sandsend")
    source = evaluate(clubs, "navigator", level=9)
    assert len(source.result.scheduled_effects) == 1
    wood = evaluate(clubs, "high_flight", level=9, pending=source.result.pending_effects)
    assert wood.result.consumed_effect_ids == ("navigator__chains_into_woods_hybrids:next-compatible-shot",)
    assert wood.result.final_stats.control - wood.result.base_stats.control == 5


def test_chains_into_corvid_reuses_delayed_effect_and_consumes_once():
    clubs = ("conspiracy", "divebomb", "ember", "homestead", "sunstorm")
    source = evaluate(clubs, "conspiracy", level=9)
    target = evaluate(clubs, "divebomb", level=9, pending=source.result.pending_effects)
    assert target.result.consumed_effect_ids == ("conspiracy__chains_into_corvid:next-compatible-shot",)
    assert target.result.final_stats.power - target.result.base_stats.power == 5
    assert target.result.final_stats.control - target.result.base_stats.control == 5
    assert target.result.final_stats.spin - target.result.base_stats.spin == 5


def test_brand_and_self_wind_resistance_are_objective_modifiers():
    clubs = ("divebomb", "conspiracy", "into_the_blue", "homestead", "sunstorm")
    corvid = evaluate(clubs, "conspiracy", level=9)
    assert contribution(corvid, "divebomb__corvid_wind_resist").modification["wind_resistance_percent"] == 35
    self_only = evaluate(clubs, "into_the_blue", level=9)
    assert contribution(self_only, "into_the_blue__wind_resist").modification["wind_resistance_percent"] == 20
    non_corvid = evaluate(clubs, "homestead", level=9)
    assert contribution(non_corvid, "divebomb__corvid_wind_resist").modification.get("wind_resistance_percent", 0) == 0


@pytest.mark.parametrize(
    ("club_id", "occurrence", "expected"),
    (("into_the_blue", "into_the_blue__loft_angle_10", 10), ("rebound", "rebound__loft_angle_3", -3)),
)
def test_existing_static_modifier_pipeline_covers_remaining_loft(club_id, occurrence, expected):
    clubs = (club_id, "jumpstart", "ember", "homestead", "sunstorm")
    result = evaluate(clubs, club_id, level=9)
    assert contribution(result, occurrence).modification["loft_angle_degrees"] == expected


@pytest.mark.parametrize(
    ("source", "current", "terrain", "occurrence", "deltas"),
    (
        ("homecoming", "homecoming", "fairway", "homecoming__off_green_power", (14, 14, 0)),
        ("dunecrawler", "jumpstart", "sand", "dunecrawler__bag_sand_bonus", (5, 5, 5)),
        ("obelisk", "obelisk", "sand", "obelisk__sand_bonus_x", (5, 5, 5)),
        ("sandblast", "sandblast", "sand", "sandblast__sand_bonus", (11, 11, 5.5)),
        ("bushwhacker", "bushwhacker", "deep_rough", "bushwhacker__rough_bonus", (3, 3, 3)),
        ("hero", "hero", "rough", "hero__rough_power", (6, 0, 0)),
        ("new_frontier", "jumpstart", "rough", "new_frontier__bag_rough_power", (7, 0, 0)),
    ),
)
def test_simple_terrain_families_use_official_values(source, current, terrain, occurrence, deltas):
    clubs = (source, "jumpstart", "ember", "homestead", "sunstorm")
    result = evaluate(clubs, current, level=9, terrain=terrain)
    item = contribution(result, occurrence)
    assert tuple(item.modification.get(stat, 0) for stat in ("power", "control", "spin")) == deltas


def test_context_absence_is_unresolved_and_explain_records_expected_and_observed():
    clubs = ("bushwhacker", "jumpstart", "ember", "homestead", "sunstorm")
    partial = evaluate(clubs, "bushwhacker", level=9, terrain=None)
    assert not partial.result.complete
    summary = next(item for item in partial.result.explain if item.source.startswith("Bushwhacker /"))
    assert summary.inputs["context_field"] == "terrain"
    assert summary.inputs["expected"] == ["rough", "deep_rough"]
    assert summary.inputs["observed"] is None
    assert summary.outputs["condition_matched"] is False
    strict = evaluate(clubs, "bushwhacker", level=9, terrain=None, mode=EvaluationMode.STRICT)
    assert strict.strict_failed


def test_fairway_affinity_filters_brand_and_elite_adds_tee_condition():
    clubs = ("groundskeep", "homestead", "jumpstart", "steadfast", "sunstorm")
    fairway = evaluate(clubs, "homestead", level=9, terrain="fairway", mode=EvaluationMode.STRICT)
    assert contribution(fairway, "groundskeep__fairway_affinity").modification["power"] == 2
    wrong_brand = evaluate(clubs, "jumpstart", level=9, terrain="fairway", mode=EvaluationMode.STRICT)
    assert contribution(wrong_brand, "groundskeep__fairway_affinity").modification["power"] == 0
    elite = evaluate(clubs, "homestead", level={club: ("Elite" if club == "groundskeep" else 12) for club in clubs}, terrain="tee", mode=EvaluationMode.STRICT)
    assert contribution(elite, "groundskeep__fairway_affinity").modification["power"] == 3


def test_type_count_and_matching_neighbor_patterns_are_data_driven():
    triumph = evaluate(("triumph", "navigator", "steward", "rook", "homestead"), "navigator", level=9)
    assert contribution(triumph, "triumph__overdrive").modification["power"] == 6
    pantheon = evaluate(("pantheon", "jumpstart", "cloudcatcher", "high_flight", "rook"), "cloudcatcher", level=9)
    assert contribution(pantheon, "pantheon__combined_power").modification["power"] == 2
    assert contribution(pantheon, "pantheon__combined_spin").modification["spin"] == 1


def test_composed_blazing_flight_keeps_separate_power_and_loft_contributions():
    clubs = ("hot_streak", "jumpstart", "ember", "homestead", "sunstorm")
    result = evaluate(clubs, "hot_streak", level=9, terrain="tee")
    item = contribution(result, "hot_streak__blazing_flight")
    assert item.modification["power"] == 4
    assert item.modification["loft_angle_degrees"] == -3
    leaves = [entry for entry in result.result.explain if entry.source.startswith("Hot Streak /")]
    assert any(entry.mechanism == "ADD_STAT" for entry in leaves)
    assert any(entry.mechanism == "ADD_MODIFIER" for entry in leaves)


def test_composed_blazing_flight_explain_matches_golden():
    clubs = ("hot_streak", "jumpstart", "ember", "homestead", "sunstorm")
    result = evaluate(clubs, "hot_streak", level=9, terrain="tee")
    lines = []
    for entry in result.result.explain:
        if entry.source != "Hot Streak / hot_streak__blazing_flight":
            continue
        change = {key: value for key, value in entry.modification.items() if value}
        lines.append(
            f"{entry.mechanism} | {entry.condition} | {'APPLIED' if entry.applied else 'SKIPPED'} | "
            f"inputs={json.dumps(entry.inputs, sort_keys=True)} | outputs={json.dumps(entry.outputs, sort_keys=True)} | "
            f"change={json.dumps(change, sort_keys=True)}"
        )
    expected = (ROOT / "tests" / "golden" / "blazing_flight_composed_explain.txt").read_text(encoding="utf-8")
    assert "\n".join(lines) + "\n" == expected


def test_positioned_composed_gear_effects_apply_only_at_declared_edge():
    left = evaluate(("gearshift", "jumpstart", "ember", "homestead", "sunstorm"), "jumpstart", level=9)
    first = contribution(left, "gearshift__first_gear")
    assert first.modification["control"] == 1
    assert first.modification["bounce_reduction_percent"] == 12
    middle = evaluate(("jumpstart", "gearshift", "ember", "homestead", "sunstorm"), "jumpstart", level=9)
    assert contribution(middle, "gearshift__first_gear").modification.get("control", 0) == 0


def test_partial_compound_applies_certain_part_and_retains_unresolved_physics():
    clubs = ("crusader", "homestead", "jumpstart", "steadfast", "sunstorm")
    result = evaluate(clubs, "homestead", level=9)
    item = contribution(result, "crusader__brand_fairway_rush")
    assert item.modification["power"] == 2
    assert item.unresolved
    assert not result.result.complete


def test_optimizer_eligibility_and_all_owned_occurrences_have_precise_classification():
    report = analyze_inventory_status(
        user_dir=ROOT / "data" / "pga_shootout.sqlite",
        normalized_dir=ROOT / "data" / "normalized",
        raw_catalog_path=RAW,
    )
    assert report.simulated_abilities == 81
    assert (report.fully_optimizable_clubs, report.context_optimizable_clubs, report.warning_optimizable_clubs, report.non_optimizable_clubs) == (29, 6, 15, 25)
    assert all(ability.status in ABILITY_STATUSES for club in report.clubs for ability in club.abilities)
    assert all(ability.qualification_category != "unclassified" for club in report.clubs for ability in club.abilities)
    blacksmith = next(club for club in report.clubs if club.club_id == "blacksmith")
    assert blacksmith.optimizer_eligibility == "optimizable_with_context"
    pantheon = next(club for club in report.clubs if club.club_id == "pantheon")
    assert pantheon.optimizer_eligibility == "not_optimizable"


def test_every_catalog_group_is_implemented_or_has_an_explicit_blocker():
    semantic = json.loads((ROOT / "data" / "normalized" / "semantic_map.json").read_text(encoding="utf-8"))
    assert len(semantic["entries"]) == 125
    for entry in semantic["entries"].values():
        assert entry.get("mechanic_id") or entry.get("effects") or entry.get("qualification")


def test_compare_bags_exposes_new_modifier_without_rule_engine_special_case(tmp_path):
    user = tmp_path / "user"
    shutil.copytree(ROOT / "data" / "user", user)
    (user / "bags.json").write_text(json.dumps({"bags": [
        {"id": "left", "name": "Left", "status": "test", "club_ids": ["into_the_blue", "jumpstart", "ember", "homestead", "sunstorm"]},
        {"id": "right", "name": "Right", "status": "test", "club_ids": ["rebound", "jumpstart", "ember", "homestead", "sunstorm"]},
    ]}), encoding="utf-8")
    result = compare_saved_bags("left", "right", level=9, current_position=1, mode=EvaluationMode.PARTIAL, user_dir=user, catalog_path=CATALOG)
    metrics = {metric.definition.identifier for metric in result.metrics}
    assert "loft_angle_degrees" in metrics


def test_engine_contains_no_new_club_specific_branching():
    source = "\n".join((ROOT / "src" / "pga_shootout" / name).read_text(encoding="utf-8").casefold() for name in ("dsl.py", "engine.py", "conditions.py", "bag_evaluation.py"))
    for club_name in ("conspiracy", "triumph", "pantheon", "hot_streak", "gearshift", "bushwhacker"):
        assert club_name not in source
