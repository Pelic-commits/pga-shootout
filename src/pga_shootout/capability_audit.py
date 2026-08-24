"""Reproducible audit of every official ability not fully supported by the engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .bag_evaluation import _semantic_effect_specs, semantic_support
from .inventory_status import (
    _primitive_profile,
    _technical_family,
    analyze_inventory_status,
)
from .loader import load_raw_json
from .registry import default_mechanism_registry
from .user_data import load_user_data
from .user_gap_report import _club_records, _official_texts


CLASSIFICATION_LABELS = {
    "A": "Déterministe / implémentation directe",
    "B": "Déterministe / petite extension générique",
    "C": "Texte ou sémantique ambiguë",
    "D": "Conflit entre sources ou données",
    "E": "Physique ou géométrie non modélisée",
    "F": "Historique de coups ou état temporel complexe",
    "G": "Aléatoire ou transformation",
    "H": "Partiellement simulée",
}

QUALIFICATION_CLASS = {
    "deterministic_existing_primitives": "A",
    "deterministic_small_generic_extension": "B",
    "true_semantic_ambiguity": "C",
    "official_text_table_conflict": "D",
    "geometry_or_trajectory_required": "E",
    "state_duration_or_trigger_unknown": "F",
    "random_or_transformational": "G",
    "clear_component_plus_physics": "H",
}

CONFIDENCE_BY_CLASS = {
    "A": "high",
    "B": "high",
    "C": "low",
    "D": "blocked",
    "E": "high_dependency_confidence",
    "F": "medium",
    "G": "high_dependency_confidence",
    "H": "high_for_resolved_component_only",
}


@dataclass(frozen=True)
class RemainingAbilityOccurrence:
    occurrence_id: str
    group_id: str
    club_id: str
    club_name: str
    owned: bool
    current_level: int | None
    official_name: str
    official_text: str
    values_by_level: tuple[tuple[str, str | None], ...]
    current_level_value: str | None
    status: str
    status_reason: str
    qualification_category: str
    audit_class: str
    technical_family: str
    reusable_primitives: tuple[str, ...]
    required_primitive: str | None
    difficulty: str
    confidence: str
    provenance: str
    validation_experiment: str | None


@dataclass(frozen=True)
class RemainingAbilityGroup:
    group_id: str
    audit_class: str
    official_names: tuple[str, ...]
    club_ids: tuple[str, ...]
    owned_club_ids: tuple[str, ...]
    occurrence_ids: tuple[str, ...]
    difficulty: str
    confidence: str
    reusable_primitives: tuple[str, ...]
    required_primitives: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityAuditReport:
    catalog_clubs: int
    owned_clubs: int
    catalog_occurrences: int
    owned_occurrences: int
    owned_fully_supported_occurrences: int
    owned_partial_occurrences: int
    owned_unresolved_occurrences: int
    owned_fully_simulated_clubs: int
    owned_clubs_with_unresolved_ability: int
    global_fully_supported_occurrences: int
    global_partial_occurrences: int
    global_unresolved_occurrences: int
    occurrences: tuple[RemainingAbilityOccurrence, ...]
    groups: tuple[RemainingAbilityGroup, ...]

    @property
    def class_counts(self) -> Mapping[str, int]:
        return {
            key: sum(item.audit_class == key for item in self.occurrences)
            for key in CLASSIFICATION_LABELS
        }

    @property
    def owned_class_counts(self) -> Mapping[str, int]:
        return {
            key: sum(item.audit_class == key and item.owned for item in self.occurrences)
            for key in CLASSIFICATION_LABELS
        }

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["class_counts"] = dict(self.class_counts)
        value["owned_class_counts"] = dict(self.owned_class_counts)
        return value


def _raw_value(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    notation = value.get("official_notation")
    if isinstance(notation, Mapping) and notation.get("raw") is not None:
        return str(notation["raw"])
    return None


def _audit_class(qualification_category: str, partially_supported: bool) -> str:
    if partially_supported:
        return "H"
    return QUALIFICATION_CLASS.get(qualification_category, "C")


def analyze_capability_audit(
    *,
    user_dir: str | Path = "data/pga_shootout.sqlite",
    normalized_dir: str | Path = "data/normalized",
    raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
) -> CapabilityAuditReport:
    normalized_root = Path(normalized_dir)
    catalog = load_raw_json(normalized_root / "clubs_official.json")
    semantic_map = load_raw_json(normalized_root / "semantic_map.json")
    raw = load_raw_json(raw_catalog_path)
    clubs_data = catalog["clubs"]
    semantics = semantic_map["entries"]
    patterns = semantic_map["patterns"]
    bundle = load_user_data(user_dir)
    owned_levels = {item.club_id: item.current_level for item in bundle.inventory.entries}
    owned_report = analyze_inventory_status(
        user_dir=user_dir,
        normalized_dir=normalized_root,
        raw_catalog_path=raw_catalog_path,
    )
    owned_status = {
        ability.occurrence_id: ability
        for club in owned_report.clubs
        for ability in club.abilities
    }
    raw_by_name = _club_records(raw)
    handler_names = set(default_mechanism_registry().names)
    occurrences: list[RemainingAbilityOccurrence] = []
    supported_count = 0
    partial_count = 0

    for club_id, club in clubs_data.items():
        raw_club = raw_by_name[str(club["name"])]
        official_texts = _official_texts(raw_club)
        official_names = [str(row[0]) for row in raw_club["tables"][0]["rows"][4:]]
        for index, ability in enumerate(club.get("abilities", ())):
            label_id = str(ability["label_id"])
            semantic = semantics[f"label:{label_id}"]
            supported, partially_supported, programs = semantic_support(
                semantic, patterns, handler_names,
            )
            if supported:
                supported_count += 1
                continue
            if partially_supported:
                partial_count += 1
            official_name = official_names[index]
            official_text = official_texts.get(official_name, "")
            family = _technical_family(semantic, label_id, official_text)
            program = programs[0] if len(programs) == 1 else {"effects": list(programs)}
            primitives, required_primitive = _primitive_profile(family, program)
            qualification = semantic.get("qualification", {})
            qualification_category = str(qualification.get("category", "unclassified"))
            classification = _audit_class(qualification_category, partially_supported)
            status_entry = owned_status.get(str(ability["occurrence_id"]))
            values = tuple(
                (str(level), _raw_value(value))
                for level, value in ability.get("values_by_level", {}).items()
            )
            current_level = owned_levels.get(club_id)
            current_value = dict(values).get(str(current_level)) if current_level is not None else None
            occurrences.append(RemainingAbilityOccurrence(
                occurrence_id=str(ability["occurrence_id"]),
                group_id=str(semantic.get("group_id", f"label:{label_id}")),
                club_id=club_id,
                club_name=str(club["name"]),
                owned=club_id in owned_levels,
                current_level=current_level,
                official_name=official_name,
                official_text=official_text,
                values_by_level=values,
                current_level_value=current_value,
                status=status_entry.status if status_entry else str(qualification.get("status", "unsupported")),
                status_reason=(
                    status_entry.reason if status_entry
                    else str(qualification.get("reason", "No validated engine interpretation."))
                ),
                qualification_category=qualification_category,
                audit_class=classification,
                technical_family=family,
                reusable_primitives=primitives,
                required_primitive=required_primitive,
                difficulty=str(semantic.get("complexity", "special")),
                confidence=CONFIDENCE_BY_CLASS[classification],
                provenance="official_versioned_catalog_and_qualified_semantic_map",
                validation_experiment=(
                    str(qualification["experiment"]) if qualification.get("experiment") else None
                ),
            ))

    grouped: dict[str, list[RemainingAbilityOccurrence]] = {}
    for item in occurrences:
        grouped.setdefault(item.group_id, []).append(item)
    groups = tuple(
        RemainingAbilityGroup(
            group_id=group_id,
            audit_class=items[0].audit_class,
            official_names=tuple(dict.fromkeys(item.official_name for item in items)),
            club_ids=tuple(item.club_id for item in items),
            owned_club_ids=tuple(item.club_id for item in items if item.owned),
            occurrence_ids=tuple(item.occurrence_id for item in items),
            difficulty=items[0].difficulty,
            confidence=items[0].confidence,
            reusable_primitives=tuple(dict.fromkeys(
                primitive for item in items for primitive in item.reusable_primitives
            )),
            required_primitives=tuple(dict.fromkeys(
                item.required_primitive for item in items if item.required_primitive
            )),
        )
        for group_id, items in sorted(grouped.items())
    )
    owned_partial = sum(item.owned and item.audit_class == "H" for item in occurrences)
    owned_remaining = sum(item.owned for item in occurrences)
    return CapabilityAuditReport(
        catalog_clubs=len(clubs_data),
        owned_clubs=owned_report.inventory_clubs,
        catalog_occurrences=owned_report.global_abilities,
        owned_occurrences=owned_report.official_abilities,
        owned_fully_supported_occurrences=owned_report.simulated_abilities,
        owned_partial_occurrences=owned_partial,
        owned_unresolved_occurrences=owned_remaining - owned_partial,
        owned_fully_simulated_clubs=owned_report.fully_simulated_clubs,
        owned_clubs_with_unresolved_ability=sum(not club.fully_simulated for club in owned_report.clubs),
        global_fully_supported_occurrences=supported_count,
        global_partial_occurrences=partial_count,
        global_unresolved_occurrences=len(occurrences) - partial_count,
        occurrences=tuple(occurrences),
        groups=groups,
    )


def _level_values_text(values: tuple[tuple[str, str | None], ...]) -> str:
    return "; ".join(f"{level}: {value if value is not None else 'inactive'}" for level, value in values)


def render_capability_audit_markdown(report: CapabilityAuditReport) -> str:
    lines = [
        "# Audit des capacités restantes",
        "",
        "> Rapport généré depuis SQLite, le catalogue officiel versionné, la carte sémantique et le registre du moteur.",
        "",
        "## État recalculé",
        "",
        "| Mesure | Valeur |",
        "|---|---:|",
        f"| Clubs du catalogue | {report.catalog_clubs} |",
        f"| Clubs possédés | {report.owned_clubs} |",
        f"| Occurrences catalogue | {report.catalog_occurrences} |",
        f"| Occurrences possédées | {report.owned_occurrences} |",
        f"| Possédées complètement simulées | {report.owned_fully_supported_occurrences} |",
        f"| Possédées partielles | {report.owned_partial_occurrences} |",
        f"| Possédées non résolues hors partielles | {report.owned_unresolved_occurrences} |",
        f"| Clubs possédés entièrement simulés | {report.owned_fully_simulated_clubs} |",
        f"| Clubs possédés avec au moins une capacité restante | {report.owned_clubs_with_unresolved_ability} |",
        "",
        "## Classification exhaustive",
        "",
        "| Classe | Définition | Catalogue | Possédées |",
        "|---|---|---:|---:|",
    ]
    for key, label in CLASSIFICATION_LABELS.items():
        lines.append(f"| {key} | {label} | {report.class_counts[key]} | {report.owned_class_counts[key]} |")
    lines.extend((
        "",
        "Les classes A et B sont vides : aucune capacité restante ne peut être implémentée sans contredire une qualification existante ou introduire une hypothèse. Aucun handler n'est donc ajouté par ce lot.",
        "",
        "## Groupes restants",
        "",
        "| Classe | Groupe | Occurrences | Clubs | Clubs possédés | Difficulté | Primitive manquante |",
        "|---|---|---:|---|---|---|---|",
    ))
    for group in sorted(report.groups, key=lambda item: (item.audit_class, item.group_id)):
        lines.append(
            f"| {group.audit_class} | `{group.group_id}` | {len(group.occurrence_ids)} | "
            f"{', '.join(group.club_ids)} | {', '.join(group.owned_club_ids) or 'aucun'} | "
            f"{group.difficulty} | {', '.join(group.required_primitives) or 'aucune primitive suffisante sans donnée externe'} |"
        )
    lines.extend(("", "## Occurrences détaillées", ""))
    for item in sorted(report.occurrences, key=lambda value: (value.audit_class, value.club_name, value.occurrence_id)):
        lines.extend((
            f"### {item.club_name} — {item.official_name}",
            "",
            f"- Identifiant : `{item.occurrence_id}`",
            f"- Classe : **{item.audit_class} — {CLASSIFICATION_LABELS[item.audit_class]}**",
            f"- Possédé : {'oui' if item.owned else 'non'}",
            f"- Niveau utilisateur : {item.current_level if item.current_level is not None else 'inconnu/non possédé'}",
            f"- Valeur au niveau utilisateur : {item.current_level_value or 'inactive/inconnue'}",
            f"- Texte officiel : {item.official_text}",
            f"- Valeurs par niveau : {_level_values_text(item.values_by_level)}",
            f"- Statut : `{item.status}`",
            f"- Raison : {item.status_reason}",
            f"- Qualification : `{item.qualification_category}`",
            f"- Famille technique : `{item.technical_family}`",
            f"- Primitives disponibles : {', '.join(item.reusable_primitives) or 'aucune'}",
            f"- Primitive/donnée manquante : `{item.required_primitive or 'validation_or_external_model'}`",
            f"- Difficulté : {item.difficulty}",
            f"- Confiance : {item.confidence}",
            f"- Provenance : `{item.provenance}`",
            f"- Validation proposée : {item.validation_experiment or 'aucune expérience qualifiée'}",
            "",
        ))
    return "\n".join(lines).rstrip() + "\n"
