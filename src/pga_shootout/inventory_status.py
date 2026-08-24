"""Operational inventory audit derived from official, semantic and user data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .bag_evaluation import _semantic_effect_specs, semantic_support
from .coverage import analyze_coverage
from .loader import load_raw_json
from .reference_gap_report import analyze_reference_gaps
from .registry import default_mechanism_registry
from .user_data import load_user_data
from .user_gap_report import _club_records, _official_texts


ABILITY_STATUSES = frozenset(
    {
        "simulated",
        "simulated_no_effect_in_current_bag",
        "missing_user_level",
        "ambiguous",
        "scenario_required",
        "simple_context_required",
        "history_required",
        "physics_required",
        "qualified_not_implemented",
        "partial",
        "unsupported",
    }
)


@dataclass(frozen=True)
class InventoryAbilityStatus:
    occurrence_id: str
    official_name: str
    official_text: str
    activation_level: str | None
    status: str
    engine_supported: bool
    metrics: tuple[str, ...]
    reason: str
    required_data: tuple[str, ...]
    technical_family: str
    saved_bag_ids: tuple[str, ...]
    behavior_id: str
    importance: str
    reusable_primitives: tuple[str, ...]
    required_primitive: str | None
    similar_occurrence_ids: tuple[str, ...]
    qualification_category: str
    validation_experiment: str | None


@dataclass(frozen=True)
class InventoryClubStatus:
    club_id: str
    name: str
    brand: str
    club_type: str
    rarity: str
    current_level: int | None
    official_abilities: int
    simulated_abilities: int
    fully_simulated: bool
    compare_bags_usability: str
    static_optimizer_usability: str
    comparison_eligibility: str
    eligibility_reasons: tuple[str, ...]
    optimizer_eligibility: str
    optimizer_eligibility_reasons: tuple[str, ...]
    abilities: tuple[InventoryAbilityStatus, ...]


@dataclass(frozen=True)
class ReferenceBagStatus:
    bag_id: str
    simulated_abilities: int
    official_abilities: int

    @property
    def coverage_percent(self) -> float:
        if not self.official_abilities:
            return 100.0
        return round(100 * self.simulated_abilities / self.official_abilities, 2)


@dataclass(frozen=True)
class DevelopmentLot:
    identifier: str
    title: str
    ability_names: tuple[str, ...]
    club_ids: tuple[str, ...]
    club_names: tuple[str, ...]
    expected_ability_gain: int
    clubs_becoming_fully_simulated: tuple[str, ...]
    difficulty: str
    requirements: tuple[str, ...]
    priority_reason: str


@dataclass(frozen=True)
class InventoryStatusReport:
    inventory_complete: bool
    inventory_clubs: int
    baseline_inventory_clubs: int
    newly_added_club_names: tuple[str, ...]
    known_user_levels: int
    official_abilities: int
    simulated_abilities: int
    unresolved_abilities: int
    fully_simulated_clubs: int
    fully_comparable_clubs: int
    warning_comparable_clubs: int
    non_comparable_clubs: int
    fully_optimizable_clubs: int
    context_optimizable_clubs: int
    warning_optimizable_clubs: int
    non_optimizable_clubs: int
    global_groups: int
    global_simulated_groups: int
    global_abilities: int
    global_simulated_abilities: int
    global_clubs: int
    global_simulated_clubs: int
    clubs: tuple[InventoryClubStatus, ...]
    reference_bags: tuple[ReferenceBagStatus, ...]
    next_lots: tuple[DevelopmentLot, ...]

    @property
    def inventory_coverage_percent(self) -> float:
        if not self.official_abilities:
            return 100.0
        return round(100 * self.simulated_abilities / self.official_abilities, 2)

    @property
    def global_coverage_percent(self) -> float:
        if not self.global_abilities:
            return 100.0
        return round(100 * self.global_simulated_abilities / self.global_abilities, 2)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["inventory_coverage_percent"] = self.inventory_coverage_percent
        value["global_coverage_percent"] = self.global_coverage_percent
        value["reference_bags"] = [
            {**asdict(item), "coverage_percent": item.coverage_percent}
            for item in self.reference_bags
        ]
        return value


def _activation_level(ability: Mapping[str, Any], level_order: list[str]) -> str | None:
    values = ability.get("values_by_level", {})
    if not isinstance(values, Mapping):
        return None
    return next((level for level in level_order if values.get(level) is not None), None)


def _program_metrics(program: Mapping[str, Any] | None, semantic: Mapping[str, Any]) -> tuple[str, ...]:
    metrics: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            operation = value.get("operation")
            parameters = value.get("parameters")
            if operation == "ADD_STAT" and isinstance(parameters, Mapping):
                stat = parameters.get("stat")
                if isinstance(stat, str):
                    metrics.add(stat)
            if operation == "ADD_MODIFIER" and isinstance(parameters, Mapping):
                modifier = parameters.get("modifier")
                if isinstance(modifier, str):
                    metrics.add(modifier)
            if operation == "SCHEDULE_EFFECT" and isinstance(parameters, Mapping):
                if parameters.get("effect_mechanism") == "add_all_stats":
                    metrics.update(("power", "control", "spin"))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(program)
    parameters = semantic.get("pattern_parameters")
    if isinstance(parameters, Mapping):
        for key in ("stat", "modifier", "penalty_stat"):
            value = parameters.get(key)
            if isinstance(value, str):
                metrics.add(value)
        for key in ("stats", "bonus_stats"):
            value = parameters.get(key)
            if isinstance(value, list):
                metrics.update(str(item) for item in value)
    return tuple(sorted(metrics))


def _program_operations(program: Mapping[str, Any] | None) -> tuple[str, ...]:
    operations: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            operation = value.get("operation")
            if isinstance(operation, str) and operation not in operations:
                operations.append(operation)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(program)
    return tuple(operations)


def _potential_metrics(program_metrics: tuple[str, ...], label_id: str, text: str) -> tuple[str, ...]:
    if program_metrics:
        return program_metrics
    normalized = f"{label_id} {text}".casefold()
    candidates = (
        ("power", "power"),
        ("control", "control"),
        ("spin", "spin"),
        ("loft", "loft_angle_degrees"),
        ("wind resist", "wind_resistance_percent"),
        ("bounce", "bounce_reduction_percent"),
        ("groundspin", "groundspin_multiplier"),
        ("gravity", "gravity_reduction_percent"),
        ("aim arrow", "aim_arrow_speed_multiplier"),
        ("fade", "fade_multiplier"),
        ("draw", "draw_multiplier"),
        ("range", "range"),
    )
    return tuple(metric for token, metric in candidates if token in normalized)


def _importance(metrics: tuple[str, ...], family: str, text: str) -> str:
    if any(metric in {"power", "control", "spin"} for metric in metrics):
        return "high"
    if any(token in family for token in ("bag", "adjacent", "brand", "type")):
        return "high"
    if metrics or any(token in text.casefold() for token in ("tee", "fairway", "rough", "wind")):
        return "medium"
    return "low"


def _primitive_profile(family: str, program: Mapping[str, Any] | None) -> tuple[tuple[str, ...], str | None]:
    operations = _program_operations(program)
    if operations:
        return operations, None
    if family == "chain_next_shot":
        return ("SELECT_SELF", "READ_LEVEL_VALUE", "SCHEDULE_EFFECT"), None
    if family in {"terrain_condition", "tee_self_power_bonus"}:
        return ("SELECT_SELF", "READ_LEVEL_VALUE", "ADD_STAT"), "READ_CONTEXT"
    if family == "wind_resistance":
        return ("SELECT_SELF", "READ_LEVEL_VALUE", "ADD_MODIFIER"), "READ_CONTEXT"
    if family == "terrain_proximity_bonus":
        return ("SELECT_SELF", "READ_LEVEL_VALUE", "ADD_STAT"), "READ_CONTEXT"
    if family == "trajectory_physics":
        return (), "validated_physics_effect"
    return (), "semantic_qualification"


def _context_requirements(semantic: Mapping[str, Any]) -> tuple[str, ...]:
    requirements: list[str] = []
    for spec in _semantic_effect_specs(semantic):
        condition = spec.get("condition")
        if not isinstance(condition, Mapping):
            continue
        parameters = condition.get("parameters")
        if not isinstance(parameters, Mapping) or not parameters.get("required"):
            continue
        field = parameters.get("field")
        if isinstance(field, str) and field not in requirements:
            requirements.append(field)
    return tuple(requirements)


def _unqualified_family(label_id: str, text: str) -> str:
    normalized = f"{label_id} {text}".casefold()
    if any(term in normalized for term in ("chains into", "next shot")):
        return "chain_next_shot"
    if "previous shot" in normalized or "perfect shot" in normalized:
        return "previous_shot_condition"
    if ("from the tee" in normalized or "hitting from the tee" in normalized) and "loft" in normalized:
        return "compound_tee_power_and_loft"
    if "from the tee" in normalized or "hitting from the tee" in normalized:
        return "tee_self_power_bonus"
    if re.search(r"\bwind(?:\s|_|-)", normalized) or "wind resistance" in normalized:
        return "wind_resistance"
    if "fade" in normalized or "draw" in normalized:
        return "static_shot_control_modifier"
    if "bounce reduction" in normalized or "less bounce" in normalized:
        return "static_bounce_modifier"
    if "tree" in normalized and any(term in normalized for term in ("within", "depending", "close")):
        return "terrain_proximity_bonus"
    if any(term in normalized for term in ("extra range", "swing timing", "faster and farther", "travels 75%")):
        return "trajectory_physics"
    if any(term in normalized for term in ("fairway", "rough", "bunker", "water", "tee box", "terrain bonus")):
        return "terrain_condition"
    return f"unqualified:{label_id}"


def _unimplemented_status(semantic: Mapping[str, Any], label_id: str, text: str) -> tuple[str, str, tuple[str, ...]]:
    qualification = semantic.get("qualification")
    if isinstance(qualification, Mapping):
        status = str(qualification.get("status", "ambiguous"))
        reason = str(qualification.get("reason", "No qualification reason was recorded."))
        required = qualification.get("required_data", ())
        if not isinstance(required, list):
            required = []
        return status, reason, tuple(str(item) for item in required)
    validation = str(semantic.get("validation_status", "not_started"))
    if validation not in ("", "not_started"):
        return (
            "qualified_not_implemented",
            "The official behavior is qualified, but no registered handler executes it.",
            ("handler",),
        )
    normalized = f"{label_id} {text}".casefold()
    if re.search(r"\b(random|randomly|transform|swap|replace)\w*\b", normalized):
        return (
            "unsupported",
            "The ability requires a random or transformational capability outside the current engine.",
            ("engine_capability",),
        )
    if any(term in normalized for term in ("chains into", "next shot", "previous shot", "perfect shot")):
        return (
            "history_required",
            "The ability depends on a previous or future shot and the history scheduler is not implemented.",
            ("shot_history", "trigger_and_consumption_validation"),
        )
    if any(term in normalized for term in ("extra range", "swing timing", "faster and farther", "travels 75%")):
        return (
            "physics_required",
            "The official effect changes trajectory, range or timing and needs a validated physics contract.",
            ("physics_contract", "in_game_validation"),
        )
    if "tree" in normalized and any(term in normalized for term in ("within", "depending", "up to")):
        return (
            "ambiguous",
            "The distance-to-tree formula behind the official 'up to' value is not specified.",
            ("in_game_validation", "terrain_proximity"),
        )
    if "fade" in normalized or "draw" in normalized:
        return (
            "ambiguous",
            "The fade/draw base metric and multiplication/stacking rule are not qualified.",
            ("metric_contract", "stacking_validation"),
        )
    if "less bounce" in normalized and "x%" not in normalized:
        return (
            "ambiguous",
            "The text omits the numeric placeholder and the bounce stacking rule is not qualified.",
            ("official_text_table_validation", "stacking_validation"),
        )
    if re.search(r"\bwind(?:\s|_|-)", normalized) or "wind resistance" in normalized:
        return (
            "simple_context_required",
            "The ability needs wind context; its static descriptor and stacking policy are not yet qualified.",
            ("wind_speed", "stacking_validation"),
        )
    if any(term in normalized for term in ("fairway", "rough", "bunker", "water", "tee box", "terrain bonus")):
        return (
            "simple_context_required",
            "The ability requires an explicit terrain scenario that is absent from the static comparator.",
            ("terrain",),
        )
    return (
        "ambiguous",
        "The normalized group has no validated semantic interpretation.",
        ("semantic_qualification",),
    )


def _technical_family(semantic: Mapping[str, Any], label_id: str, text: str) -> str:
    behavior = semantic.get("behavior_id")
    if isinstance(behavior, str):
        return behavior
    pattern = semantic.get("pattern_id")
    if isinstance(pattern, str):
        return pattern
    if semantic.get("mechanic_id"):
        return "dsl_pipeline"
    return _unqualified_family(label_id, text)


def _club_usability(simulated: int, total: int) -> str:
    if total and simulated == total:
        return "yes"
    if simulated or total:
        return "partially"
    return "no"


def _club_eligibility(
    current_level: int | None,
    abilities: tuple[InventoryAbilityStatus, ...],
) -> tuple[str, tuple[str, ...]]:
    if current_level is None:
        return "not_comparable", ("missing_user_level",)
    unresolved = tuple(item for item in abilities if not item.engine_supported)
    contexts = tuple(
        item for item in abilities if item.engine_supported and item.status == "simple_context_required"
    )
    if unresolved:
        reasons = tuple(dict.fromkeys(f"{item.occurrence_id}:{item.status}" for item in unresolved))
        if not any(item.engine_supported for item in abilities):
            return "not_comparable", reasons
        return "comparable_with_warning", reasons
    if contexts:
        return "comparable_with_warning", tuple(
            f"{item.occurrence_id}:context:{','.join(item.required_data)}" for item in contexts
        )
    return "fully_comparable", ()


def _optimizer_eligibility(
    current_level: int | None,
    abilities: tuple[InventoryAbilityStatus, ...],
) -> tuple[str, tuple[str, ...]]:
    if current_level is None:
        return "not_optimizable", ("missing_user_level",)
    unresolved = tuple(item for item in abilities if not item.engine_supported)
    contexts = tuple(item for item in abilities if item.engine_supported and item.required_data)
    if unresolved:
        reasons = tuple(dict.fromkeys(f"{item.occurrence_id}:{item.status}" for item in unresolved))
        if not any(item.engine_supported for item in abilities):
            return "not_optimizable", reasons
        return "optimizable_with_warning", reasons
    if contexts:
        return "optimizable_with_context", tuple(
            f"{item.occurrence_id}:context:{','.join(item.required_data)}" for item in contexts
        )
    return "fully_optimizable", ()


def _roadmap_lots(clubs: tuple[InventoryClubStatus, ...]) -> tuple[DevelopmentLot, ...]:
    candidates = (
        (
            "official_data_conflicts",
            "Resolve official text/table conflicts",
            {"official_text_table_conflict"},
            "validation",
            ("in-game value capture", "official source reconciliation"),
            "Removes blockers where the engine deliberately refuses to choose between contradictory official values.",
        ),
        (
            "semantic_dependencies",
            "Validate dependency and stacking semantics",
            {"true_semantic_ambiguity"},
            "validation",
            ("minimal in-game comparison", "stacking or provenance decision"),
            "Qualifies base-versus-final copying, cross-ability dependencies and stacking without guessing.",
        ),
        (
            "geometry_physics",
            "Measure geometry and trajectory effects",
            {"geometry_or_trajectory_required"},
            "experimental-high",
            ("validated physics contract", "in-game measurements"),
            "Covers proximity, collision, timing and speed/distance effects only after measurable contracts exist.",
        ),
    )
    result: list[DevelopmentLot] = []
    for identifier, title, categories, difficulty, requirements, reason in candidates:
        selected = [
            (club, ability)
            for club in clubs
            for ability in club.abilities
            if not ability.engine_supported and ability.qualification_category in categories
        ]
        selected_ids = {ability.occurrence_id for _, ability in selected}
        club_ids = tuple(dict.fromkeys(club.club_id for club, _ in selected))
        club_names = tuple(dict.fromkeys(club.name for club, _ in selected))
        becoming_full = tuple(
            club.name
            for club in clubs
            if any(candidate_id == club.club_id for candidate_id in club_ids)
            and all(ability.engine_supported or ability.occurrence_id in selected_ids for ability in club.abilities)
        )
        if not selected_ids:
            continue
        result.append(
            DevelopmentLot(
                identifier=identifier,
                title=title,
                ability_names=tuple(dict.fromkeys(ability.official_name for _, ability in selected)),
                club_ids=club_ids,
                club_names=club_names,
                expected_ability_gain=len(selected_ids),
                clubs_becoming_fully_simulated=becoming_full,
                difficulty=difficulty,
                requirements=requirements,
                priority_reason=reason,
            )
        )
    return tuple(result[:3])


def analyze_inventory_status(
    *,
    user_dir: str | Path = "data/user",
    normalized_dir: str | Path = "data/normalized",
    raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
) -> InventoryStatusReport:
    normalized_root = Path(normalized_dir)
    catalog = load_raw_json(normalized_root / "clubs_official.json")
    semantic_map = load_raw_json(normalized_root / "semantic_map.json")
    raw = load_raw_json(raw_catalog_path)
    clubs_data = catalog.get("clubs") if isinstance(catalog, Mapping) else None
    semantics = semantic_map.get("entries") if isinstance(semantic_map, Mapping) else None
    patterns = semantic_map.get("patterns") if isinstance(semantic_map, Mapping) else None
    if not isinstance(clubs_data, Mapping) or not isinstance(semantics, Mapping) or not isinstance(patterns, Mapping):
        raise ValueError("Normalized clubs and semantic map are required")

    bundle = load_user_data(user_dir)
    baseline_ids: set[str] = set()
    user_path = Path(user_dir)
    if user_path.is_file():
        legacy_dir = user_path.parent / "user"
        if (legacy_dir / "inventory.json").exists():
            baseline_ids = {entry.club_id for entry in load_user_data(legacy_dir).inventory.entries}
    raw_by_name = _club_records(raw)
    handler_names = set(default_mechanism_registry().names)
    behavior_occurrences: dict[str, list[str]] = {}
    for catalog_club in clubs_data.values():
        if not isinstance(catalog_club, Mapping):
            continue
        raw_club = raw_by_name[str(catalog_club["name"])]
        texts = _official_texts(raw_club)
        labels = [str(row[0]) for row in raw_club["tables"][0]["rows"][4:]]
        for index, ability in enumerate(catalog_club.get("abilities", [])):
            label_id = str(ability["label_id"])
            semantic = semantics[f"label:{label_id}"]
            behavior = _technical_family(semantic, label_id, texts.get(labels[index], ""))
            behavior_occurrences.setdefault(behavior, []).append(str(ability["occurrence_id"]))
    bag_ids_by_club: dict[str, list[str]] = {}
    for bag in bundle.bags:
        for club_id in bag.club_ids:
            bag_ids_by_club.setdefault(club_id, []).append(bag.identifier)

    club_results: list[InventoryClubStatus] = []
    for inventory_entry in bundle.inventory.entries:
        club = clubs_data[inventory_entry.club_id]
        raw_club = raw_by_name[str(club["name"])]
        official_texts = _official_texts(raw_club)
        official_labels = [str(row[0]) for row in raw_club["tables"][0]["rows"][4:]]
        level_order = [str(value) for value in club.get("level_order", [])]
        abilities: list[InventoryAbilityStatus] = []
        for index, ability in enumerate(club.get("abilities", [])):
            label_id = str(ability["label_id"])
            semantic = semantics[f"label:{label_id}"]
            official_name = official_labels[index]
            official_text = official_texts.get(official_name, "")
            effect_specs = _semantic_effect_specs(semantic)
            supported, partially_supported, programs = semantic_support(semantic, patterns, handler_names)
            program = programs[0] if len(programs) == 1 else {"effects": list(programs)}
            family = _technical_family(semantic, label_id, official_text)
            metrics = _potential_metrics(_program_metrics(program, semantic), label_id, official_text)
            primitives, required_primitive = _primitive_profile(family, program)
            context_requirements = _context_requirements(semantic)
            activation_level = _activation_level(ability, level_order)
            saved_bags = tuple(bag_ids_by_club.get(inventory_entry.club_id, ()))

            if supported:
                current_level = inventory_entry.current_level
                values = ability.get("values_by_level", {})
                if current_level is None:
                    status = "missing_user_level"
                    reason = "The engine supports this ability, but the user's current club level is unknown."
                    required = ("current_level",)
                elif not isinstance(values, Mapping) or values.get(str(current_level)) is None:
                    status = "simulated_no_effect_in_current_bag"
                    reason = "The ability is supported but inactive at the user's current level."
                    required = ()
                elif context_requirements:
                    status = "simple_context_required"
                    reason = "The engine supports this ability when its optional scenario context is supplied."
                    required = context_requirements
                elif not saved_bags:
                    status = "simulated_no_effect_in_current_bag"
                    reason = "The ability is supported, but its source club is absent from every saved bag."
                    required = ()
                else:
                    status = "simulated"
                    reason = "The ability has a registered data-driven pipeline and the required user level is known."
                    required = ()
            else:
                status, reason, required = _unimplemented_status(semantic, label_id, official_text)
                if partially_supported and status != "partial":
                    status = "partial"
                    reason = "At least one exact component is simulated; another component remains explicitly unresolved."

            qualification = semantic.get("qualification")
            qualification_category = (
                str(qualification.get("category", "implemented"))
                if isinstance(qualification, Mapping)
                else ("implemented" if supported else "unclassified")
            )
            validation_experiment = (
                str(qualification["experiment"])
                if isinstance(qualification, Mapping) and qualification.get("experiment")
                else None
            )

            abilities.append(
                InventoryAbilityStatus(
                    occurrence_id=str(ability["occurrence_id"]),
                    official_name=official_name,
                    official_text=official_text,
                    activation_level=activation_level,
                    status=status,
                    engine_supported=supported,
                    metrics=metrics,
                    reason=reason,
                    required_data=required,
                    technical_family=family,
                    saved_bag_ids=saved_bags,
                    behavior_id=family,
                    importance=_importance(metrics, family, official_text),
                    reusable_primitives=primitives,
                    required_primitive=required_primitive,
                    similar_occurrence_ids=tuple(behavior_occurrences.get(family, ())),
                    qualification_category=qualification_category,
                    validation_experiment=validation_experiment,
                )
            )

        simulated = sum(item.engine_supported for item in abilities)
        fully_simulated = bool(abilities) and simulated == len(abilities)
        ability_tuple = tuple(abilities)
        eligibility, eligibility_reasons = _club_eligibility(inventory_entry.current_level, ability_tuple)
        optimizer_eligibility, optimizer_reasons = _optimizer_eligibility(inventory_entry.current_level, ability_tuple)
        compare_usability = {
            "fully_comparable": "yes",
            "comparable_with_warning": "partially",
            "not_comparable": "no",
        }[eligibility]
        optimizer_usability = {
            "fully_optimizable": "yes",
            "optimizable_with_context": "with-context",
            "optimizable_with_warning": "with-warning",
            "not_optimizable": "no",
        }[optimizer_eligibility]
        club_results.append(
            InventoryClubStatus(
                club_id=inventory_entry.club_id,
                name=str(club["name"]),
                brand=str(club["brand"]["name"]),
                club_type=str(club["club_type"]["name"]),
                rarity=str(club["rarity"]["name"]),
                current_level=inventory_entry.current_level,
                official_abilities=len(abilities),
                simulated_abilities=simulated,
                fully_simulated=fully_simulated,
                compare_bags_usability=compare_usability,
                static_optimizer_usability=optimizer_usability,
                comparison_eligibility=eligibility,
                eligibility_reasons=eligibility_reasons,
                optimizer_eligibility=optimizer_eligibility,
                optimizer_eligibility_reasons=optimizer_reasons,
                abilities=ability_tuple,
            )
        )

    clubs = tuple(club_results)
    all_abilities = tuple(ability for club in clubs for ability in club.abilities)
    coverage = analyze_coverage(normalized_root)
    global_simulated_occurrences = sum(group.occurrences for group in coverage.groups if group.handler_exists)
    global_simulated_club_ids = {
        club_id for group in coverage.groups if group.handler_exists for club_id in group.club_ids
    }
    reference = analyze_reference_gaps(
        user_dir=user_dir,
        normalized_dir=normalized_root,
        raw_catalog_path=raw_catalog_path,
    )
    reference_bags = tuple(
        ReferenceBagStatus(item.bag_id, item.implemented_occurrences, item.ability_occurrences)
        for item in reference.bag_coverage
    )
    return InventoryStatusReport(
        inventory_complete=bundle.inventory.inventory_complete,
        inventory_clubs=len(clubs),
        baseline_inventory_clubs=len(baseline_ids),
        newly_added_club_names=tuple(club.name for club in clubs if club.club_id not in baseline_ids) if baseline_ids else (),
        known_user_levels=sum(club.current_level is not None for club in clubs),
        official_abilities=len(all_abilities),
        simulated_abilities=sum(ability.engine_supported for ability in all_abilities),
        unresolved_abilities=sum(not ability.engine_supported for ability in all_abilities),
        fully_simulated_clubs=sum(club.fully_simulated for club in clubs),
        fully_comparable_clubs=sum(club.comparison_eligibility == "fully_comparable" for club in clubs),
        warning_comparable_clubs=sum(club.comparison_eligibility == "comparable_with_warning" for club in clubs),
        non_comparable_clubs=sum(club.comparison_eligibility == "not_comparable" for club in clubs),
        fully_optimizable_clubs=sum(club.optimizer_eligibility == "fully_optimizable" for club in clubs),
        context_optimizable_clubs=sum(club.optimizer_eligibility == "optimizable_with_context" for club in clubs),
        warning_optimizable_clubs=sum(club.optimizer_eligibility == "optimizable_with_warning" for club in clubs),
        non_optimizable_clubs=sum(club.optimizer_eligibility == "not_optimizable" for club in clubs),
        global_groups=coverage.total_groups,
        global_simulated_groups=coverage.implemented_groups,
        global_abilities=coverage.total_occurrences,
        global_simulated_abilities=global_simulated_occurrences,
        global_clubs=coverage.total_clubs,
        global_simulated_clubs=len(global_simulated_club_ids),
        clubs=clubs,
        reference_bags=reference_bags,
        next_lots=_roadmap_lots(clubs),
    )


def render_inventory_status(report: InventoryStatusReport) -> str:
    lines = [
        "Inventory status",
        "=" * 72,
        f"Known clubs: {report.inventory_clubs} ({'complete' if report.inventory_complete else 'incomplete inventory'})",
        f"Baseline clubs: {report.baseline_inventory_clubs}; newly added: {len(report.newly_added_club_names)}",
        f"Engine coverage: {report.simulated_abilities}/{report.official_abilities} abilities ({report.inventory_coverage_percent:.2f}%)",
        f"Fully simulated clubs: {report.fully_simulated_clubs}/{report.inventory_clubs}",
        f"Fully comparable clubs: {report.fully_comparable_clubs}/{report.inventory_clubs}",
        f"Comparable with warning: {report.warning_comparable_clubs}/{report.inventory_clubs}",
        f"Not currently comparable: {report.non_comparable_clubs}/{report.inventory_clubs}",
        f"Fully optimizable: {report.fully_optimizable_clubs}/{report.inventory_clubs}",
        f"Optimizable with context: {report.context_optimizable_clubs}/{report.inventory_clubs}",
        f"Optimizable with warning: {report.warning_optimizable_clubs}/{report.inventory_clubs}",
        f"Not optimizable: {report.non_optimizable_clubs}/{report.inventory_clubs}",
        f"Known user levels: {report.known_user_levels}/{report.inventory_clubs}",
        "",
        "Clubs",
    ]
    for club in report.clubs:
        level = club.current_level if club.current_level is not None else "unknown"
        lines.append(
            f"- {club.name} [{club.brand} / {club.club_type} / {club.rarity}] "
            f"level={level}; abilities={club.simulated_abilities}/{club.official_abilities}; "
            f"eligibility={club.comparison_eligibility}; reasons={','.join(club.eligibility_reasons) or 'none'}; "
            f"compare-bags={club.compare_bags_usability}; optimizer={club.optimizer_eligibility}; "
            f"optimizer-reasons={','.join(club.optimizer_eligibility_reasons) or 'none'}"
        )
    lines.extend(["", f"Unresolved engine abilities ({report.unresolved_abilities})"])
    for club in report.clubs:
        for ability in club.abilities:
            if not ability.engine_supported:
                lines.append(
                    f"- {club.name} / {ability.official_name}: {ability.status} — {ability.reason} "
                    f"Needed: {', '.join(ability.required_data)}"
                )
    missing_levels = [club.name for club in report.clubs if club.current_level is None]
    lines.extend(
        [
            "",
            f"Missing user levels ({len(missing_levels)}): " + (", ".join(missing_levels) or "none"),
            "",
            "Fully comparable clubs: "
            + (", ".join(club.name for club in report.clubs if club.comparison_eligibility == "fully_comparable") or "none"),
        ]
    )
    return "\n".join(lines)


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_inventory_markdown(report: InventoryStatusReport) -> str:
    lines = [
        "# User Inventory Status",
        "",
        "> Generated from official, normalized, engine-registry and user data by `pga-shootout inventory-status --write-reports`. This is a factual snapshot, not an active development roadmap.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Known inventory clubs | {report.inventory_clubs} |",
        f"| Baseline inventory clubs | {report.baseline_inventory_clubs} |",
        f"| Clubs added since baseline | {len(report.newly_added_club_names)} |",
        f"| Inventory declared complete | {'yes' if report.inventory_complete else 'no'} |",
        f"| Known user levels | {report.known_user_levels}/{report.inventory_clubs} |",
        f"| Official owned-club abilities | {report.official_abilities} |",
        f"| Engine-supported owned-club abilities | {report.simulated_abilities} |",
        f"| Unresolved owned-club abilities | {report.unresolved_abilities} |",
        f"| Owned-ability coverage | {report.inventory_coverage_percent:.2f}% |",
        f"| Fully simulated owned clubs | {report.fully_simulated_clubs}/{report.inventory_clubs} |",
        f"| Fully comparable owned clubs | {report.fully_comparable_clubs}/{report.inventory_clubs} |",
        f"| Comparable with warning | {report.warning_comparable_clubs}/{report.inventory_clubs} |",
        f"| Not currently comparable | {report.non_comparable_clubs}/{report.inventory_clubs} |",
        f"| Fully optimizable | {report.fully_optimizable_clubs}/{report.inventory_clubs} |",
        f"| Optimizable with context | {report.context_optimizable_clubs}/{report.inventory_clubs} |",
        f"| Optimizable with warning | {report.warning_optimizable_clubs}/{report.inventory_clubs} |",
        f"| Not optimizable | {report.non_optimizable_clubs}/{report.inventory_clubs} |",
        "",
        "## Inventory changes since the retained JSON baseline",
        "",
        f"- Newly added clubs ({len(report.newly_added_club_names)}): {', '.join(report.newly_added_club_names) or 'none'}.",
        "",
        "## Clubs",
        "",
        "| Club | Brand | Type | Rarity | User level | Abilities | Fully simulated | Comparison | Reasons | Optimizer | Optimizer reasons |",
        "|---|---|---|---|---:|---:|---|---|---|---|---|",
    ]
    for club in report.clubs:
        level = str(club.current_level) if club.current_level is not None else "unknown"
        lines.append(
            f"| {club.name} (`{club.club_id}`) | {club.brand} | {club.club_type} | {club.rarity} | {level} | "
            f"{club.simulated_abilities}/{club.official_abilities} | {'yes' if club.fully_simulated else 'no'} | "
            f"`{club.comparison_eligibility}` | {_markdown_escape(', '.join(club.eligibility_reasons) or 'none')} | "
            f"`{club.optimizer_eligibility}` | {_markdown_escape(', '.join(club.optimizer_eligibility_reasons) or 'none')} |"
        )
    for club in report.clubs:
        lines.extend(
            [
                "",
                f"### {club.name}",
                "",
                "| Official ability | Official text | Activates | Status | Classification | Potential metrics/behavior | Importance | Reason | Needed data | Existing primitives | New primitive | Same behavior in catalog | Technical family | Validation experiment |",
                "|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for ability in club.abilities:
            lines.append(
                f"| {ability.official_name} (`{ability.occurrence_id}`) | {_markdown_escape(ability.official_text)} | "
                f"{ability.activation_level or 'unknown'} | `{ability.status}` | `{ability.qualification_category}` | "
                f"{', '.join(f'`{metric}`' for metric in ability.metrics) or 'none'} | `{ability.importance}` | {_markdown_escape(ability.reason)} | "
                f"{', '.join(f'`{item}`' for item in ability.required_data) or 'none'} | "
                f"{', '.join(f'`{item}`' for item in ability.reusable_primitives) or 'none'} | "
                f"{f'`{ability.required_primitive}`' if ability.required_primitive else 'none'} | "
                f"{', '.join(f'`{item}`' for item in ability.similar_occurrence_ids) or 'none'} | "
                f"`{ability.technical_family}` | {_markdown_escape(ability.validation_experiment or 'none')} |"
            )
    lines.extend(["", "## Reference bags (regression only)", "", "| Bag | Supported abilities | Coverage |", "|---|---:|---:|"])
    for bag in report.reference_bags:
        lines.append(
            f"| `{bag.bag_id}` | {bag.simulated_abilities}/{bag.official_abilities} | {bag.coverage_percent:.2f}% |"
        )
    lines.extend(["", "## Missing user data", ""])
    missing = [club.name for club in report.clubs if club.current_level is None]
    lines.append(f"- Current levels: {', '.join(missing) if missing else 'none'}." )
    lines.append(f"- Inventory completeness: {'complete' if report.inventory_complete else 'the inventory is explicitly partial'}." )
    lines.extend(
        [
            "",
            "## Development status",
            "",
            "Functional development is temporarily frozen for real-world use. "
            "The audit still computes candidate lots internally, but this report does not publish them as a roadmap.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_project_status_markdown(report: InventoryStatusReport) -> str:
    comparable = [club.name for club in report.clubs if club.comparison_eligibility == "fully_comparable"]
    lines = [
        "# Project Status",
        "",
        "> Generated from the same factual audit as `pga-shootout inventory-status`; no totals are maintained here manually.",
        "",
        "## What the tool does today",
        "",
        "- Loads official club statistics, user inventory and saved bags.",
        "- Evaluates supported deterministic bag abilities in strict or partial mode.",
        "- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.",
        "- Builds ordered five-club bags from an empty bag and the live inventory, independently of saved bags, with required clubs, metric constraints and allowed brands.",
        f"- Supports {report.simulated_abilities}/{report.official_abilities} owned-club abilities ({report.inventory_coverage_percent:.2f}%).",
        "",
        "## What it does not do",
        "",
        "- It does not compute an aggregate user-value score.",
        "- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.",
        "- It cannot prove real shot distance or a physically successful shot from Power alone.",
        "",
        "## Inventory",
        "",
        f"- Known clubs: {report.inventory_clubs}; inventory complete: {'yes' if report.inventory_complete else 'no'}.",
        f"- Fully simulated clubs: {report.fully_simulated_clubs}/{report.inventory_clubs}.",
        f"- Fully comparable clubs: {report.fully_comparable_clubs}/{report.inventory_clubs}: {', '.join(comparable) or 'none'}.",
        f"- Comparable with warning: {report.warning_comparable_clubs}/{report.inventory_clubs}.",
        f"- Not currently comparable: {report.non_comparable_clubs}/{report.inventory_clubs}.",
        f"- Known current levels: {report.known_user_levels}/{report.inventory_clubs}.",
        "",
        "## compare-bags",
        "",
        "Operational for real inventory levels and explicit scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts without an opaque score.",
        "",
        "## Optimizer",
        "",
        "Operational through the Windows GUI and CLI. Build From Scratch is the primary workflow; saved-bag improvement and replacement remain secondary. Final proposals expose a reason for every slot, preserve meaningful tradeoffs and label bounded searches as MEILLEUR TROUVÉ rather than MAXIMUM PROUVÉ.",
        "",
        "## Meteor",
        "",
        "Meteor remains experimentally blocked. Alien Relic and Alien World are not implemented; no behavior is invented.",
        "",
        "## Current phase",
        "",
        "Current work focuses on real-world validation of the independent Build From Scratch workflow and its readable five-club result cards.",
        "",
    ]
    lines.extend(
        [
            "## Secondary global coverage",
            "",
            f"- Groups: {report.global_simulated_groups}/{report.global_groups}.",
            f"- Ability occurrences: {report.global_simulated_abilities}/{report.global_abilities} ({report.global_coverage_percent:.2f}%).",
            f"- Clubs touched by at least one supported group: {report.global_simulated_clubs}/{report.global_clubs}.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_inventory_reports(
    report: InventoryStatusReport,
    inventory_output: str | Path = "docs/INVENTORY_STATUS.md",
    project_output: str | Path = "docs/PROJECT_STATUS.md",
) -> None:
    inventory_path = Path(inventory_output)
    project_path = Path(project_output)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(render_inventory_markdown(report), encoding="utf-8", newline="\n")
    project_path.write_text(render_project_status_markdown(report), encoding="utf-8", newline="\n")


def render_inventory_json(report: InventoryStatusReport) -> str:
    return json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
