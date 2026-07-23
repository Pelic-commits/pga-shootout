"""Operational inventory audit derived from official, semantic and user data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .bag_evaluation import _semantic_program
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
        "history_required",
        "physics_required",
        "qualified_not_implemented",
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
    known_user_levels: int
    official_abilities: int
    simulated_abilities: int
    unresolved_abilities: int
    fully_simulated_clubs: int
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


def _unqualified_family(label_id: str, text: str) -> str:
    normalized = f"{label_id} {text}".casefold()
    if any(term in normalized for term in ("chains into", "next shot")):
        return "chain_next_shot"
    if "previous shot" in normalized or "perfect shot" in normalized:
        return "previous_shot_condition"
    if "wind" in normalized:
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
    if "wind" in normalized:
        return (
            "scenario_required",
            "The ability needs wind context; its static descriptor and stacking policy are not yet qualified.",
            ("wind_speed", "stacking_validation"),
        )
    if any(term in normalized for term in ("fairway", "rough", "bunker", "water", "tee box", "terrain bonus")):
        return (
            "scenario_required",
            "The ability requires an explicit terrain scenario that is absent from the static comparator.",
            ("terrain",),
        )
    return (
        "ambiguous",
        "The normalized group has no validated semantic interpretation.",
        ("semantic_qualification",),
    )


def _technical_family(semantic: Mapping[str, Any], label_id: str, text: str) -> str:
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


def _roadmap_lots(clubs: tuple[InventoryClubStatus, ...]) -> tuple[DevelopmentLot, ...]:
    candidates = (
        (
            "static_modifiers",
            "Qualify owned-club static modifiers",
            {"static_bounce_modifier", "static_shot_control_modifier"},
            "medium",
            ("metric and stacking validation",),
            "Adds deterministic comparison metrics using the existing target-selection and modifier pipeline.",
        ),
        (
            "wind_resistance",
            "Expose wind resistance as an objective modifier",
            {"wind_resistance"},
            "medium",
            ("scope validation", "stacking validation"),
            "Improves owned par-3 clubs without requiring a full wind simulation for the static descriptor.",
        ),
        (
            "chains",
            "Implement next-shot chains",
            {"chain_next_shot"},
            "medium-high",
            ("history trigger validation", "duration and consumption validation"),
            "Covers the largest remaining owned-club cluster after deterministic static modifiers.",
        ),
        (
            "terrain_conditions",
            "Implement simple terrain conditions",
            {"terrain_condition"},
            "medium-high",
            ("optional terrain context", "official condition validation"),
            "Adds the next reusable scenario contract after the static comparator patterns.",
        ),
        (
            "trajectory_physics",
            "Qualify deterministic trajectory modifiers",
            {"trajectory_physics"},
            "high",
            ("validated physics contract", "in-game measurements"),
            "Covers the remaining owned deterministic trajectory abilities once their physical meaning is validated.",
        ),
    )
    result: list[DevelopmentLot] = []
    for identifier, title, families, difficulty, requirements, reason in candidates:
        selected = [
            (club, ability)
            for club in clubs
            for ability in club.abilities
            if not ability.engine_supported and ability.technical_family in families
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
    raw_by_name = _club_records(raw)
    handler_names = set(default_mechanism_registry().names)
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
            mechanic_id = semantic.get("mechanic_id")
            supported = isinstance(mechanic_id, str) and mechanic_id in handler_names
            program = _semantic_program(semantic, patterns) if supported else None
            metrics = _program_metrics(program, semantic)
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
                    technical_family=_technical_family(semantic, label_id, official_text),
                    saved_bag_ids=saved_bags,
                )
            )

        simulated = sum(item.engine_supported for item in abilities)
        fully_simulated = bool(abilities) and simulated == len(abilities)
        compare_usability = _club_usability(simulated, len(abilities))
        optimizer_usability = "yes" if fully_simulated and inventory_entry.current_level is not None else "partially"
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
                abilities=tuple(abilities),
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
        known_user_levels=sum(club.current_level is not None for club in clubs),
        official_abilities=len(all_abilities),
        simulated_abilities=sum(ability.engine_supported for ability in all_abilities),
        unresolved_abilities=sum(not ability.engine_supported for ability in all_abilities),
        fully_simulated_clubs=sum(club.fully_simulated for club in clubs),
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
        f"Engine coverage: {report.simulated_abilities}/{report.official_abilities} abilities ({report.inventory_coverage_percent:.2f}%)",
        f"Fully simulated clubs: {report.fully_simulated_clubs}/{report.inventory_clubs}",
        f"Known user levels: {report.known_user_levels}/{report.inventory_clubs}",
        "",
        "Clubs",
    ]
    for club in report.clubs:
        level = club.current_level if club.current_level is not None else "unknown"
        lines.append(
            f"- {club.name} [{club.brand} / {club.club_type} / {club.rarity}] "
            f"level={level}; abilities={club.simulated_abilities}/{club.official_abilities}; "
            f"compare-bags={club.compare_bags_usability}; optimizer={club.static_optimizer_usability}"
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
            + (", ".join(club.name for club in report.clubs if club.fully_simulated) or "none"),
        ]
    )
    return "\n".join(lines)


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_inventory_markdown(report: InventoryStatusReport) -> str:
    lines = [
        "# User Inventory Status",
        "",
        "> Generated from official, normalized, engine-registry and user data by `pga-shootout inventory-status --write-reports`.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Known inventory clubs | {report.inventory_clubs} |",
        f"| Inventory declared complete | {'yes' if report.inventory_complete else 'no'} |",
        f"| Known user levels | {report.known_user_levels}/{report.inventory_clubs} |",
        f"| Official owned-club abilities | {report.official_abilities} |",
        f"| Engine-supported owned-club abilities | {report.simulated_abilities} |",
        f"| Unresolved owned-club abilities | {report.unresolved_abilities} |",
        f"| Owned-ability coverage | {report.inventory_coverage_percent:.2f}% |",
        f"| Fully simulated owned clubs | {report.fully_simulated_clubs}/{report.inventory_clubs} |",
        "",
        "## Clubs",
        "",
        "| Club | Brand | Type | Rarity | User level | Abilities | Fully simulated | compare-bags | Static optimizer |",
        "|---|---|---|---|---:|---:|---|---|---|",
    ]
    for club in report.clubs:
        level = str(club.current_level) if club.current_level is not None else "unknown"
        lines.append(
            f"| {club.name} (`{club.club_id}`) | {club.brand} | {club.club_type} | {club.rarity} | {level} | "
            f"{club.simulated_abilities}/{club.official_abilities} | {'yes' if club.fully_simulated else 'no'} | "
            f"{club.compare_bags_usability} | {club.static_optimizer_usability} |"
        )
    for club in report.clubs:
        lines.extend(
            [
                "",
                f"### {club.name}",
                "",
                "| Official ability | Official text | Activates | Status | Metrics | Reason | Needed | Technical family |",
                "|---|---|---:|---|---|---|---|---|",
            ]
        )
        for ability in club.abilities:
            lines.append(
                f"| {ability.official_name} (`{ability.occurrence_id}`) | {_markdown_escape(ability.official_text)} | "
                f"{ability.activation_level or 'unknown'} | `{ability.status}` | "
                f"{', '.join(f'`{metric}`' for metric in ability.metrics) or 'none'} | {_markdown_escape(ability.reason)} | "
                f"{', '.join(f'`{item}`' for item in ability.required_data) or 'none'} | `{ability.technical_family}` |"
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
    lines.extend(["", "## Recommended next lots", ""])
    for index, lot in enumerate(report.next_lots, start=1):
        lines.extend(
            [
                f"### {index}. {lot.title}",
                "",
                f"- Abilities: {', '.join(lot.ability_names) or 'none'}.",
                f"- Owned clubs: {', '.join(lot.club_names) or 'none'}.",
                f"- Expected ability coverage gain: +{lot.expected_ability_gain}.",
                f"- Clubs becoming fully simulated: {', '.join(lot.clubs_becoming_fully_simulated) or 'none'}.",
                f"- Difficulty: {lot.difficulty}.",
                f"- Required: {', '.join(lot.requirements)}.",
                f"- Priority: {lot.priority_reason}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_project_status_markdown(report: InventoryStatusReport) -> str:
    comparable = [club.name for club in report.clubs if club.fully_simulated]
    lines = [
        "# Project Status",
        "",
        "> Generated from the same audit as `pga-shootout inventory-status`; no totals are maintained here manually.",
        "",
        "## What the tool does today",
        "",
        "- Loads official club statistics, user inventory and saved bags.",
        "- Evaluates supported deterministic bag abilities in strict or partial mode.",
        "- Compares bags metric by metric with attributed contributions and a factual completeness diagnostic.",
        f"- Supports {report.simulated_abilities}/{report.official_abilities} owned-club abilities ({report.inventory_coverage_percent:.2f}%).",
        "",
        "## What it does not do",
        "",
        "- It does not rank bags or compute an aggregate user-value score.",
        "- It does not simulate full trajectory physics, terrain history, random transformations or Meteor's abilities.",
        "- It cannot reproduce Pierre's real club values until their current levels are recorded.",
        "",
        "## Inventory",
        "",
        f"- Known clubs: {report.inventory_clubs}; inventory complete: {'yes' if report.inventory_complete else 'no'}.",
        f"- Fully simulated clubs: {report.fully_simulated_clubs}/{report.inventory_clubs}.",
        f"- Fully comparable by engine coverage: {', '.join(comparable) or 'none'}.",
        f"- Known current levels: {report.known_user_levels}/{report.inventory_clubs}.",
        "",
        "## compare-bags",
        "",
        "Operational for explicit level scenarios. It exposes Power, Control, Spin, qualified static modifiers, ability contributions, unresolved abilities and completeness facts. Saved reference bags are regression fixtures, not product priorities.",
        "",
        "## Optimizer",
        "",
        "The evaluator API exists, but candidate generation, inventory enforcement, normalization, validated weights, multi-club aggregation and ranking are incomplete or missing. No automatic best-bag recommendation is currently produced.",
        "",
        "## Meteor",
        "",
        "Meteor remains a future, experimentally blocked subject. Alien Relic and Alien World are not implemented and are not among the next three owned-inventory lots.",
        "",
        "## Next three development lots",
        "",
    ]
    for index, lot in enumerate(report.next_lots, start=1):
        lines.append(
            f"{index}. **{lot.title}** — {', '.join(lot.club_names)}; +{lot.expected_ability_gain} owned abilities; "
            f"difficulty {lot.difficulty}; requires {', '.join(lot.requirements)}."
        )
    lines.extend(
        [
            "",
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
