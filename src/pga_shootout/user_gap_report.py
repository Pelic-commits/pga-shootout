"""Inventory-first ability gap reporting from official and user data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import html
from pathlib import Path
import re
from typing import Any, Mapping

from .loader import load_raw_json
from .registry import default_mechanism_registry
from .user_data import load_user_data


ALLOWED_STATUSES = frozenset(
    {
        "implemented",
        "qualified_not_implemented",
        "ambiguous",
        "scenario_required",
        "unsupported",
    }
)


@dataclass(frozen=True)
class AbilityGap:
    occurrence_id: str
    label: str
    official_text: str
    pattern: str
    status: str
    saved_bag_ids: tuple[str, ...]
    compare_bags_impact: str


@dataclass(frozen=True)
class ClubGap:
    club_id: str
    name: str
    saved_bag_ids: tuple[str, ...]
    abilities: tuple[AbilityGap, ...]


@dataclass(frozen=True)
class UserGapReport:
    inventory_clubs: int
    ability_occurrences: int
    implemented_occurrences: int
    fully_implemented_clubs: int
    clubs: tuple[ClubGap, ...]

    @property
    def occurrence_coverage_percent(self) -> float:
        if not self.ability_occurrences:
            return 100.0
        return round(100 * self.implemented_occurrences / self.ability_occurrences, 2)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["occurrence_coverage_percent"] = self.occurrence_coverage_percent
        return value


def _club_records(raw: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    clubs = raw.get("clubs")
    if not isinstance(clubs, list):
        raise ValueError("Raw official catalog must contain a clubs list")
    return {
        str(club["name"]): club
        for club in clubs
        if isinstance(club, Mapping) and isinstance(club.get("name"), str)
    }


def _official_texts(raw_club: Mapping[str, Any]) -> dict[str, str]:
    """Recover labels and descriptions without interpreting their meaning."""
    expanded_html = raw_club.get("expanded_html")
    if not isinstance(expanded_html, str):
        return {}
    marker = ">Abilities</h4>"
    if marker not in expanded_html:
        return {}
    ability_html = expanded_html.split(marker, 1)[1]
    descriptions: dict[str, str] = {}
    for raw_label, raw_description in re.findall(
        r"<p\b[^>]*>(.*?)</p>\s*<div\b[^>]*>(.*?)</div>", ability_html, re.DOTALL
    ):
        label = html.unescape(re.sub(r"<[^>]+>", "", raw_label)).strip()
        description = html.unescape(re.sub(r"<[^>]+>", "", raw_description)).strip()
        descriptions[label] = description
    return descriptions


def _status(semantic: Mapping[str, Any], text: str, handler_names: set[str]) -> str:
    mechanic = semantic.get("mechanic_id")
    if isinstance(mechanic, str) and mechanic in handler_names:
        return "implemented"
    if semantic.get("validation_status") not in (None, "not_started"):
        return "qualified_not_implemented"
    normalized = text.casefold()
    if re.search(r"\b(random|randomly|transform|swap|replace)\w*\b", normalized):
        return "unsupported"
    if re.search(
        r"\b(wind|fairway|rough|bunker|green|tee|previous|next shot|after .*shot|"
        r"before .*shot|tree|boundary|out of bounds|special ball)\b",
        normalized,
    ):
        return "scenario_required"
    return "ambiguous"


def _impact(label: str, text: str, status: str) -> str:
    normalized = f"{label} {text}".casefold()
    if status == "scenario_required":
        return "scenario metric; no effect in the static comparator"
    if status == "unsupported":
        return "outside the deterministic static comparator"
    if re.search(r"\b(power|control|spin)\b", normalized):
        return "changes a core compared statistic"
    if re.search(r"\b(angle|loft|bounce|fade|draw)\b", normalized):
        return "adds or changes a separately compared static metric"
    if status == "implemented":
        return "included in objective ability contributions"
    return "impact cannot be quantified before semantic qualification"


def analyze_user_gaps(
    *,
    user_dir: str | Path = "data/user",
    normalized_dir: str | Path = "data/normalized",
    raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
) -> UserGapReport:
    normalized_root = Path(normalized_dir)
    catalog = load_raw_json(normalized_root / "clubs_official.json")
    semantic = load_raw_json(normalized_root / "semantic_map.json")
    raw = load_raw_json(raw_catalog_path)
    clubs = catalog.get("clubs") if isinstance(catalog, Mapping) else None
    entries = semantic.get("entries") if isinstance(semantic, Mapping) else None
    if not isinstance(clubs, Mapping) or not isinstance(entries, Mapping):
        raise ValueError("Normalized club catalog and semantic map are required")

    bundle = load_user_data(user_dir)
    bags_by_club: dict[str, list[str]] = {}
    for bag in bundle.bags:
        for club_id in bag.club_ids:
            bags_by_club.setdefault(club_id, []).append(bag.identifier)
    raw_by_name = _club_records(raw)
    handlers = set(default_mechanism_registry().names)
    result: list[ClubGap] = []

    for inventory_entry in bundle.inventory.entries:
        club = clubs[inventory_entry.club_id]
        descriptions = _official_texts(raw_by_name[str(club["name"])])
        abilities: list[AbilityGap] = []
        raw_table = raw_by_name[str(club["name"])]["tables"][0]["rows"]
        display_labels = [str(row[0]) for row in raw_table[4:]]
        for index, ability in enumerate(club.get("abilities", [])):
            label_id = str(ability["label_id"])
            group_id = f"label:{label_id}"
            semantic_entry = entries[group_id]
            label = display_labels[index]
            official_text = descriptions.get(label, "")
            status = _status(semantic_entry, official_text, handlers)
            abilities.append(
                AbilityGap(
                    occurrence_id=str(ability["occurrence_id"]),
                    label=label,
                    official_text=official_text,
                    pattern=str(
                        semantic_entry.get("pattern_id")
                        or (f"mechanic:{semantic_entry['mechanic_id']}" if semantic_entry.get("mechanic_id") else None)
                        or f"unqualified:{label_id}"
                    ),
                    status=status,
                    saved_bag_ids=tuple(bags_by_club.get(inventory_entry.club_id, ())),
                    compare_bags_impact=_impact(label, official_text, status),
                )
            )
        result.append(
            ClubGap(
                club_id=inventory_entry.club_id,
                name=str(club["name"]),
                saved_bag_ids=tuple(bags_by_club.get(inventory_entry.club_id, ())),
                abilities=tuple(abilities),
            )
        )

    all_abilities = tuple(ability for club in result for ability in club.abilities)
    return UserGapReport(
        inventory_clubs=len(result),
        ability_occurrences=len(all_abilities),
        implemented_occurrences=sum(item.status == "implemented" for item in all_abilities),
        fully_implemented_clubs=sum(
            bool(club.abilities) and all(item.status == "implemented" for item in club.abilities)
            for club in result
        ),
        clubs=tuple(result),
    )


def render_user_gap_markdown(report: UserGapReport) -> str:
    lines = [
        "# User Inventory Ability Gaps",
        "",
        "> Generated automatically by `pga-shootout user-gaps`. Do not edit manually.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Known inventory clubs | {report.inventory_clubs} |",
        f"| Official ability occurrences | {report.ability_occurrences} |",
        f"| Implemented occurrences | {report.implemented_occurrences} |",
        f"| Inventory occurrence coverage | {report.occurrence_coverage_percent:.2f}% |",
        f"| Fully implemented clubs | {report.fully_implemented_clubs} |",
        "",
    ]
    for club in report.clubs:
        bags = ", ".join(f"`{bag}`" for bag in club.saved_bag_ids) or "none"
        lines.extend(
            [
                f"## {club.name} (`{club.club_id}`)",
                "",
                f"Saved bags: {bags}.",
                "",
                "| Official ability | Official text | Pattern | Status | compare-bags impact |",
                "|---|---|---|---|---|",
            ]
        )
        for ability in club.abilities:
            official_text = ability.official_text.replace("|", "\\|") or "not captured"
            lines.append(
                f"| {ability.label} (`{ability.occurrence_id}`) | {official_text} | "
                f"`{ability.pattern}` | `{ability.status}` | {ability.compare_bags_impact} |"
            )
        lines.append("")
    return "\n".join(lines)


def generate_user_gap_report(
    output_path: str | Path = "docs/USER_GAPS.md",
    **kwargs: Any,
) -> UserGapReport:
    report = analyze_user_gaps(**kwargs)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_user_gap_markdown(report), encoding="utf-8", newline="\n")
    return report
