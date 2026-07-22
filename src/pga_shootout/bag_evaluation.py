"""End-to-end user bag evaluation using the existing rule registries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .engine import EvaluationError, RuleEngine
from .loader import load_raw_json
from .models import Ability, Bag, BagEntry, Club, Condition, Effect, EvaluationMode, EvaluationResult, GameState, Stats
from .user_data import SavedBag, load_user_data


class BagEvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class BagEvaluation:
    bag: SavedBag
    state: GameState
    result: EvaluationResult
    mode: EvaluationMode
    strict_failed: bool
    supported_mechanics: tuple[str, ...]


def load_saved_bag(user_dir: str | Path, bag_id: str) -> SavedBag:
    bundle = load_user_data(user_dir)
    for bag in bundle.bags:
        if bag.identifier == bag_id:
            return bag
    available = ", ".join(item.identifier for item in bundle.bags)
    raise BagEvaluationError(f"Unknown bag {bag_id!r}. Available bags: {available}")


def _stats_by_level(club_data: Mapping[str, Any]) -> dict[int | str, Stats]:
    stats: dict[int | str, Stats] = {}
    for level_name, level_data in club_data["levels"].items():
        values = level_data.get("stats", {})
        if level_data.get("available") and all(values.get(name) is not None for name in ("power", "control", "spin")):
            level: int | str = int(level_name) if str(level_name).isdigit() else str(level_name)
            stats[level] = Stats.from_mapping(values)
    return stats


def _official_level_scalar(value: Mapping[str, Any]) -> float | None:
    notation = value.get("official_notation")
    components = notation.get("components") if isinstance(notation, Mapping) else None
    if not isinstance(components, list) or len(components) != 1:
        return None
    scalar = components[0].get("value") if isinstance(components[0], Mapping) else None
    if isinstance(scalar, bool) or not isinstance(scalar, (int, float)):
        return None
    return float(scalar)


def _official_level_components(value: Mapping[str, Any]) -> dict[str, float]:
    semantic = value.get("semantic_value")
    components = semantic.get("components") if isinstance(semantic, Mapping) else None
    if not isinstance(components, Mapping):
        return {}
    resolved: dict[str, float] = {}
    for name, component in components.items():
        numeric = component.get("value") if isinstance(component, Mapping) else None
        if isinstance(numeric, bool) or not isinstance(numeric, (int, float)):
            continue
        resolved[str(name)] = float(numeric)
    return resolved


def _materialize_pattern(value: Any, parameters: Mapping[str, Any]) -> Any:
    """Resolve declarative pattern parameters without knowing any ability family."""
    if isinstance(value, Mapping) and set(value) == {"pattern_parameter"}:
        name = str(value["pattern_parameter"])
        try:
            replacement = parameters[name]
        except KeyError as exc:
            raise BagEvaluationError(f"Missing semantic pattern parameter: {name}") from exc
        return _materialize_pattern(replacement, parameters)
    if isinstance(value, list):
        return [_materialize_pattern(item, parameters) for item in value]
    if isinstance(value, Mapping):
        return {key: _materialize_pattern(item, parameters) for key, item in value.items()}
    return value


def _semantic_program(
    semantic: Mapping[str, Any],
    semantic_patterns: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    inline = semantic.get("program")
    if isinstance(inline, Mapping):
        return inline
    pattern_id = semantic.get("pattern_id")
    if not pattern_id:
        return None
    try:
        pattern = semantic_patterns[str(pattern_id)]
    except KeyError as exc:
        raise BagEvaluationError(f"Unknown semantic pattern: {pattern_id}") from exc
    if not isinstance(pattern, Mapping) or not isinstance(pattern.get("program"), Mapping):
        raise BagEvaluationError(f"Semantic pattern {pattern_id!r} has no valid program")
    parameters = semantic.get("pattern_parameters", {})
    if not isinstance(parameters, Mapping):
        raise BagEvaluationError(f"Semantic pattern parameters for {pattern_id!r} must be an object")
    materialized = _materialize_pattern(pattern["program"], parameters)
    if not isinstance(materialized, Mapping):
        raise BagEvaluationError(f"Semantic pattern {pattern_id!r} did not produce a program")
    return materialized


def _abilities_at_level(
    club_data: Mapping[str, Any],
    level: int | str,
    semantic_entries: Mapping[str, Any] | None = None,
    semantic_patterns: Mapping[str, Any] | None = None,
) -> tuple[Ability, ...]:
    abilities = []
    level_key = str(level)
    for item in club_data.get("abilities", []):
        value = item.get("values_by_level", {}).get(level_key)
        if value is None:
            continue
        occurrence_id = str(item["occurrence_id"])
        label_id = str(item.get("label_id", occurrence_id))
        mechanism = item.get("mechanism")
        parameters = dict(item.get("effect_parameters", {}))
        semantic = (semantic_entries or {}).get(f"label:{label_id}", {})
        program = _semantic_program(semantic, semantic_patterns or {}) if isinstance(semantic, Mapping) else None
        if not mechanism and isinstance(semantic, Mapping) and semantic.get("mechanic_id") and program is not None:
            level_value = _official_level_scalar(value) if isinstance(value, Mapping) else None
            level_components = _official_level_components(value) if isinstance(value, Mapping) else {}
            if level_value is not None or level_components:
                mechanism = str(semantic["mechanic_id"])
                parameters = {
                    "program": program,
                    "source_club_id": str(club_data["id"]),
                    "ability_level": level,
                    "level_components": level_components,
                }
                if level_value is not None:
                    parameters["level_value"] = level_value
        if not mechanism:
            mechanism = f"unsupported:{label_id}"
        effect = Effect(
            mechanism=str(mechanism),
            parameters=dict(parameters),
            condition=Condition("always", description="semantic condition not available in official catalog"),
            source=f"{club_data['name']} / {occurrence_id}",
        )
        abilities.append(Ability(identifier=occurrence_id, text=label_id, effects=(effect,)))
    return tuple(abilities)


def build_game_state(
    saved_bag: SavedBag,
    catalog_path: str | Path,
    level: int | str | Mapping[str, int | str],
    current_club_id: str | None = None,
) -> GameState:
    catalog = load_raw_json(catalog_path)
    clubs_data = catalog.get("clubs") if isinstance(catalog, dict) else None
    if not isinstance(clubs_data, dict):
        raise BagEvaluationError("Official catalog clubs must be keyed by stable identifier")
    semantic_path = Path(catalog_path).with_name("semantic_map.json")
    semantic_data = load_raw_json(semantic_path) if semantic_path.exists() else {}
    semantic_entries = semantic_data.get("entries", {}) if isinstance(semantic_data, Mapping) else {}
    semantic_patterns = semantic_data.get("patterns", {}) if isinstance(semantic_data, Mapping) else {}
    current_id = current_club_id or saved_bag.club_ids[0]
    if current_id not in saved_bag.club_ids:
        raise BagEvaluationError(f"Current club {current_id!r} is not in bag {saved_bag.identifier!r}")

    entries = []
    for club_id in saved_bag.club_ids:
        try:
            data = clubs_data[club_id]
        except KeyError as exc:
            raise BagEvaluationError(f"Unknown official club reference: {club_id}") from exc
        club_level = level.get(club_id) if isinstance(level, Mapping) else level
        if club_level is None:
            raise BagEvaluationError(f"No level provided for club {club_id!r}")
        stats = _stats_by_level(data)
        if club_id == current_id and club_level not in stats:
            raise BagEvaluationError(f"No official stats for {club_id} at level {club_level}")
        club = Club(
            identifier=club_id,
            name=str(data["name"]),
            brand=str(data["brand"]["id"]),
            club_type=str(data["club_type"]["id"]),
            stats_by_level=stats,
            abilities=_abilities_at_level(data, club_level, semantic_entries, semantic_patterns),
            rarity=str(data["rarity"]["id"]),
        )
        entries.append(BagEntry(club=club, level=club_level))
    return GameState(bag=Bag(tuple(entries)), current_club_id=current_id)


def evaluate_bag(
    saved_bag: SavedBag,
    *,
    level: int | str | Mapping[str, int | str],
    mode: EvaluationMode,
    catalog_path: str | Path = "data/normalized/clubs_official.json",
    current_club_id: str | None = None,
    engine: RuleEngine | None = None,
) -> BagEvaluation:
    """Evaluate any ordered bag description, including generated candidates."""
    state = build_game_state(saved_bag, catalog_path, level, current_club_id)
    rule_engine = engine or RuleEngine()
    effects = [effect for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects]
    strict_failed = False
    try:
        result = rule_engine.evaluate(state, effects, mode=mode)
    except EvaluationError as exc:
        if exc.result is None:
            raise
        result = exc.result
        strict_failed = True
    return BagEvaluation(saved_bag, state, result, mode, strict_failed, rule_engine.mechanisms.names)


def evaluate_saved_bag(
    bag_id: str,
    *,
    level: int | str,
    mode: EvaluationMode,
    user_dir: str | Path = "data/user",
    catalog_path: str | Path = "data/normalized/clubs_official.json",
    current_club_id: str | None = None,
    engine: RuleEngine | None = None,
) -> BagEvaluation:
    saved_bag = load_saved_bag(user_dir, bag_id)
    return evaluate_bag(
        saved_bag,
        level=level,
        mode=mode,
        catalog_path=catalog_path,
        current_club_id=current_club_id,
        engine=engine,
    )


def render_bag_evaluation(evaluation: BagEvaluation) -> str:
    result = evaluation.result
    current = evaluation.state.current_entry.club
    lines = [
        "=" * 60,
        current.name,
        f"Bag: {evaluation.bag.name}",
        f"Level scenario: {evaluation.state.current_entry.level}",
        "",
        "Base stats",
        f"Power ..... {result.base_stats.power:g}",
        f"Control ... {result.base_stats.control:g}",
        f"Spin ...... {result.base_stats.spin:g}",
    ]
    for entry in result.explain:
        lines.extend(
            [
                "-" * 60,
                f"Ability: {entry.source}",
                f"Condition: {entry.condition}",
                f"Status: {'APPLIED' if entry.applied else 'UNSUPPORTED' if entry.message.startswith('Unresolved') else 'SKIPPED'}",
                f"Effect: {entry.mechanism}",
                f"Inputs: {dict(entry.inputs)}" if entry.inputs else "Inputs: {}",
                f"Outputs: {dict(entry.outputs)}" if entry.outputs else "Outputs: {}",
                f"Before: {dict(entry.before)}",
                f"Change: {dict(entry.modification)}",
                f"After: {dict(entry.after)}",
            ]
        )
        if entry.message:
            lines.append(f"Reason: {entry.message}")
    applied = sum(entry.applied for entry in result.explain)
    lines.extend(
        [
            "-" * 60,
            "Evaluation finished",
            f"Final stats: {result.final_stats.as_dict()}",
            f"Supported mechanics: {len(evaluation.supported_mechanics)} ({', '.join(evaluation.supported_mechanics)})",
            f"Applied effects: {applied}",
            f"Unsupported effects: {len(result.unresolved)}",
            f"Strict mode: {'FAILED' if evaluation.strict_failed else 'NOT REQUESTED' if evaluation.mode is EvaluationMode.PARTIAL else 'SUCCESS'}",
            f"Partial mode: {'SUCCESS' if evaluation.mode is EvaluationMode.PARTIAL else 'NOT REQUESTED'}",
            "=" * 60,
        ]
    )
    return "\n".join(lines)
