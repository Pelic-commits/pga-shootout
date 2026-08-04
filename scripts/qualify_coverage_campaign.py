"""Apply the validated, data-only semantic mappings from the coverage campaign."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "normalized" / "semantic_map.json"


def source_and_value() -> list[dict[str, Any]]:
    return [
        {"id": "source", "operation": "SELECT_SELF", "inputs": {"source_club_id": {"from": "effect.source_club_id"}}},
        {"id": "level_value", "operation": "READ_LEVEL_VALUE", "inputs": {"level": {"from": "effect.ability_level"}, "level_value": {"from": "effect.level_value"}}},
    ]


def self_stats(*stats: str) -> dict[str, Any]:
    nodes = source_and_value()
    nodes.extend(
        {"id": f"add_{stat}", "operation": "ADD_STAT", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "level_value.value"}}, "parameters": {"stat": stat}}
        for stat in stats
    )
    return {"version": "1.0", "nodes": nodes}


def self_modifier(modifier: str) -> dict[str, Any]:
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "add_modifier", "operation": "ADD_MODIFIER", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "level_value.value"}}, "parameters": {"modifier": modifier}}
    ]}


def selected_stats(selection: str, selection_inputs: dict[str, Any], selection_parameters: dict[str, Any], *stats: str) -> dict[str, Any]:
    inner = [
        {"id": f"add_{stat}", "operation": "ADD_STAT", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "level_value.value"}}, "parameters": {"stat": stat}}
        for stat in stats
    ]
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "targets", "operation": selection, "inputs": selection_inputs, "parameters": selection_parameters},
        {"id": "each_target", "operation": "FOR_EACH", "inputs": {"items": {"from": "targets.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": inner}}},
    ]}


def all_stats(*stats: str) -> dict[str, Any]:
    return selected_stats("SELECT_ALL", {"source": {"from": "source.club"}}, {"include_source": True}, *stats)


def all_modifier(modifier: str) -> dict[str, Any]:
    inner = [{"id": "apply_modifier", "operation": "ADD_MODIFIER", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "level_value.value"}}, "parameters": {"modifier": modifier}}]
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "targets", "operation": "SELECT_ALL", "inputs": {"source": {"from": "source.club"}}, "parameters": {"include_source": True}},
        {"id": "each_target", "operation": "FOR_EACH", "inputs": {"items": {"from": "targets.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": inner}}},
    ]}


def brand_targets_stats(*stats: str) -> dict[str, Any]:
    inner = [
        {"id": f"add_{stat}", "operation": "ADD_STAT", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "level_value.value"}}, "parameters": {"stat": stat}}
        for stat in stats
    ]
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "candidates", "operation": "SELECT_ALL", "inputs": {"source": {"from": "source.club"}}, "parameters": {"include_source": True}},
        {"id": "matching", "operation": "MATCH_BRAND", "inputs": {"source": {"from": "source.club"}, "clubs": {"from": "candidates.clubs"}}},
        {"id": "each_target", "operation": "FOR_EACH", "inputs": {"items": {"from": "matching.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": inner}}},
    ]}


def brand_targets_modifier(modifier: str) -> dict[str, Any]:
    inner = [{"id": "apply_modifier", "operation": "ADD_MODIFIER", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "level_value.value"}}, "parameters": {"modifier": modifier}}]
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "candidates", "operation": "SELECT_ALL", "inputs": {"source": {"from": "source.club"}}, "parameters": {"include_source": True}},
        {"id": "matching", "operation": "MATCH_BRAND", "inputs": {"source": {"from": "source.club"}, "clubs": {"from": "candidates.clubs"}}},
        {"id": "each_target", "operation": "FOR_EACH", "inputs": {"items": {"from": "matching.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": inner}}},
    ]}


def weighted_sand() -> dict[str, Any]:
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "half", "operation": "SCALE", "inputs": {"amount": {"from": "level_value.value"}, "factor": 0.5}},
        {"id": "add_power", "operation": "ADD_STAT", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "level_value.value"}}, "parameters": {"stat": "power"}},
        {"id": "add_control", "operation": "ADD_STAT", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "level_value.value"}}, "parameters": {"stat": "control"}},
        {"id": "add_spin", "operation": "ADD_STAT", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "half.value"}}, "parameters": {"stat": "spin"}},
    ]}


def delayed_set(field: str, values: list[str]) -> dict[str, Any]:
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "schedule", "operation": "SCHEDULE_EFFECT", "inputs": {"source": {"from": "source.club"}, "amount": {"from": "level_value.value"}, "ability_id": {"from": "effect.ability_id"}, "ability_source": {"from": "effect.ability_source"}}, "parameters": {"filter_field": field, "filter_values": values, "effect_mechanism": "add_all_stats"}}
    ]}


def driver_count(stat: str) -> dict[str, Any]:
    add = {"id": "apply_target", "operation": "ADD_STAT", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "scaled.value"}}, "parameters": {"stat": stat}}
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "candidates", "operation": "SELECT_ALL", "inputs": {"source": {"from": "source.club"}}, "parameters": {"include_source": True}},
        {"id": "drivers", "operation": "MATCH_TYPE", "inputs": {"clubs": {"from": "candidates.clubs"}}, "parameters": {"operator": "equals", "expected": "driver"}},
        {"id": "driver_count", "operation": "COUNT", "inputs": {"items": {"from": "drivers.clubs"}}},
        {"id": "scaled", "operation": "SCALE", "inputs": {"amount": {"from": "level_value.value"}, "factor": {"from": "driver_count.value"}}},
        {"id": "apply_source", "operation": "ADD_STAT", "inputs": {"target": {"from": "source.club"}, "delta": {"from": "scaled.value"}}, "parameters": {"stat": stat}},
        {"id": "each_driver", "operation": "FOR_EACH", "inputs": {"items": {"from": "drivers.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": [add]}}},
    ]}


def matching_neighbor_count(stat: str) -> dict[str, Any]:
    nested = [
        {"id": "neighbors", "operation": "SELECT_ADJACENT", "inputs": {"origin": {"from": "iteration.target"}}, "parameters": {"directions": ["left", "right"], "distance": 1}},
        {"id": "same_brand", "operation": "MATCH_BRAND", "inputs": {"source": {"from": "iteration.target"}, "clubs": {"from": "neighbors.clubs"}}},
        {"id": "count", "operation": "COUNT", "inputs": {"items": {"from": "same_brand.clubs"}}},
        {"id": "scaled", "operation": "SCALE", "inputs": {"amount": {"from": "level_value.value"}, "factor": {"from": "count.value"}}},
        {"id": "apply", "operation": "ADD_STAT", "inputs": {"target": {"from": "iteration.target"}, "delta": {"from": "scaled.value"}}, "parameters": {"stat": stat}},
    ]
    return {"version": "1.0", "nodes": source_and_value() + [
        {"id": "targets", "operation": "SELECT_ALL", "inputs": {"source": {"from": "source.club"}}, "parameters": {"include_source": True}},
        {"id": "each_target", "operation": "FOR_EACH", "inputs": {"items": {"from": "targets.clubs"}}, "parameters": {"binding": "target", "program": {"nodes": nested}}},
    ]}


def condition(kind: str, values: list[str], description: str) -> dict[str, Any]:
    return {"kind": kind, "parameters": {"field": "terrain", "values": values, "required": True}, "description": description}


def implemented(program: dict[str, Any], behavior: str, *, semantic_condition: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "complexity": "parameterized",
        "dependencies": ["ordered_bag", "source_club", "ability_level_value"],
        "interpretation_status": "implemented_from_official_text",
        "mechanic_id": "dsl_pipeline",
        "program": program,
        "behavior_id": behavior,
        "validation_status": "official_text_validated",
        "notes": ["Qualified from the exact official text and normalized per-level values during the coverage campaign."],
        "priority": 5,
    }
    if semantic_condition:
        result["condition"] = semantic_condition
    return result


def qualify(entry: dict[str, Any], status: str, category: str, reason: str, required: list[str], experiment: str | None = None) -> None:
    complexity_by_status = {
        "ambiguous": "special",
        "history_required": "stateful",
        "physics_required": "special",
        "unsupported": "special",
        "partial": "special",
    }
    entry["complexity"] = complexity_by_status.get(status, "special")
    entry["dependencies"] = list(required)
    entry["qualification"] = {"status": status, "category": category, "reason": reason, "required_data": required}
    if experiment:
        entry["qualification"]["experiment"] = experiment


def main() -> None:
    document = json.loads(PATH.read_text(encoding="utf-8"))
    entries = document["entries"]

    mappings: dict[str, dict[str, Any]] = {
        "chains_into_corvid": implemented(delayed_set("brand", ["corvid"]), "delayed_all_stats_by_club_attribute"),
        "chains_into_woods_hybrids": implemented(delayed_set("club_type", ["wood", "hybrid"]), "delayed_all_stats_by_club_attribute"),
        "chains_into_irons_putters_wedges_drivers": implemented(delayed_set("club_type", ["iron", "putter", "wedge", "driver"]), "delayed_all_stats_by_club_attribute"),
        "corvid_wind_resist": implemented(brand_targets_modifier("wind_resistance_percent"), "brand_static_modifier"),
        "wind_resist": implemented(self_modifier("wind_resistance_percent"), "self_static_modifier"),
        "loft_angle_10": implemented(self_modifier("loft_angle_degrees"), "self_static_modifier"),
        "loft_angle_3": implemented(self_modifier("loft_angle_degrees"), "self_static_modifier"),
        "groundspin_x3": implemented(self_modifier("groundspin_multiplier"), "self_static_modifier"),
        "groundspin_x4": implemented(self_modifier("groundspin_multiplier"), "self_static_modifier"),
        "swing_speed_x2": implemented(self_modifier("aim_arrow_speed_multiplier"), "self_static_modifier"),
        "gravity_reduction": implemented(self_modifier("gravity_reduction_percent"), "positioned_self_static_modifier", semantic_condition={"kind": "bag_position_equals", "parameters": {"source_club_id": "$source_club_id", "position": "rightmost"}, "description": "source club is in the rightmost bag position"}),
        "off_green_power": implemented(self_stats("power", "control", "spin"), "terrain_stat_bonus", semantic_condition=condition("state_not_in", ["green"], "terrain is not green")),
        "bag_sand_bonus": implemented(all_stats("power", "control", "spin"), "terrain_stat_bonus", semantic_condition=condition("state_in", ["sand"], "terrain is sand")),
        "sand_bonus_x": implemented(self_stats("power", "control", "spin"), "terrain_stat_bonus", semantic_condition=condition("state_in", ["sand"], "terrain is sand")),
        "sand_bonus": implemented(weighted_sand(), "terrain_weighted_stat_bonus", semantic_condition=condition("state_in", ["sand"], "terrain is sand")),
        "rough_bonus": implemented(self_stats("power", "control", "spin"), "terrain_stat_bonus", semantic_condition=condition("state_in", ["rough", "deep_rough"], "terrain is rough or deep rough")),
        "rough_power": implemented(self_stats("power"), "terrain_stat_bonus", semantic_condition=condition("state_in", ["rough", "deep_rough"], "terrain is rough or deep rough")),
        "bag_rough_power": implemented(all_stats("power"), "terrain_stat_bonus", semantic_condition=condition("state_in", ["rough", "deep_rough"], "terrain is rough or deep rough")),
        "fairway_affinity": implemented(brand_targets_stats("power", "control", "spin"), "brand_terrain_stat_bonus", semantic_condition={"kind": "state_in", "parameters": {"field": "terrain", "values": ["fairway"], "required": True}, "parameters_by_level": {"Elite": {"values": ["fairway", "tee"]}}, "description": "terrain is fairway; Elite also accepts tee"}),
        "overdrive": implemented(driver_count("power"), "type_count_scaled_stat_bonus"),
        "overaim": implemented(driver_count("control"), "type_count_scaled_stat_bonus"),
        "combined_power": implemented(matching_neighbor_count("power"), "matching_neighbor_count_stat_bonus"),
        "combined_spin": implemented(matching_neighbor_count("spin"), "matching_neighbor_count_stat_bonus"),
        "zephyr_x_mph": implemented(all_modifier("wind_speed_toward_hole_mph"), "bag_environment_modifier"),
        "ludicrous_mode": implemented(all_modifier("wind_speed_toward_hole_mph"), "bag_environment_modifier"),
    }
    for label, mapping in mappings.items():
        mapping["group_id"] = f"label:{label}"
        entries[f"label:{label}"].update(mapping)
        entries[f"label:{label}"].pop("qualification", None)

    # Fully deterministic composed abilities: every component remains separately attributable.
    entries["label:blazing_flight"].update({
        "complexity": "parameterized", "dependencies": ["source_club", "ability_level_value", "terrain"],
        "interpretation_status": "implemented_from_official_text", "mechanic_id": None,
        "behavior_id": "composed_tee_power_and_loft", "validation_status": "official_text_validated", "priority": 5,
        "notes": ["The tee Power and unconditional -3 degree loft components are separate effects."],
        "effects": [
            {"mechanic_id": "dsl_pipeline", "program": self_stats("power"), "level_value_component": "power_bonus", "condition": condition("state_in", ["tee"], "terrain is tee")},
            {"mechanic_id": "dsl_pipeline", "program": self_modifier("loft_angle_degrees"), "constant_level_value": -3},
        ],
    })

    position_conditions = {
        "first_gear": ("leftmost", "control_bonus", "control", "bounce_reduction", "bounce_reduction_percent"),
        "top_gear": ("rightmost", "power_bonus", "power", "groundspin_increase", "groundspin_increase_percent"),
    }
    for label, (position, stat_component, stat, modifier_component, modifier) in position_conditions.items():
        position_condition = {"kind": "bag_position_equals", "parameters": {"source_club_id": "$source_club_id", "position": position}, "description": f"source club is in the {position} bag position"}
        entries[f"label:{label}"].update({
            "complexity": "parameterized", "dependencies": ["ordered_bag", "source_club", "ability_level_components"],
            "interpretation_status": "implemented_from_official_text", "mechanic_id": None,
            "behavior_id": "positioned_bag_composed_modifier", "validation_status": "official_text_validated", "priority": 5,
            "notes": ["The two official table components are evaluated as separate effects."],
            "effects": [
                {"mechanic_id": "dsl_pipeline", "program": all_stats(stat), "level_value_component": stat_component, "condition": position_condition},
                {"mechanic_id": "dsl_pipeline", "program": all_modifier(modifier), "level_value_component": modifier_component, "condition": position_condition},
            ],
        })

    # Partially calculable compound abilities retain an explicit unresolved effect.
    partials = {
        "brand_fairway_rush": (brand_targets_stats("power"), "power_bonus", "The Willoughsby Power component is exact; fairway speed/distance still requires a physics contract."),
        "forester_power_elite": (brand_targets_stats("power"), "amount", "The Forester Power component is exact; tree passing still requires collision semantics."),
    }
    for label, (program, component, reason) in partials.items():
        entries[f"label:{label}"].update({
            "complexity": "special", "dependencies": ["source_club", "ability_level_components", "unresolved_physics_component"],
            "interpretation_status": "partially_implemented_from_official_text", "mechanic_id": None,
            "behavior_id": "composed_partial", "validation_status": "official_text_partially_validated", "priority": 4,
            "notes": [reason],
            "effects": [
                {"mechanic_id": "dsl_pipeline", "program": program, "level_value_component": component},
                {"mechanic_id": None, "allow_valueless": True},
            ],
        })
        qualify(entries[f"label:{label}"], "partial", "clear_component_plus_physics", reason, ["physics_contract"], "Measure the speed/distance or tree-collision component independently in game.")

    # Precise, auditable blockers for every group that remains unimplemented.
    conflict = {
        "wind_resistance_100": "The official text says 100% while the normalized level table contains 85%.",
        "chains_into_itself": "The official text says +2 to all stats while the level table contains +6 and +7.",
        "magnetism_0_15ft": "The official text uses feet while normalized table values are marked as metres.",
        "electrodynamics_0_2ft": "The official text uses feet while normalized table values are marked as metres, and the chain-hit increment duration is stateful.",
        "terrain_resist_50": "The shared label contains level-varying values and an Elite 60% value that conflicts with one club text stating 50%.",
    }
    for label, reason in conflict.items():
        qualify(entries[f"label:{label}"], "ambiguous", "official_text_table_conflict", reason, ["official_data_resolution"], "Compare the displayed in-game ability value and resulting modifier at the conflicting level.")

    geometry = {
        "flight_training", "boundary_rush_75", "boundary_bonus", "tree_bonus", "wild_rush_speed", "tree_bonus_x",
        "bag_tree_bonus", "water_rush", "water_bonus", "shoreline_rush", "emerald_rush_75", "water_bonus_x",
        "boundary_rush", "ground_rush", "green_grip", "momentum", "alien_world", "tree_passing", "bag_tree_passing",
        "bag_water_bounce", "bag_water_bonus", "power_shot",
    }
    for label in geometry:
        qualify(entries[f"label:{label}"], "physics_required", "geometry_or_trajectory_required", "The official effect depends on proximity, trajectory phase, collision, timing, or physical speed/distance behavior that the static context does not contain.", ["validated_geometry_or_physics"], "Record the relevant distance/time/terrain phase and the before/after in-game result across boundary cases.")

    history = {
        "adventure", "perfect_shot_bag_power", "perfect_shot_terrain_bonus_boost", "fission", "gravity_reduction_x",
        "palo_control_on_hit_x", "hollow_earth", "volt_bounce", "wind_up_toy", "ability_mirror",
    }
    for label in history:
        qualify(entries[f"label:{label}"], "history_required", "state_duration_or_trigger_unknown", "The trigger is identifiable, but duration, reset, consumption, or stacking semantics are not fully specified by the official text.", ["validated_trigger_lifetime"], "Trigger the effect once, change club, repeat it, and observe persistence, reset, and stacking separately.")

    random_or_transform = {"random_boost_x", "trumpet_blast", "shuffle_up", "three_heads", "beast_strength", "sacrifice"}
    for label in random_or_transform:
        qualify(entries[f"label:{label}"], "unsupported", "random_or_transformational", "The ability performs random selection, destruction, replacement, or bag transformation outside deterministic comparison.", ["random_or_transformation_model"])

    dependency_ambiguity = {
        "shared_growth": "Whether copied Tree Bonus uses the source level, target level, or evaluated source contribution is not specified.",
        "home_turf_southwind": "The official course identity and exact doubling stage of Forester Power must be validated.",
        "scottsdale_boosters": "The exact doubling stage of Phoenix Power and official course identity must be validated.",
        "gem_ball_bonus": "The source and stacking order of Gem Ball bonuses are outside the official club table.",
        "rocket_boosters": "The text does not establish whether neighboring base stats or final ability-modified stats are copied.",
        "stat_fusion": "The text does not establish whether neighboring base stats or final ability-modified stats are copied.",
        "super_fireball": "The Fireball changes and the stage at which their percentage is increased are not specified here.",
        "solidarity": "Interactions between multi-brand identity and every brand filter require a validated matching contract.",
        "alien_relic_left": "Ability duplication, level provenance, wrapping, ordering, and recursion are not validated.",
        "alien_relic_right": "Ability duplication, level provenance, wrapping, ordering, and recursion are not validated.",
        "aura_of_death": "The text does not establish base-versus-final source stats or ability-order interactions.",
        "smoke_x": "With two matching neighbors, whether the source bonus stacks once or twice is not specified.",
        "steam_x": "With two matching neighbors, whether the source bonus stacks once or twice is not specified.",
        "sparks_x": "With two matching neighbors, whether the source bonus stacks once or twice is not specified.",
        "bag_wind_power": "The rounding rule for incomplete wind-speed intervals and interaction with wind-changing abilities are not specified.",
        "rough_boosters": "At Elite the behavior changes from categorical rough to nearby-area scaling, whose formula is not specified.",
        "terrain_bonus": "The listed terrain bonuses use proximity/terrain formulas that are not present in the official table.",
    }
    for label, reason in dependency_ambiguity.items():
        qualify(entries[f"label:{label}"], "ambiguous", "true_semantic_ambiguity", reason, ["in_game_validation"], "Compare the competing interpretations in a minimal bag and record the exact displayed stat change.")

    # Sanity gate: no uninterpreted group may silently fall back to a generic ambiguous bucket.
    missing = [
        key for key, entry in entries.items()
        if not entry.get("mechanic_id") and not entry.get("effects") and not entry.get("qualification")
    ]
    if missing:
        raise RuntimeError(f"Missing explicit qualification for: {', '.join(missing)}")

    PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
