"""Reference-bag ability matrix generated from official, normalized and user data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from .loader import load_raw_json
from .registry import default_mechanism_registry
from .user_data import load_user_data
from .user_gap_report import _club_records, _official_texts


REFERENCE_STATUSES = frozenset({"implemented", "partial", "ambiguous", "scenario_required", "unsupported"})


@dataclass(frozen=True)
class ReferenceAbilityGap:
    club_id: str
    club_name: str
    occurrence_id: str
    official_label: str
    official_text: str
    normalized_pattern: str
    status: str
    required_data: tuple[str, ...]
    confidence: str
    compare_bags_impact: str
    bag_ids: tuple[str, ...]
    user_level: int | None


@dataclass(frozen=True)
class ReferenceBagCoverage:
    bag_id: str
    ability_occurrences: int
    implemented_occurrences: int

    @property
    def coverage_percent(self) -> float:
        return round(100 * self.implemented_occurrences / self.ability_occurrences, 2)


@dataclass(frozen=True)
class ReferenceGapReport:
    unique_clubs: int
    unique_ability_occurrences: int
    abilities: tuple[ReferenceAbilityGap, ...]
    bag_coverage: tuple[ReferenceBagCoverage, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["bag_coverage"] = [
            {**asdict(item), "coverage_percent": item.coverage_percent}
            for item in self.bag_coverage
        ]
        return value


def _status(semantic: Mapping[str, Any], official_text: str, handlers: set[str]) -> str:
    mechanic = semantic.get("mechanic_id")
    if isinstance(mechanic, str) and mechanic in handlers:
        return "implemented"
    if mechanic:
        return "partial"
    text = official_text.casefold()
    if re.search(r"\b(random|randomly|transform|swap|replace)\w*\b", text):
        return "unsupported"
    if re.search(
        r"\b(wind|previous shot|next shot|fairway|rough|bunker|tee box|tree|"
        r"boundary|out of bounds|special ball)\b",
        text,
    ):
        return "scenario_required"
    if re.search(r"\b(pull all the way back|extra range|swing timing)\b", text):
        return "unsupported"
    return "ambiguous"


def _required_data(
    semantic: Mapping[str, Any],
    official_text: str,
    has_level_values: bool,
) -> tuple[str, ...]:
    dependencies = semantic.get("dependencies")
    if isinstance(dependencies, list):
        return tuple(str(value) for value in dependencies)
    text = official_text.casefold()
    required = []
    if has_level_values:
        required.append("ability_level_value")
    if any(term in text for term in ("next shot", "previous shot", "chains into")):
        required.extend(("shot_history", "previous_club"))
    if "wind" in text:
        required.append("wind_speed")
    if any(term in text for term in ("fairway", "rough", "bunker", "tee box", "tree")):
        required.append("terrain")
    if any(term in text for term in ("next to", "left of", "right of", "farthest club", "bag", "clubs")):
        required.append("ordered_bag")
    if any(term in text for term in ("drivers", "woods", "hybrids")):
        required.append("club_type")
    if any(term in text for term in ("bounce", "range", "swing timing", "plasma arc")):
        required.append("static_metric_or_physics_contract")
    return tuple(dict.fromkeys(required)) or ("semantic_qualification",)


def _confidence(status: str, semantic: Mapping[str, Any]) -> str:
    if status == "implemented":
        validation = str(semantic.get("validation_status", ""))
        return "medium" if "needs_in_game" in validation else "high"
    if status == "scenario_required":
        return "medium"
    if status == "unsupported":
        return "medium"
    return "low"


def _impact(label: str, text: str, status: str) -> str:
    normalized = f"{label} {text}".casefold()
    if status == "unsupported":
        return "outside the deterministic static comparator"
    if re.search(r"\b(power|control|spin|all stats)\b", normalized):
        return "may change Power, Control or Spin totals and their ability contributions"
    if "bounce" in normalized:
        return "may add a bounce metric and change the unresolved-bonus count"
    if "wind" in normalized:
        return "requires a wind scenario; unresolved in static comparison"
    if status == "implemented":
        return "included in the current objective comparison"
    return "cannot be quantified before semantic qualification"


def analyze_reference_gaps(
    *,
    user_dir: str | Path = "data/user",
    normalized_dir: str | Path = "data/normalized",
    raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
) -> ReferenceGapReport:
    root = Path(normalized_dir)
    catalog = load_raw_json(root / "clubs_official.json")
    semantic_map = load_raw_json(root / "semantic_map.json")
    raw = load_raw_json(raw_catalog_path)
    clubs = catalog.get("clubs") if isinstance(catalog, Mapping) else None
    semantics = semantic_map.get("entries") if isinstance(semantic_map, Mapping) else None
    if not isinstance(clubs, Mapping) or not isinstance(semantics, Mapping):
        raise ValueError("Normalized catalog and semantic map are required")

    bundle = load_user_data(user_dir)
    bag_ids_by_club: dict[str, list[str]] = {}
    ordered_club_ids: list[str] = []
    for bag in bundle.bags:
        for club_id in bag.club_ids:
            bag_ids_by_club.setdefault(club_id, []).append(bag.identifier)
            if club_id not in ordered_club_ids:
                ordered_club_ids.append(club_id)
    raw_by_name = _club_records(raw)
    handlers = set(default_mechanism_registry().names)
    inventory_by_club = {entry.club_id: entry for entry in bundle.inventory.entries}
    abilities: list[ReferenceAbilityGap] = []

    for club_id in ordered_club_ids:
        club = clubs[club_id]
        raw_club = raw_by_name[str(club["name"])]
        descriptions = _official_texts(raw_club)
        rows = raw_club["tables"][0]["rows"]
        labels = [str(row[0]) for row in rows[4:]]
        for index, ability in enumerate(club.get("abilities", [])):
            label_id = str(ability["label_id"])
            semantic = semantics[f"label:{label_id}"]
            official_label = labels[index]
            official_text = descriptions.get(official_label, "")
            values = ability.get("values_by_level", {})
            has_values = isinstance(values, Mapping) and any(value is not None for value in values.values())
            status = _status(semantic, official_text, handlers)
            pattern = semantic.get("pattern_id") or (
                f"mechanic:{semantic['mechanic_id']}" if semantic.get("mechanic_id") else f"unqualified:{label_id}"
            )
            abilities.append(
                ReferenceAbilityGap(
                    club_id=club_id,
                    club_name=str(club["name"]),
                    occurrence_id=str(ability["occurrence_id"]),
                    official_label=official_label,
                    official_text=official_text,
                    normalized_pattern=str(pattern),
                    status=status,
                    required_data=_required_data(semantic, official_text, has_values),
                    confidence=_confidence(status, semantic),
                    compare_bags_impact=_impact(official_label, official_text, status),
                    bag_ids=tuple(bag_ids_by_club[club_id]),
                    user_level=(
                        inventory_by_club[club_id].current_level
                        if club_id in inventory_by_club
                        else None
                    ),
                )
            )

    by_club = {club_id: tuple(item for item in abilities if item.club_id == club_id) for club_id in ordered_club_ids}
    coverage = []
    for bag in bundle.bags:
        bag_abilities = tuple(item for club_id in bag.club_ids for item in by_club[club_id])
        coverage.append(
            ReferenceBagCoverage(
                bag.identifier,
                len(bag_abilities),
                sum(item.status == "implemented" for item in bag_abilities),
            )
        )
    return ReferenceGapReport(len(ordered_club_ids), len(abilities), tuple(abilities), tuple(coverage))


def render_reference_gap_markdown(report: ReferenceGapReport) -> str:
    lines = [
        "# Reference Bag Ability Matrix",
        "",
        "> Generated automatically by `pga-shootout reference-gaps`. Do not edit manually.",
        "",
        "## Coverage",
        "",
        "| Bag | Implemented | Total | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for bag in report.bag_coverage:
        lines.append(
            f"| `{bag.bag_id}` | {bag.implemented_occurrences} | {bag.ability_occurrences} | {bag.coverage_percent:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Ability matrix",
            "",
            "| Club | User level | Official ability and text | Normalized pattern | Status | Required data | Confidence | compare-bags impact | Bags |",
            "|---|---:|---|---|---|---|---|---|---|",
        ]
    )
    for item in report.abilities:
        text = item.official_text.replace("|", "\\|") or "not captured"
        data = ", ".join(f"`{value}`" for value in item.required_data)
        bags = ", ".join(f"`{value}`" for value in item.bag_ids)
        lines.append(
            f"| {item.club_name} (`{item.club_id}`) | {item.user_level if item.user_level is not None else 'null'} | **{item.official_label}** — {text} "
            f"(`{item.occurrence_id}`) | `{item.normalized_pattern}` | `{item.status}` | {data} | "
            f"{item.confidence} | {item.compare_bags_impact} | {bags} |"
        )
    return "\n".join(lines) + "\n"


def generate_reference_gap_report(
    output_path: str | Path = "docs/REFERENCE_BAG_GAPS.md",
    **kwargs: Any,
) -> ReferenceGapReport:
    report = analyze_reference_gaps(**kwargs)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_reference_gap_markdown(report), encoding="utf-8", newline="\n")
    return report
