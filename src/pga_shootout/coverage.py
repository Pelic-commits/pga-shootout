"""Mechanic coverage analysis driven exclusively by normalized artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .loader import load_raw_json
from .registry import default_mechanism_registry


class CoverageError(ValueError):
    pass


@dataclass(frozen=True)
class GroupCoverage:
    rank: int
    group_id: str
    source_label_id: str
    mechanic_id: str | None
    occurrences: int
    clubs: int
    club_ids: tuple[str, ...]
    club_names: tuple[str, ...]
    handler_exists: bool
    coverage_percent: float
    difficulty: str
    dependencies: tuple[str, ...] | None
    interpretation_status: str
    estimated_gain_occurrences: int
    estimated_gain_clubs: int


@dataclass(frozen=True)
class CoverageReport:
    total_groups: int
    total_occurrences: int
    total_clubs: int
    implemented_groups: int
    registered_handlers: tuple[str, ...]
    occurrence_coverage_percent: float
    club_coverage_percent: float
    interpreted_groups: int
    unclassified_groups: int
    groups: tuple[GroupCoverage, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_object(path: Path, field: str) -> dict[str, Any]:
    data = load_raw_json(path)
    value = data.get(field) if isinstance(data, dict) else None
    if not isinstance(value, dict):
        raise CoverageError(f"{path.name} must contain an object named {field}")
    return value


def analyze_coverage(
    normalized_dir: str | Path = "data/normalized",
    handler_names: tuple[str, ...] | None = None,
) -> CoverageReport:
    root = Path(normalized_dir)
    occurrences = _load_object(root / "ability_occurrences.json", "occurrences")
    labels = _load_object(root / "ability_labels.json", "labels")
    groups = _load_object(root / "mechanics_catalog.json", "groups")
    semantic_entries = _load_object(root / "semantic_map.json", "entries")
    handlers = tuple(handler_names if handler_names is not None else default_mechanism_registry().names)

    if set(groups) != set(semantic_entries):
        raise CoverageError("mechanics_catalog and semantic_map group identifiers differ")
    grouped_occurrences = [occurrence_id for group in groups.values() for occurrence_id in group["occurrence_ids"]]
    if len(grouped_occurrences) != len(set(grouped_occurrences)):
        raise CoverageError("an occurrence belongs to more than one mechanic group")
    if set(grouped_occurrences) != set(occurrences):
        raise CoverageError("mechanic groups do not cover every ability occurrence exactly once")
    if {group["source_label_id"] for group in groups.values()} != set(labels):
        raise CoverageError("mechanic groups and ability labels differ")

    all_clubs = {
        str(record["club"]["id"]): str(record["club"]["name"])
        for record in occurrences.values()
    }
    implemented_occurrences: set[str] = set()
    implemented_clubs: set[str] = set()
    preliminary: list[dict[str, Any]] = []
    allowed_complexities = {"generic", "parameterized", "stateful", "special"}

    for group_id, group in groups.items():
        semantic = semantic_entries[group_id]
        mechanic_id = semantic.get("mechanic_id") or group.get("mechanic_id")
        difficulty = semantic.get("complexity")
        if difficulty not in allowed_complexities:
            difficulty = "unclassified"
        raw_dependencies = semantic.get("dependencies")
        dependencies = tuple(str(value) for value in raw_dependencies) if isinstance(raw_dependencies, list) else None
        handler_exists = isinstance(mechanic_id, str) and mechanic_id in handlers
        occurrence_ids = tuple(str(value) for value in group["occurrence_ids"])
        club_ids = tuple(str(value) for value in group["club_ids"])
        if handler_exists:
            implemented_occurrences.update(occurrence_ids)
            implemented_clubs.update(club_ids)
        preliminary.append(
            {
                "group_id": group_id,
                "source_label_id": str(group["source_label_id"]),
                "mechanic_id": mechanic_id,
                "occurrences": len(occurrence_ids),
                "clubs": len(club_ids),
                "club_ids": club_ids,
                "club_names": tuple(all_clubs[club_id] for club_id in club_ids),
                "handler_exists": handler_exists,
                "coverage_percent": 100.0 if handler_exists else 0.0,
                "difficulty": difficulty,
                "dependencies": dependencies,
                "interpretation_status": str(semantic.get("interpretation_status", "unknown")),
                "estimated_gain_occurrences": 0 if handler_exists else len(occurrence_ids),
                "estimated_gain_clubs": 0 if handler_exists else len(club_ids),
            }
        )

    preliminary.sort(
        key=lambda item: (
            item["handler_exists"],
            -item["estimated_gain_occurrences"],
            -item["estimated_gain_clubs"],
            item["group_id"],
        )
    )
    ranked = tuple(GroupCoverage(rank=index, **item) for index, item in enumerate(preliminary, start=1))
    total_occurrences = len(occurrences)
    total_clubs = len(all_clubs)
    interpreted_groups = sum(group.mechanic_id is not None for group in ranked)
    return CoverageReport(
        total_groups=len(groups),
        total_occurrences=total_occurrences,
        total_clubs=total_clubs,
        implemented_groups=sum(group.handler_exists for group in ranked),
        registered_handlers=handlers,
        occurrence_coverage_percent=round(100 * len(implemented_occurrences) / total_occurrences, 2),
        club_coverage_percent=round(100 * len(implemented_clubs) / total_clubs, 2),
        interpreted_groups=interpreted_groups,
        unclassified_groups=sum(group.difficulty == "unclassified" for group in ranked),
        groups=ranked,
    )


def render_coverage_markdown(report: CoverageReport) -> str:
    lines = [
        "# Mechanic Coverage",
        "",
        "> Generated automatically by `pga-shootout coverage`. Do not edit manually.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Structural groups | {report.total_groups} |",
        f"| Ability occurrences | {report.total_occurrences} |",
        f"| Clubs represented | {report.total_clubs} |",
        f"| Groups mapped to a registered handler | {report.implemented_groups} |",
        f"| Occurrence coverage | {report.occurrence_coverage_percent:.2f}% |",
        f"| Club coverage | {report.club_coverage_percent:.2f}% |",
        f"| Interpreted groups | {report.interpreted_groups} |",
        f"| Unclassified groups | {report.unclassified_groups} |",
        "",
        f"Registered handlers: `{', '.join(report.registered_handlers)}`.",
        "",
    ]
    if report.interpreted_groups == 0:
        lines.extend(
            [
                "## Roadmap status",
                "",
                "Implementation ranking is blocked: every semantic mapping is still `uninterpreted` and has no mechanic ID, complexity or dependencies.",
                "The ranking below is therefore a **semantic qualification queue**, ordered only by maximum raw occurrence gain. It is not permission to implement a handler.",
                "",
            ]
        )
    lines.extend(
        [
            "## Top 20 potential coverage gains",
            "",
            "| Rank | Structural group | Mechanic | Occurrences | Clubs | Difficulty | Dependencies | Handler |",
            "|---:|---|---|---:|---:|---|---|---|",
        ]
    )
    for group in report.groups[:20]:
        dependencies = "unknown" if group.dependencies is None else ", ".join(group.dependencies) or "none"
        lines.append(
            f"| {group.rank} | `{group.source_label_id}` | "
            f"{f'`{group.mechanic_id}`' if group.mechanic_id else 'uninterpreted'} | "
            f"{group.occurrences} | {group.clubs} | {group.difficulty} | {dependencies} | "
            f"{'yes' if group.handler_exists else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Roadmap",
            "",
            "### Phase 0 — Semantic qualification (required)",
            "",
            "Validate mechanic ID, complexity and dependencies for the structural groups in ranking order. No implementation phase can be calculated safely before this metadata exists.",
            "",
            "### Projected implementation phases",
            "",
            "Not generated while semantic mappings are absent. Once mappings are populated, rerun this command to rank actual mechanics against registered handlers.",
            "",
            "## Complete group coverage",
            "",
            "| Rank | Group | Mechanic | Occurrences | Clubs | Club list | Coverage | Difficulty | Dependencies |",
            "|---:|---|---|---:|---:|---|---:|---|---|",
        ]
    )
    for group in report.groups:
        dependencies = "unknown" if group.dependencies is None else ", ".join(group.dependencies) or "none"
        clubs = ", ".join(f"{name} (`{club_id}`)" for name, club_id in zip(group.club_names, group.club_ids))
        mechanic = f"`{group.mechanic_id}`" if group.mechanic_id else "uninterpreted"
        lines.append(
            f"| {group.rank} | `{group.source_label_id}` | {mechanic} | {group.occurrences} | {group.clubs} | "
            f"{clubs} | {group.coverage_percent:.0f}% | {group.difficulty} | {dependencies} |"
        )
    return "\n".join(lines) + "\n"


def generate_coverage_report(
    normalized_dir: str | Path = "data/normalized",
    output_path: str | Path = "docs/MECHANIC_COVERAGE.md",
) -> CoverageReport:
    report = analyze_coverage(normalized_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_coverage_markdown(report), encoding="utf-8", newline="\n")
    return report
