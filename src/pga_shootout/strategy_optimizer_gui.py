"""Windows-friendly Tkinter presentation for the generic strategy optimizer.

The presenter and controller deliberately have no Tkinter dependency.  This
keeps the UI a replaceable consumer of StrategyOptimizationResult and makes the
threading, French messages and exports testable without opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Callable, Mapping

from .inventory_editor import InventoryEditorApp, InventoryEditorService
from .models import EvaluationMode
from .optimizer_cards import METRICS as METRIC_LABELS
from .strategy import StrategyError, StrategyRegistry
from .strategy_optimizer import (
    ClubStepResult,
    ContributionRecord,
    StrategyCandidateResult,
    StrategyOptimizationError,
    StrategyOptimizationRequest,
    StrategyOptimizationResult,
    StrategyOptimizer,
    render_strategy_optimization,
    render_strategy_optimization_json,
)
from .storage import PgaDatabase
from .user_data import BagReferenceProfile
from .user_data import load_user_data


ROLE_LABELS = {
    "active": "actif",
    "support": "support",
    "hybrid": "hybride",
    "neutral": "neutre",
}
GROUP_LABELS = {
    "without_observed_loss": "Amélioration sans contrepartie observée",
    "tradeoff": "Compromis",
    "with_warnings": "Compromis partiellement évalué",
    "excluded": "Candidat exclu",
    "neutral": "Neutre",
    "best_admissible": "Meilleur sac admissible sous la restriction",
    "inferior": "Alternative inférieure",
}


def _bag_label(bag) -> str:
    return f"{bag.reference.label} — {bag.name}" if bag.reference else bag.name


@dataclass(frozen=True)
class StrategyChoice:
    identifier: str
    label: str


@dataclass(frozen=True)
class VariantChoice:
    identifier: str | None
    label: str


@dataclass(frozen=True)
class OptimizationGuiOptions:
    strategy_id: str
    variant_id: str | None = None
    real_mode: bool = True
    scenario_level: int | None = None
    limit: int = 5
    max_evaluations: int = 2000
    reference_bag_id: str | None = None
    search_mode: str = "build_from_scratch"
    target_bag_id: str | None = None
    fixed_club_id: str | None = None
    replace_club_id: str | None = None
    replacement_depth: int = 1
    required_club_ids: tuple[str, ...] = ()
    excluded_club_ids: tuple[str, ...] = ()
    locked_positions: Mapping[int, str] | None = None
    keep_current_putter: bool = False
    fixed_step_id: str | None = None
    club_roles: Mapping[str, str] | None = None
    metric_minimums: Mapping[str, Mapping[str, float]] | None = None
    primary_step_id: str | None = None
    allowed_brands: tuple[str, ...] = ()
    replacement_type_policy: str = "same_type"

    def to_request(self) -> StrategyOptimizationRequest:
        if self.limit not in {5, 10, 20}:
            raise ValueError("Choisissez 5, 10 ou 20 résultats.")
        if self.max_evaluations < 1:
            raise ValueError("La limite de calcul doit être supérieure à zéro.")
        if not self.real_mode and self.scenario_level is None:
            raise ValueError("Indiquez un niveau pour le mode Scénario.")
        if self.scenario_level is not None and not 1 <= self.scenario_level <= 12:
            raise ValueError("Le niveau de scénario doit être compris entre 1 et 12.")
        return StrategyOptimizationRequest(
            strategy_id=self.strategy_id,
            variant_ids=(self.variant_id,) if self.variant_id else (),
            limit=self.limit,
            mode=EvaluationMode.PARTIAL,
            scenario_level=None if self.real_mode else self.scenario_level,
            max_evaluations=self.max_evaluations,
            reference_bag_id=self.reference_bag_id,
            search_mode=self.search_mode,
            target_bag_id=self.target_bag_id,
            fixed_club_id=self.fixed_club_id,
            replace_club_id=self.replace_club_id,
            replacement_depth=self.replacement_depth,
            required_club_ids=self.required_club_ids,
            excluded_club_ids=self.excluded_club_ids,
            locked_positions=self.locked_positions or {},
            keep_current_putter=self.keep_current_putter,
            fixed_step_id=self.fixed_step_id,
            club_roles=self.club_roles or {},
            metric_minimums=self.metric_minimums or {},
            primary_step_id=self.primary_step_id,
            allowed_brands=self.allowed_brands,
            replacement_type_policy=self.replacement_type_policy,
        )


@dataclass(frozen=True)
class CandidateListPresentation:
    display_number: int
    composition: str
    active_clubs: str
    category: str
    unresolved_count: int
    has_neutral_club: bool
    strengths: str
    families: str = ""
    origin: str = ""


@dataclass(frozen=True)
class StepPresentation:
    step_id: str
    label: str
    content: str


@dataclass(frozen=True)
class CandidateDetailPresentation:
    title: str
    overview: str
    steps: tuple[StepPresentation, ...]
    synergies: str
    technical_details: str
    clipboard_summary: str


@dataclass(frozen=True)
class OptimizationPresentation:
    reference_text: str
    warning_text: str
    search_information: str
    candidates: tuple[CandidateListPresentation, ...]
    details: tuple[CandidateDetailPresentation, ...]


class StrategyOptimizerPresenter:
    """Translate optimizer domain objects into user-facing French text."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self.registry = registry

    @classmethod
    def load(cls, registry_path: str | Path = "data/strategies/strategies.json") -> "StrategyOptimizerPresenter":
        return cls(StrategyRegistry.load(registry_path))

    def strategy_choices(self) -> tuple[StrategyChoice, ...]:
        return tuple(StrategyChoice(item.identifier, item.user_name) for item in self.registry.strategies)

    def variant_choices(self, strategy_id: str) -> tuple[VariantChoice, ...]:
        return (
            VariantChoice(None, "Aucune variante"),
            *(VariantChoice(item.identifier, item.user_name) for item in self.registry.compatible_variants(strategy_id)),
        )

    def present(self, result: StrategyOptimizationResult) -> OptimizationPresentation:
        resolved = self.registry.resolve(result.strategy_id, result.applied_variant_ids)
        step_labels = {step.identifier: step.name for step in resolved.definition.sequence}
        family_names = {item.identifier: item.user_name for item in result.result_families}
        candidates = tuple(
            self._candidate_list(index, item, step_labels, family_names)
            for index, item in enumerate(result.retained_results, 1)
        )
        details = tuple(self._candidate_detail(index, item, step_labels) for index, item in enumerate(result.retained_results, 1))
        return OptimizationPresentation(
            reference_text=self._reference_summary(result, step_labels),
            warning_text=self._warnings(result),
            search_information=self._search_information(result),
            candidates=candidates,
            details=details,
        )

    @staticmethod
    def _reference_summary(result: StrategyOptimizationResult, step_labels: Mapping[str, str]) -> str:
        reference = result.comparison_reference
        if reference is None:
            return "COMPARER À — Aucun sac réel sélectionné"
        baseline = next((item for item in result.retained_results if "current_bag" in item.result_family_ids), None)
        lines = [f"RÉFÉRENCE — {reference.label}"]
        if reference.usage:
            lines.append(reference.usage)
        if baseline:
            clubs = {item.club_id: item for item in baseline.clubs}
            for step_id, club_id in baseline.active_assignments.items():
                club = clubs[club_id]
                step = next(item for item in club.steps if item.step_id == step_id)
                displayed = {
                    **step.final_stats,
                    **reference.observed_metrics.get(step_id, {}),
                }
                values = " / ".join(
                    f"{METRIC_LABELS[key]} {value:g}"
                    for key, value in displayed.items() if value is not None and key in METRIC_LABELS
                )
                lines.append(f"{step_labels.get(step_id, step_id)} — {club.club_name} — {values}")
        if reference.note:
            lines.append("Note : " + reference.note)
        if reference.reference_roles:
            role_labels = {
                "automatic": "Automatique", "support": "Support", "variable": "Variable",
                **step_labels,
            }
            names = {
                club.club_id: club.club_name
                for candidate in result.retained_results for club in candidate.clubs
            }
            lines.append("Rôles observés : " + ", ".join(
                f"{names.get(club_id, club_id)}={role_labels.get(role, role)}"
                for club_id, role in reference.reference_roles.items()
            ))
        if result.reference_is_admissible and not result.improvement_without_loss_found:
            lines.append("Aucune amélioration sans perte calculable trouvée.")
        return "\n".join(lines)

    def _candidate_list(
        self,
        index: int,
        candidate: StrategyCandidateResult,
        step_labels: Mapping[str, str],
        family_names: Mapping[str, str],
    ) -> CandidateListPresentation:
        club_names = {club.club_id: club.club_name for club in candidate.clubs}
        active = ", ".join(
            f"{step_labels.get(step_id, step_id)} : {club_names[club_id]}"
            for step_id, club_id in candidate.active_assignments.items()
        )
        return CandidateListPresentation(
            display_number=index,
            composition=" · ".join(f"{club.club_name} — {club.club_type.title()}" for club in candidate.clubs),
            active_clubs=active,
            category=(
                "SAC ACTUEL — MEILLEUR RÉSULTAT CONNU"
                if candidate.result_status == "current_best_known"
                else "SAC ACTUEL" if candidate.result_status == "current_bag"
                else GROUP_LABELS.get(candidate.comparison_group, "Proposition retenue")
            ),
            unresolved_count=len(candidate.unresolved_abilities),
            has_neutral_club=any(club.role == "neutral" for club in candidate.clubs),
            strengths=self._strengths(candidate, step_labels),
            families=", ".join(family_names.get(item, item) for item in candidate.result_family_ids),
            origin={
                "reference_bag": "Sac enregistré",
                "reference_neighborhood": "Amélioration locale",
                "global_search": "Recherche globale",
                "interactive_builder": "Constructeur interactif",
                "build_from_scratch": "Construction depuis zéro",
                "known_candidate": "Solution connue de la session",
            }.get(candidate.origin, candidate.origin),
        )

    def _strengths(self, candidate: StrategyCandidateResult, step_labels: Mapping[str, str]) -> str:
        facts: list[str] = []
        facts.extend(candidate.optimization_badges)
        if candidate.metric_deltas_from_power_max:
            facts.extend(
                f"{key} {value:+g}"
                for key, value in candidate.metric_deltas_from_power_max.items()
                if value not in {None, 0}
            )
        if candidate.removed_club_ids or candidate.added_club_ids:
            facts.append(
                "Remplacement " + ", ".join(candidate.removed_club_ids or ("aucun",))
                + " → " + ", ".join(candidate.added_club_ids or ("aucun",))
            )
        if candidate.metric_deltas_from_reference:
            facts.extend(
                f"{metric} {delta:+g}"
                for metric, delta in candidate.metric_deltas_from_reference.items()
                if delta not in {None, 0}
            )
        for club in candidate.clubs:
            if club.role not in {"active", "hybrid"}:
                continue
            for step in club.steps:
                if step.step_id not in club.active_steps:
                    continue
                for metric, delta in step.deltas.items():
                    if delta is not None and delta > 0:
                        facts.append(f"{club.club_name} {_metric_label(metric)} {delta:+g}")
                for metric, value in step.additional_metrics.items():
                    if value:
                        facts.append(f"{club.club_name} {_metric_label(metric)} {value:g}{_metric_unit(metric)}")
        return " ; ".join(dict.fromkeys(facts))[:240] or "Aucun gain différenciant observé sur les métriques calculables"

    def _candidate_detail(
        self,
        index: int,
        candidate: StrategyCandidateResult,
        step_labels: Mapping[str, str],
    ) -> CandidateDetailPresentation:
        steps = tuple(
            StepPresentation(step_id, label, self._step_content(candidate, step_id, label, step_labels))
            for step_id, label in step_labels.items()
        )
        prefix = "SAC ACTUEL" if candidate.result_status in {"current_bag", "current_best_known"} else f"Proposition {index}"
        title = prefix + " — " + " · ".join(club.club_name for club in candidate.clubs)
        clipboard = "\n".join((
            title,
            GROUP_LABELS.get(candidate.comparison_group, "Proposition retenue"),
            *(f"{club.position}. {club.club_name} — niveau {club.level} — {ROLE_LABELS[club.role]}" for club in candidate.clubs),
            "",
            self._synergies(candidate, step_labels),
        ))
        return CandidateDetailPresentation(
            title=title,
            overview=self._overview(candidate, step_labels),
            steps=steps,
            synergies=self._synergies(candidate, step_labels),
            technical_details=self._technical(candidate, step_labels),
            clipboard_summary=clipboard,
        )

    def _overview(
        self,
        candidate: StrategyCandidateResult,
        step_labels: Mapping[str, str],
    ) -> str:
        clubs = {item.club_id: item for item in candidate.clubs}
        lines = ["Résumé des clubs essentiels", "=" * 28]
        lines.extend((
            f"Statut : {candidate.result_status}",
            f"Pourquoi ce résultat est affiché : {candidate.reason_for_display}",
            f"Clubs remplacés : {candidate.replacement_depth}",
        ))
        if candidate.optimization_badges:
            lines.extend(("", " / ".join(candidate.optimization_badges)))
        if candidate.metric_deltas_from_power_max:
            lines.extend(("", "ÉCART AVEC LA MEILLEURE PUISSANCE TROUVÉE"))
            lines.extend(
                f"- {step_labels.get(key.split('.', 1)[0], key)} / {_metric_label(key.split('.', 1)[1])} : "
                + ("inconnu" if value is None else "=" if value == 0 else f"{value:+g}")
                for key, value in candidate.metric_deltas_from_power_max.items()
                if key.rsplit(".", 1)[-1] in METRIC_LABELS
            )
        if candidate.metric_values_from_reference is not None:
            lines.extend(("", self._reference_comparison(candidate, step_labels)))
        for step_id, club_id in candidate.active_assignments.items():
            club = clubs[club_id]
            step = next(item for item in club.steps if item.step_id == step_id)
            values = []
            for metric in ("power", "control", "spin"):
                value = step.final_stats.get(metric)
                if value is not None and step.metric_relevance.get(metric) == "objective":
                    values.append(f"{_metric_label(metric)} {value:g}")
            lines.extend((
                "",
                step_labels.get(step_id, step_id).upper(),
                f"Club : {club.club_name}",
                " — ".join(values) or "Aucune métrique objective disponible",
            ))
        support_lines = [
            f"{club.club_name} : {', '.join(step_labels.get(step, step) for step in club.support_steps)}"
            for club in candidate.clubs if club.support_steps
        ]
        lines.extend(("", "SUPPORTS", *(support_lines or ("Aucun support différenciant observé",))))
        lines.extend(("", "LES CINQ CLUBS", "=" * 15))
        primary_step = next(iter(candidate.active_assignments), None)
        for club in candidate.clubs:
            display_step_id = club.active_steps[0] if club.active_steps else primary_step
            display_step = next(
                (step for step in club.steps if step.step_id == display_step_id),
                club.steps[0],
            )
            stats = " / ".join(
                f"{_metric_label(metric)} {display_step.final_stats[metric]:g}"
                for metric in ("power", "control", "spin")
                if display_step.final_stats.get(metric) is not None
            )
            lines.append(
                f"{club.position}. {club.club_name} — {club.club_type.title()} — niveau {club.level} — "
                f"{ROLE_LABELS[club.role]} — {stats}"
            )
            lines.append("   → " + (
                " ; ".join(club.selection_reasons)
                or "aucune contribution déterminante identifiée"
            ))
        lines.extend(("", "ORDRE", " → ".join(club.club_name for club in candidate.clubs)))
        if candidate.unresolved_abilities:
            lines.extend(("", f"AVERTISSEMENTS : {len(candidate.unresolved_abilities)} capacité(s) non résolue(s)"))
        return "\n".join(lines)

    @staticmethod
    def _reference_comparison(
        candidate: StrategyCandidateResult,
        step_labels: Mapping[str, str],
    ) -> str:
        names = {club.club_id: club.club_name for club in candidate.clubs}
        lines = ["COMPARAISON AVANT / APRÈS", "=" * 27]
        lines.append("CLUBS RETIRÉS : " + (", ".join(candidate.removed_club_ids) or "aucun"))
        lines.append("CLUBS AJOUTÉS : " + (", ".join(candidate.added_club_ids) or "aucun"))
        lines.append("CHANGEMENTS DE POSITION :")
        if candidate.position_changes:
            for club_id, (before, after) in candidate.position_changes.items():
                lines.append(f"  {names.get(club_id, club_id)} : {before or 'hors sac'} → {after or 'hors sac'}")
        else:
            lines.append("  aucun")

        profiles = (("PROFIL D’ATTAQUE", {"power", "control", "spin"}),
                    ("PROFIL D’ATTERRISSAGE", set(METRIC_LABELS) - {"power", "control", "spin"}))
        gains: list[str] = []
        losses: list[str] = []
        unchanged: list[str] = []
        unknown: list[str] = []
        values = candidate.metric_values_from_reference or {}
        for heading, metrics in profiles:
            selected = [(key, value) for key, value in values.items() if key.rsplit(".", 1)[-1] in metrics]
            if not selected:
                continue
            lines.extend(("", heading))
            for key, value in selected:
                step_id, metric = key.split(".", 1)
                before, after = value.get("before"), value.get("after")
                label = f"{step_labels.get(step_id, step_id)} / {_metric_label(metric)}"
                if before is None or after is None:
                    line = f"{label} : inconnu"
                    unknown.append(label)
                else:
                    delta = after - before
                    sign = "=" if delta == 0 else f"{delta:+g}"
                    line = f"{label} : {before:g} → {after:g} ({sign})"
                    (gains if delta > 0 else losses if delta < 0 else unchanged).append(
                        f"{label} {sign}{_metric_unit(metric)}"
                    )
                lines.append("  " + line)
        for heading, items in (("GAINS", gains), ("PERTES", losses), ("INCHANGÉ", unchanged), ("INCONNU", unknown)):
            lines.extend(("", heading))
            lines.extend((f"- {item}" for item in items) if items else ("- aucun",))
        if candidate.gained_contribution_ids:
            lines.extend(("", "CAPACITÉS GAGNÉES", *(f"- {item}" for item in candidate.gained_contribution_ids)))
        if candidate.lost_contribution_ids:
            lines.extend(("", "CAPACITÉS PERDUES", *(f"- {item}" for item in candidate.lost_contribution_ids)))
        return "\n".join(lines)

    def _step_content(
        self,
        candidate: StrategyCandidateResult,
        step_id: str,
        label: str,
        step_labels: Mapping[str, str],
    ) -> str:
        lines = [label, "=" * len(label)]
        for club in candidate.clubs:
            step = next(item for item in club.steps if item.step_id == step_id)
            active_labels = ", ".join(step_labels.get(item, item) for item in club.active_steps) or "aucune"
            support_labels = ", ".join(step_labels.get(item, item) for item in club.support_steps) or "aucune"
            lines.extend((
                "",
                f"Position {club.position} — {club.club_name} — niveau {club.level} — rôle {ROLE_LABELS[club.role]}",
                f"Étapes actives : {active_labels}",
                f"Étapes soutenues : {support_labels}",
            ))
            step_position = next(index for index, item in enumerate(club.steps) if item.step_id == step_id)
            previous = club.steps[step_position - 1] if step_position else None
            if previous is not None and _same_values(previous, step):
                lines.append("Valeurs identiques à l’étape précédente.")
            else:
                lines.extend(_stat_lines(step))
                if step.additional_metrics:
                    relevant = {
                        metric: value for metric, value in step.additional_metrics.items()
                        if step.metric_relevance.get(metric) in {"objective", "constraint"}
                    }
                    descriptive = {
                        metric: value for metric, value in step.additional_metrics.items()
                        if step.metric_relevance.get(metric) == "descriptive"
                    }
                    if relevant:
                        lines.append("Métriques pertinentes activées :")
                        lines.extend(
                            f"  {_metric_label(metric)} : {value:g}{_metric_unit(metric)}"
                            for metric, value in sorted(relevant.items())
                        )
                    if descriptive:
                        lines.append("Contributions calculées, seulement descriptives :")
                        lines.extend(
                            f"  {_metric_label(metric)} : {value:g}{_metric_unit(metric)}"
                            for metric, value in sorted(descriptive.items())
                        )
        return "\n".join(lines)

    def _synergies(self, candidate: StrategyCandidateResult, step_labels: Mapping[str, str]) -> str:
        counterfactuals = {item.club_id: item for item in candidate.support_counterfactuals}
        club_names = {item.club_id: item.club_name for item in candidate.clubs}
        lines = ["Pourquoi ce club est présent ?", "=" * 31]
        for club in candidate.clubs:
            lines.extend(("", f"{club.club_name} — {ROLE_LABELS[club.role]}"))
            if club.role == "neutral":
                lines.append("Aucun effet différenciant observé dans ce sac.")
                continue
            sent = _unique_contributions(item for step in club.steps for item in step.contributions_sent)
            if sent:
                lines.append("Contributions envoyées :")
                lines.extend(f"  {_contribution_line(item, club_names)}" for item in sent)
            received = _unique_contributions(item for step in club.steps for item in step.contributions_received)
            if received:
                lines.append("Contributions reçues :")
                lines.extend(f"  {_contribution_line(item, club_names)}" for item in received)
            counterfactual = counterfactuals.get(club.club_id)
            if counterfactual and counterfactual.changes:
                lines.append("Perte observée sans ce club :")
                for change in counterfactual.changes:
                    values = ", ".join(
                        f"{_metric_label(metric)} {value:+g}{_metric_unit(metric)}"
                        for metric, value in change.lost_metrics_if_removed.items()
                    )
                    if values:
                        target_name = club_names.get(change.target_club_id, change.target_club_id)
                        lines.append(f"  {step_labels.get(change.step_id, change.step_id)} / {target_name} : {values}")
        return "\n".join(lines)

    def _technical(self, candidate: StrategyCandidateResult, step_labels: Mapping[str, str]) -> str:
        lines = [
            f"Origine : {candidate.origin}",
            f"replacement_depth : {candidate.replacement_depth}",
            f"result_status : {candidate.result_status}",
            f"reason_for_display : {candidate.reason_for_display}",
            "Gains : " + (", ".join(candidate.gains) or "aucun"),
            "Pertes : " + (", ".join(candidate.losses) or "aucune"),
            "Inconnus : " + (", ".join(candidate.unknowns) or "aucun"),
            "Exigences",
        ]
        if candidate.metric_deltas_from_reference is not None:
            lines.extend((
                "",
                "Différence avec le sac actuel",
                "Clubs retirés : " + (", ".join(candidate.removed_club_ids) or "aucun"),
                "Clubs ajoutés : " + (", ".join(candidate.added_club_ids) or "aucun"),
                *(
                    f"- {metric} : {'indéterminé' if delta is None else f'{delta:+g}'}"
                    for metric, delta in candidate.metric_deltas_from_reference.items()
                ),
                "Contributions gagnées : " + (", ".join(candidate.gained_contribution_ids) or "aucune"),
                "Contributions perdues : " + (", ".join(candidate.lost_contribution_ids) or "aucune"),
                "",
            ))
        for item in candidate.requirements:
            missing = f" — données manquantes : {', '.join(item.missing_data)}" if item.missing_data else ""
            lines.append(f"- {step_labels.get(item.step_id, item.step_id)} : {item.description} = {item.status}{missing}")
        lines.append("\nCapacités et effets par club")
        for club in candidate.clubs:
            lines.append(f"\n{club.club_name}")
            for step in club.steps:
                label = step_labels.get(step.step_id, step.step_id)
                lines.append(f"  {label}")
                lines.append("    Capacités actives : " + (", ".join(step.active_abilities) or "aucune"))
                lines.append("    Capacités sans effet : " + (", ".join(step.abilities_without_effect) or "aucune"))
                lines.append("    Capacités non résolues : " + (", ".join(step.unresolved_abilities) or "aucune"))
                scheduled = tuple(
                    effect_id
                    for item in (*step.contributions_received, *step.contributions_sent)
                    for effect_id in item.scheduled_effect_ids
                )
                lines.append("    Effets différés planifiés : " + (", ".join(dict.fromkeys(scheduled)) or "aucun"))
                for fact in step.amplifications:
                    magnitude = (f"{fact['original']:g} → {fact['amplified']:g} {fact.get('metric', '')}"
                                 if "original" in fact else "effet final non résolu")
                    lines.append(f"    Amplification ×{fact.get('multiplier', 1):g} : {fact.get('target_ability_source')} ; "
                                 f"{magnitude} ; cible finale : {fact.get('final_target') or 'prochain club compatible / indéterminée'} ; "
                                 f"statut : {fact.get('status')}")
                    if fact.get("value_kind") == "model_magnitude":
                        lines.append(f"      Magnitude native {fact['original']:g} + contribution supplémentaire "
                                     f"{fact['additional']:g} = {fact['amplified']:g} ; valeur calculée du modèle, "
                                     "sans conversion physique ni plafond 100.")
        return "\n".join(lines)

    @staticmethod
    def _warnings(result: StrategyOptimizationResult) -> str:
        lines = [
            "Résultats à interpréter avec prudence",
            "• La portée réelle n’est pas encore modélisée.",
            "• La réussite du putt n’est pas modélisée.",
            "• Seules les métriques actuellement calculables sont comparées.",
            "• Recherche intelligente réduite : de nombreuses combinaisons pertinentes ont été testées, mais l’optimum absolu n’est pas garanti.",
        ]
        if result.search.safety_limit_reached:
            lines.append("• La limite de sécurité a été atteinte avant la fin de la recherche réduite.")
        if result.excluded_clubs:
            lines.append("• Clubs possédés exclus avant l’analyse :")
            lines.extend(f"  - {item.club_name} : {item.reason}" for item in result.excluded_clubs)
        if result.empirical_reference:
            lines.append("• " + result.empirical_reference.statement)
        if result.reference_brand_violations:
            lines.append(
                "• Le sac de référence contient des clubs hors marques autorisées : "
                + ", ".join(result.reference_brand_violations)
                + ". Il reste visible uniquement pour la comparaison."
            )
        if result.inventory_changes.added_club_ids:
            lines.append("• Nouveau(x) club(s) détecté(s) depuis la précédente analyse :")
            lines.extend(f"  - {item.club_name} — niveau {item.level}" for item in result.new_club_diagnostics)
        if not result.criteria_satisfied:
            lines.append("• Aucun sac ne satisfait actuellement ces critères ; les solutions les plus proches sont affichées sans modifier vos minimums.")
        if result.reference_is_admissible and not result.improvement_without_loss_found and result.comparison_reference:
            lines.append("• Aucune amélioration sans perte calculable trouvée.")
        if result.inferior_results_hidden_count:
            lines.append(f"• {result.inferior_results_hidden_count} résultat(s) strictement inférieur(s) masqué(s).")
        return "\n".join(lines)

    @staticmethod
    def _search_information(result: StrategyOptimizationResult) -> str:
        total = result.search.total_seconds
        brands = ", ".join(result.allowed_brand_names) if result.allowed_brands else "Toutes"
        replacement_type = (
            "Même type" if result.replacement_type_policy == "same_type" else "Tous les types admissibles"
        )
        return "\n".join((
            "Informations sur la recherche",
            f"Marques : {brands}",
            f"Origine de la contrainte : {result.admissibility_provenance}",
            f"Type de remplaçant : {replacement_type}",
            f"Remplacements autorisés : jusqu’à {result.search.replacement_depth}",
            f"Résultats inférieurs masqués : {result.inferior_results_hidden_count}",
            f"Candidats générés : {result.search.reduced_candidates_generated}",
            f"Candidats évalués : {result.search.candidates_evaluated}",
            f"Doublons éliminés : {result.search.candidate_result_duplicates_removed}",
            f"Durée mesurée : {total:.2f} s",
            f"Génération : {result.search.generation_seconds:.2f} s",
            f"Moteur : {result.search.evaluation_seconds:.2f} s",
            f"Comparaison et détails : {result.search.comparison_seconds:.2f} s",
            f"Limite de sécurité atteinte : {'oui' if result.search.safety_limit_reached else 'non'}",
            f"Statut du résultat : {'MAXIMUM PROUVÉ' if result.search.optimality_status == 'maximum_proven' else 'MEILLEUR TROUVÉ'}",
            f"Compositions : {result.search.compositions_generated}",
            f"Compositions théoriques : {result.search.theoretical_compositions}",
            f"Compositions évaluées : {result.search.compositions_evaluated}",
            f"Affectations actives : {result.search.active_assignments_considered} / {result.search.active_assignments_theoretical}",
            f"Supports considérés : {result.search.support_clubs_considered}",
            f"Permutations théoriques : {result.search.permutations_theoretical}",
            f"Permutations prouvées équivalentes : {result.search.permutations_proven_equivalent}",
            f"Permutations structurellement distinctes : {result.search.permutations_structurally_distinct}",
            f"Cache d’évaluation : {result.search.evaluation_cache_hits} hits / {result.search.evaluation_cache_misses} misses",
            f"Origines : {dict(result.search.origin_counts or {})}",
            f"Candidats issus de sacs enregistrés injectés : {result.search.saved_bag_candidates_injected}",
            f"Solutions de session injectées : {result.search.known_candidates_injected}",
            f"Suppressions par raison : {dict(result.search.removal_reasons or {})}",
            f"Complétude locale : {result.search.local_search_completeness}",
            f"Inventaire utilisé : {result.inventory_owned_count} clubs possédés — observation {result.inventory_observed_at or 'inconnue'}",
        ))


class StrategyOptimizerGuiController:
    """Run the optimizer off the UI thread and marshal callbacks through schedule."""

    def __init__(
        self,
        optimizer: StrategyOptimizer,
        *,
        schedule: Callable[[Callable[[], None]], None],
        on_state: Callable[[bool, str], None],
        on_success: Callable[[StrategyOptimizationResult, float], None],
        on_error: Callable[[str, str], None],
        thread_factory: Callable[..., Thread] = Thread,
    ) -> None:
        self.optimizer = optimizer
        self.schedule = schedule
        self.on_state = on_state
        self.on_success = on_success
        self.on_error = on_error
        self.thread_factory = thread_factory
        self.running = False

    def start(self, options: OptimizationGuiOptions) -> bool:
        if self.running:
            return False
        try:
            request = options.to_request()
        except (ValueError, StrategyError) as error:
            self.on_error(str(error), error.__class__.__name__)
            return False
        self.running = True
        self.on_state(True, "Analyse en cours…")

        def work() -> None:
            started = datetime.now()
            try:
                result = self.optimizer.optimize(request)
                elapsed = (datetime.now() - started).total_seconds()
            except Exception as error:  # converted to a safe French UI message
                self.schedule(lambda captured=error: self._finish_error(captured))
                return
            self.schedule(lambda captured=result, seconds=elapsed: self._finish_success(captured, seconds))

        self.thread_factory(target=work, daemon=True).start()
        return True

    def _finish_success(self, result: StrategyOptimizationResult, elapsed: float) -> None:
        self.running = False
        self.on_state(False, f"Analyse terminée en {elapsed:.2f} s.")
        if not result.retained_results:
            self.on_error("Aucune proposition n’a pu être conservée avec les données disponibles.", "empty_result")
            return
        self.on_success(result, elapsed)

    def _finish_error(self, error: Exception) -> None:
        self.running = False
        self.on_state(False, "L’analyse n’a pas pu être terminée.")
        self.on_error(french_optimizer_error(error), f"{error.__class__.__name__}: {error}")


def french_optimizer_error(error: Exception) -> str:
    if isinstance(error, FileNotFoundError):
        return "Les données nécessaires sont introuvables. Vérifiez que le projet a été installé complètement."
    if isinstance(error, sqlite3.Error):
        return "La base de données de l’inventaire est indisponible ou endommagée."
    if isinstance(error, StrategyError):
        return "La stratégie ou la variante sélectionnée n’est pas compatible."
    if isinstance(error, StrategyOptimizationError):
        text = str(error)
        if "eligible owned clubs" in text:
            return "L’inventaire ne contient pas assez de clubs possédés avec un niveau connu."
        return "L’optimisation ne peut pas démarrer avec les données actuelles : " + text
    return "Une erreur de calcul est survenue. Vos données n’ont pas été modifiées."


def export_result_json(result: StrategyOptimizationResult, destination: str | Path) -> Path:
    path = Path(destination)
    path.write_text(render_strategy_optimization_json(result) + "\n", encoding="utf-8")
    return path


def export_result_text(result: StrategyOptimizationResult, destination: str | Path) -> Path:
    path = Path(destination)
    path.write_text(render_strategy_optimization(result) + "\n", encoding="utf-8")
    return path


def suggested_export_name(strategy_id: str, extension: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M")
    return f"resultats_{strategy_id}_{timestamp}.{extension.lstrip('.')}"


class StrategyOptimizerApp:
    """Visual bag builder with secondary tools and on-demand technical detail."""

    def __init__(
        self,
        *,
        user_data_path: str | Path = "data/pga_shootout.sqlite",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        registry_path: str | Path = "data/strategies/strategies.json",
        root=None,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.user_data_path = Path(user_data_path)
        self.catalog_path = Path(catalog_path)
        self.registry_path = Path(registry_path)
        self.presenter = StrategyOptimizerPresenter.load(self.registry_path)
        self.optimizer = StrategyOptimizer(
            user_data_path=self.user_data_path,
            catalog_path=self.catalog_path,
            strategy_registry_path=self.registry_path,
        )
        self.root = root or tk.Tk()
        self.root.title("PGA Shootout — Optimiser mes sacs")
        self.root.geometry("1480x900")
        self.root.minsize(1100, 700)
        self.result: StrategyOptimizationResult | None = None
        self.presentation: OptimizationPresentation | None = None
        self.last_technical_error: str | None = None
        self.inventory_windows: list[InventoryEditorApp] = []
        choices = self.presenter.strategy_choices()
        if not choices:
            raise StrategyError("Aucune stratégie disponible")
        self.strategy_by_label = {item.label: item.identifier for item in choices}
        self.strategy_name = tk.StringVar(value=choices[0].label)
        self.variant_name = tk.StringVar(value="Aucune variante")
        self.real_mode = tk.BooleanVar(value=True)
        self.scenario_level = tk.StringVar(value="12")
        self.limit = tk.StringVar(value="5")
        self.max_evaluations = tk.StringVar(value="2000")
        catalog_document = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        canonical_brands = sorted({
            (str(club["brand"]["name"]), str(club["brand"]["id"]))
            for club in catalog_document["clubs"].values()
        })
        self.brand_id_by_label = dict(canonical_brands)
        self.all_brands = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Choisissez une stratégie puis lancez l’analyse.")
        self.show_advanced = tk.BooleanVar(value=False)
        bundle = load_user_data(self.user_data_path)
        self.reference_by_label = {"Aucun": None, **{bag.name: bag.identifier for bag in bundle.bags}}
        self.reference_name = tk.StringVar(value="Aucun")
        self.search_mode_by_label = {
            "Construire mon sac": "build_from_scratch",
            "Optimiser autour de mes clubs": "interactive_builder",
            "Chercher de nouveaux sacs": "global",
            "Améliorer un de mes sacs": "improve_bag",
            "Remplacer un club de mon sac": "replace_club",
            "Optimiser autour d’un club": "around_club",
            "Tester un nouveau club dans mes sacs": "test_new_club",
        }
        self.search_mode_name = tk.StringVar(value="Construire mon sac")
        self.target_bag_by_label = {"Aucun": None, **{_bag_label(bag): bag.identifier for bag in bundle.bags}}
        self.target_bag_name = tk.StringVar(value="Aucun")
        owned = tuple(item for item in bundle.inventory.entries if item.unlocked and item.current_level is not None)
        self.fixed_club_by_label = {item.display_name: item.club_id for item in owned}
        self.fixed_club_name = tk.StringVar(value=next(iter(self.fixed_club_by_label), ""))
        self.fixed_step_name = tk.StringVar(value="")
        self.replacement_depth = tk.StringVar(value="Jusqu’à 1 remplacement")
        self.replacement_type_by_label = {
            "Même type que le club actuel": "same_type",
            "Tous les types admissibles": "all_types",
        }
        self.replacement_type_name = tk.StringVar(value="Même type que le club actuel")
        self.keep_current_putter = tk.BooleanVar(value=False)
        self.lock_required_positions = tk.BooleanVar(value=False)
        self.last_detected_club_ids: tuple[str, ...] = ()
        self.chosen_club_rows: list[dict[str, object]] = []
        self.step_minimum_vars: dict[str, dict[str, object]] = {}
        self._callback_queue: Queue[Callable[[], None]] = Queue()
        self.controller = StrategyOptimizerGuiController(
            self.optimizer,
            schedule=self._callback_queue.put,
            on_state=self._on_state,
            on_success=self._on_success,
            on_error=self._on_error,
        )
        self._build()
        self._refresh_inventory_choices()
        self.root.after(25, self._poll_callbacks)
        self._refresh_variants()
        self._toggle_mode()
        self._toggle_search_mode()

    def _build(self) -> None:
        from .optimizer_cards import ACCENT, BG, INK, GraphicAssets, ScrollArea
        tk, ttk = self.tk, self.ttk
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=BG, foreground=INK)
        style.configure("TButton", padding=(12, 7))
        style.configure("Primary.TButton", background=ACCENT, foreground="white", font=("Segoe UI", 11, "bold"), padding=(14, 13))
        style.map("Primary.TButton", background=[("active", "#0B5744"), ("disabled", "#9CAFA7")])
        style.configure("TCombobox", padding=5, fieldbackground="white", background="white", bordercolor="#CBD8D1")
        style.map("TCombobox", fieldbackground=[("readonly", "white")], selectbackground=[("readonly", "white")], selectforeground=[("readonly", INK)])
        self.root.configure(bg=BG)
        self.root.title("PGA Shootout — Construire mon sac")
        self.root.minsize(1180, 760)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = tk.Frame(self.root, bg=INK)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="PGA  /  SHOOTOUT", bg=INK, fg="#9BD6BD", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(24, 18), pady=20)
        tk.Label(header, text="Construire mon sac", bg=INK, fg="white", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Button(header, text="Mon inventaire", command=self._open_inventory).pack(side="right", padx=(8, 24))
        ttk.Button(header, text="Outils", command=lambda: self.tools_window.deiconify()).pack(side="right")
        content = ttk.Frame(self.root)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(content, width=330)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(16, 0), pady=16)
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(0, weight=1)
        sidebar.columnconfigure(0, weight=1)
        self.form_scroll = ScrollArea(sidebar)
        self.form_scroll.frame.grid(row=0, column=0, sticky="nsew")
        form = self.form_scroll.body
        form.columnconfigure(0, weight=1)
        ttk.Label(form, text="01  VOTRE STRATÉGIE", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 8))
        self.strategy_box = ttk.Combobox(form, textvariable=self.strategy_name, values=tuple(self.strategy_by_label), state="readonly")
        self.strategy_box.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.strategy_box.bind("<<ComboboxSelected>>", lambda _event: self._strategy_changed())
        self.builder_frame = ttk.Frame(form)
        self.builder_frame.grid(row=2, column=0, sticky="ew", pady=(24, 0), padx=(0, 10))
        ttk.Label(self.builder_frame, text="02  VOS CLUBS", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.chosen_rows_frame = ttk.Frame(self.builder_frame)
        self.chosen_rows_frame.pack(fill="x")
        self.add_club_button = ttk.Button(self.builder_frame, text="+ Ajouter un club", command=self._add_chosen_club)
        self.add_club_button.pack(anchor="w", pady=(6, 0))
        self.objectives_frame = ttk.Frame(form)
        self.objectives_frame.grid(row=3, column=0, sticky="ew", pady=(24, 0), padx=(0, 10))
        brands = ttk.Frame(form)
        brands.grid(row=4, column=0, sticky="ew", pady=(20, 0), padx=(0, 10))
        ttk.Label(brands, text="Marques autorisées", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Checkbutton(brands, text="Toutes les marques", variable=self.all_brands, command=self._toggle_all_brands).pack(anchor="w", pady=5)
        self.brand_list = tk.Listbox(brands, selectmode="multiple", exportselection=False, height=5, relief="flat", font=("Segoe UI", 10), selectbackground=ACCENT)
        for brand in self.brand_id_by_label:
            self.brand_list.insert("end", brand)
        self.brand_list.bind("<<ListboxSelect>>", self._brand_selection_changed)
        self.analyze_button = ttk.Button(form, text="OPTIMISER MON SAC", command=self._start, style="Primary.TButton")
        self.analyze_button.grid(row=5, column=0, sticky="ew", pady=(24, 12), padx=(0, 10))
        ttk.Checkbutton(form, text="Options avancées", variable=self.show_advanced, command=self._toggle_advanced).grid(row=6, column=0, sticky="w", pady=(0, 8))
        self.advanced_frame = ttk.Frame(form)
        self.advanced_frame.columnconfigure(0, weight=1)
        self.advanced_roles = ttk.Frame(self.advanced_frame)
        self.advanced_roles.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.advanced_objectives = ttk.Frame(self.advanced_frame)
        self.advanced_objectives.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(self.advanced_frame, text="Contexte explicite").grid(row=2, column=0, sticky="w")
        self.variant_box = ttk.Combobox(self.advanced_frame, textvariable=self.variant_name, state="readonly")
        self.variant_box.grid(row=3, column=0, sticky="ew", pady=4)
        modes = ttk.Frame(self.advanced_frame)
        modes.grid(row=4, column=0, sticky="ew")
        ttk.Radiobutton(modes, text="Niveaux réels", variable=self.real_mode, value=True, command=self._toggle_mode).pack(side="left")
        ttk.Radiobutton(modes, text="Scénario", variable=self.real_mode, value=False, command=self._toggle_mode).pack(side="left")
        self.scenario_entry = ttk.Spinbox(self.advanced_frame, from_=1, to=12, textvariable=self.scenario_level, width=5)
        self.scenario_entry.grid(row=5, column=0, sticky="w", pady=4)
        ttk.Label(self.advanced_frame, text="Résultats / limite de recherche").grid(row=6, column=0, sticky="w")
        limits = ttk.Frame(self.advanced_frame)
        limits.grid(row=7, column=0, sticky="w", pady=4)
        ttk.Combobox(limits, textvariable=self.limit, values=("5", "10", "20"), state="readonly", width=5).pack(side="left")
        ttk.Entry(limits, textvariable=self.max_evaluations, width=10).pack(side="left", padx=8)
        self._add_chosen_club()
        self.progress = ttk.Progressbar(form, mode="indeterminate")
        self.progress.grid(row=8, column=0, sticky="ew", pady=8, padx=(0, 10))
        self.progress.grid_remove()

        results = ttk.Frame(content)
        results.grid(row=0, column=1, sticky="nsew", pady=16)
        results.rowconfigure(2, weight=1)
        results.columnconfigure(0, weight=1)
        self.results_heading = tk.StringVar(value="Votre prochain sac commence ici")
        ttk.Label(results, textvariable=self.results_heading, font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(0, 8))
        self.warning_summary = tk.StringVar(value="Choisissez une stratégie et un club, puis lancez la recherche.")
        self.warning_button = ttk.Button(results, textvariable=self.warning_summary, command=self._show_warnings)
        self.warning_button.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.cards_scroll = ScrollArea(results)
        self.cards_scroll.frame.grid(row=2, column=0, sticky="nsew")
        self.cards = []
        tk.Label(self.cards_scroll.body, text="Un club au cœur du jeu.\nCinq clubs qui travaillent ensemble.", font=("Segoe UI", 23, "bold"), fg=INK, bg=BG, justify="left", anchor="w").pack(fill="x", padx=35, pady=(95, 20))
        tk.Label(self.cards_scroll.body, text="1  Choisissez votre club principal\n2  Ajoutez des clubs obligatoires si vous le souhaitez\n3  Comparez les rôles, les gains et les compromis", font=("Segoe UI", 12), fg="#596B65", bg=BG, justify="left", anchor="w").pack(fill="x", padx=35)
        footer = ttk.Frame(self.root, padding=(16, 8))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Label(footer, textvariable=self.status, wraplength=1000).pack(side="left")
        self.search_info_button = ttk.Button(footer, text="Recherche", command=self._show_search_info, state="disabled")
        self.search_info_button.pack(side="right")
        self.assets = GraphicAssets(self.root, json.loads(self.catalog_path.read_text(encoding="utf-8")))

        # Existing tools and presenter remain secondary, in separate windows.
        self.tools_window = tk.Toplevel(self.root)
        self.tools_window.title("Outils — parcours historiques et exports")
        self.tools_window.geometry("570x720")
        self.tools_window.withdraw()
        self.tools_window.protocol("WM_DELETE_WINDOW", self.tools_window.withdraw)
        self.tools_scroll = ScrollArea(self.tools_window)
        self.tools_scroll.frame.pack(fill="both", expand=True, padx=18, pady=18)
        tools = self.tools_scroll.body
        def selector(label, variable, values):
            ttk.Label(tools, text=label).pack(anchor="w", pady=(8, 2))
            box = ttk.Combobox(tools, textvariable=variable, values=values, state="readonly", width=45)
            box.pack(fill="x")
            return box
        self.search_mode_box = selector("Parcours (Construire mon sac par défaut)", self.search_mode_name, tuple(self.search_mode_by_label))
        self.search_mode_box.bind("<<ComboboxSelected>>", lambda _: self._toggle_search_mode())
        self.target_bag_box = selector("Sac enregistré", self.target_bag_name, tuple(self.target_bag_by_label))
        self.fixed_club_box = selector("Club à tester", self.fixed_club_name, tuple(self.fixed_club_by_label))
        self.fixed_step_box = selector("Rôle du club testé", self.fixed_step_name, ())
        self.depth_box = selector("Profondeur", self.replacement_depth, ("Jusqu’à 1 remplacement", "Jusqu’à 2 remplacements"))
        self.replacement_type_box = selector("Type de remplacement", self.replacement_type_name, tuple(self.replacement_type_by_label))
        self.reference_box = selector("Référence empirique facultative", self.reference_name, tuple(self.reference_by_label))
        ttk.Button(tools, text="Définir le sac comme référence", command=self._mark_reference).pack(fill="x", pady=4)
        ttk.Button(tools, text="Utiliser les rôles de la référence", command=self._use_reference_roles).pack(fill="x")
        self.legacy_constraints = ttk.Frame(tools)
        self.required_list = tk.Listbox(self.legacy_constraints, selectmode="multiple", exportselection=False)
        self.excluded_list = tk.Listbox(self.legacy_constraints, selectmode="multiple", exportselection=False)
        self.test_new_button = ttk.Button(tools, text="Tester le nouveau club", command=self._test_detected_club, state="disabled")
        self.test_new_button.pack(pady=8)
        ttk.Button(tools, text="Lancer le parcours sélectionné", command=self._start).pack()
        self.export_json_button = ttk.Button(tools, text="Exporter les résultats JSON", command=self._export_json, state="disabled")
        self.export_text_button = ttk.Button(tools, text="Exporter les résultats texte", command=self._export_text, state="disabled")
        self.export_json_button.pack(fill="x", pady=(12, 4))
        self.export_text_button.pack(fill="x")
        self.detail_window = tk.Toplevel(self.root)
        self.detail_window.title("Détail technique — calculs et contributions")
        self.detail_window.geometry("1050x720")
        self.detail_window.withdraw()
        self.detail_window.protocol("WM_DELETE_WINDOW", self.detail_window.withdraw)
        self.detail_title = tk.StringVar()
        ttk.Label(self.detail_window, textvariable=self.detail_title, font=("Segoe UI", 12, "bold"), wraplength=950).pack(fill="x", padx=15, pady=12)
        self.notebook = ttk.Notebook(self.detail_window)
        self.notebook.pack(fill="both", expand=True, padx=15)
        bar = ttk.Frame(self.detail_window, padding=12)
        bar.pack(fill="x")
        self.copy_button = ttk.Button(bar, text="Copier le résumé", command=self._copy_summary, state="disabled")
        self.save_bag_button = ttk.Button(bar, text="Enregistrer ce sac", command=self._save_selected_bag, state="disabled")
        self.replace_reference_button = ttk.Button(bar, text="Remplacer la référence", command=self._replace_reference, state="disabled")
        for button in (self.copy_button, self.save_bag_button, self.replace_reference_button):
            button.pack(side="left", padx=5)
        self._visual_selected_index = None
        self._toggle_all_brands()

    def _poll_callbacks(self) -> None:
        """Execute worker completions exclusively from Tk's main thread."""

        try:
            while True:
                self._callback_queue.get_nowait()()
        except Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(25, self._poll_callbacks)

    def _refresh_variants(self) -> None:
        strategy_id = self.strategy_by_label[self.strategy_name.get()]
        choices = self.presenter.variant_choices(strategy_id)
        self.variant_by_label = {item.label: item.identifier for item in choices}
        self.variant_box.configure(values=tuple(self.variant_by_label))
        self.variant_name.set(choices[0].label)
        strategy = self.presenter.registry.get(strategy_id)
        self.fixed_step_by_label = {step.name: step.identifier for step in strategy.sequence}
        self.fixed_step_box.configure(values=tuple(self.fixed_step_by_label))
        self.fixed_step_name.set(next(iter(self.fixed_step_by_label), ""))
        self._refresh_chosen_roles()
        self._rebuild_objectives()

    def _strategy_changed(self) -> None:
        self._refresh_variants()
        self._toggle_search_mode()

    def _role_choices(self) -> dict[str, str]:
        strategy_id = self.strategy_by_label[self.strategy_name.get()]
        strategy = self.presenter.registry.get(strategy_id)
        result = {"Automatique": "auto", "Support uniquement": "support"}
        result.update({f"Actif — {step.name}": step.identifier for step in strategy.sequence})
        return result

    def _add_chosen_club(self, club_id: str | None = None, role: str = "auto") -> None:
        if len(self.chosen_club_rows) >= 5:
            self.status.set("Un sac contient cinq clubs au maximum.")
            return
        label = next((name for name, value in self.fixed_club_by_label.items() if value == club_id), "")
        roles = self._role_choices()
        row_frame = self.ttk.Frame(self.chosen_rows_frame)
        row_frame.pack(fill="x", pady=4)
        row_label = self.ttk.Label(row_frame, text="Club principal" if not self.chosen_club_rows else "Club obligatoire")
        row_label.pack(anchor="w", pady=(0, 3))
        club_var = self.tk.StringVar(value=label)
        role_var = self.tk.StringVar(value=next((name for name, value in roles.items() if value == role), "Automatique"))
        position_var = self.tk.StringVar(value="Libre")
        club_box = self.ttk.Combobox(row_frame, textvariable=club_var, values=tuple(self.fixed_club_by_label), state="readonly", width=21)
        club_box.pack(side="left", fill="x", expand=True)
        advanced_row = self.ttk.Frame(self.advanced_roles)
        advanced_row.pack(fill="x", pady=5)
        self.ttk.Label(advanced_row, textvariable=club_var).pack(anchor="w")
        role_box = self.ttk.Combobox(advanced_row, textvariable=role_var, values=tuple(roles), state="readonly", width=20)
        role_box.pack(side="left")
        position_box = self.ttk.Combobox(advanced_row, textvariable=position_var, values=("Libre", "1", "2", "3", "4", "5"), state="readonly", width=5)
        position_box.pack(side="left", padx=3)
        row = {"frame": row_frame, "club_var": club_var, "role_var": role_var, "position_var": position_var,
               "club_box": club_box, "role_box": role_box, "position_box": position_box,
               "row_label": row_label, "advanced_row": advanced_row}
        if self.chosen_club_rows:
            self.ttk.Button(row_frame, text="×", width=2, command=lambda: self._remove_chosen_club(row)).pack(side="right", padx=(3, 0))
        self.chosen_club_rows.append(row)
        self.add_club_button.configure(state="disabled" if len(self.chosen_club_rows) == 5 else "normal")

    def _remove_chosen_club(self, row: dict[str, object]) -> None:
        row["frame"].destroy()
        row["advanced_row"].destroy()
        self.chosen_club_rows.remove(row)
        self.add_club_button.configure(state="normal")

    def _refresh_chosen_roles(self) -> None:
        roles = self._role_choices()
        for row in self.chosen_club_rows:
            current = str(row["role_var"].get())
            row["role_box"].configure(values=tuple(roles))
            if current not in roles:
                row["role_var"].set("Automatique")

    def _rebuild_objectives(self) -> None:
        for host in (self.objectives_frame, self.advanced_objectives):
            for child in host.winfo_children():
                child.destroy()
        self.step_minimum_vars = {}
        strategy = self.presenter.registry.get(self.strategy_by_label[self.strategy_name.get()])
        self.ttk.Label(self.objectives_frame, text="03  VOTRE OBJECTIF", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.ttk.Label(self.objectives_frame, text="Power maximale", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(5, 10))
        self.ttk.Label(self.objectives_frame, text="Minimums facultatifs pour le premier coup", wraplength=285).pack(anchor="w")
        for index, step in enumerate(strategy.sequence):
            host = self.objectives_frame if index == 0 else self.advanced_objectives
            if index:
                self.ttk.Label(host, text=step.name).pack(anchor="w", pady=(7, 3))
            values = {}
            metrics = ("power", "control") if step.function.identifier == "finish" else ("control", "spin")
            for metric in metrics:
                line = self.ttk.Frame(host)
                line.pack(fill="x", pady=3)
                self.ttk.Label(line, text=f"{METRIC_LABELS[metric]} minimum").pack(side="left")
                variable = self.tk.StringVar(value="Aucun")
                box = self.ttk.Combobox(line, textvariable=variable, values=("Aucun",), width=9)
                box.pack(side="right")
                values[metric] = (variable, box)
            self.step_minimum_vars[step.identifier] = values

    def _toggle_mode(self) -> None:
        self.scenario_entry.configure(state="disabled" if self.real_mode.get() else "normal")

    def _toggle_search_mode(self) -> None:
        mode = self.search_mode_by_label[self.search_mode_name.get()]
        self.target_bag_box.configure(state="disabled" if mode == "build_from_scratch" else "readonly")
        self.fixed_club_box.configure(state="readonly" if mode in {"replace_club", "around_club", "test_new_club"} else "disabled")
        self.fixed_step_box.configure(state="readonly" if mode == "around_club" else "disabled")
        self.analyze_button.configure(text="OPTIMISER MON SAC" if mode == "build_from_scratch" else "LANCER LE PARCOURS OUTILS")
        if mode != "build_from_scratch":
            self.status.set("Parcours secondaire actif : " + self.search_mode_name.get())
        else:
            self.status.set("Choisissez un club principal. Vos niveaux réels seront utilisés.")

    def _refresh_inventory_choices(self) -> None:
        bundle = load_user_data(self.user_data_path)
        previous_bag = self.target_bag_name.get()
        previous_club = self.fixed_club_name.get()
        previous_ids = set(self.fixed_club_by_label.values())
        self.target_bag_by_label = {"Aucun": None, **{_bag_label(bag): bag.identifier for bag in bundle.bags}}
        owned = tuple(item for item in bundle.inventory.entries if item.unlocked and item.current_level is not None)
        self.fixed_club_by_label = {item.display_name: item.club_id for item in owned}
        self.target_bag_box.configure(values=tuple(self.target_bag_by_label))
        self.fixed_club_box.configure(values=tuple(self.fixed_club_by_label))
        for row in self.chosen_club_rows:
            row["club_box"].configure(values=tuple(self.fixed_club_by_label))
        for widget in (self.required_list, self.excluded_list):
            selected = {widget.get(index) for index in widget.curselection()}
            widget.delete(0, "end")
            for label in self.fixed_club_by_label:
                widget.insert("end", label)
                if label in selected:
                    widget.selection_set(widget.size() - 1)
        self.target_bag_name.set(previous_bag if previous_bag in self.target_bag_by_label else "Aucun")
        self.fixed_club_name.set(previous_club if previous_club in self.fixed_club_by_label else next(iter(self.fixed_club_by_label), ""))
        detected = tuple(sorted(set(self.fixed_club_by_label.values()) - previous_ids))
        if detected:
            self.last_detected_club_ids = detected
            names = [label for label, club_id in self.fixed_club_by_label.items() if club_id in detected]
            self.status.set("Nouveau club détecté : " + ", ".join(names) + " — vous pouvez le tester dans vos sacs.")
            self.test_new_button.configure(state="normal")

    def _test_detected_club(self) -> None:
        if not self.last_detected_club_ids:
            return
        club_id = self.last_detected_club_ids[-1]
        label = next((name for name, value in self.fixed_club_by_label.items() if value == club_id), None)
        mode_label = next(
            (name for name, value in self.search_mode_by_label.items() if value == "test_new_club"), None
        )
        if label is None or mode_label is None:
            return
        self.fixed_club_name.set(label)
        self.search_mode_name.set(mode_label)
        self._toggle_search_mode()
        self.status.set(f"{label} est prêt à être testé dans le sac sélectionné.")

    def _toggle_advanced(self) -> None:
        if self.show_advanced.get():
            self.advanced_frame.grid(row=7, column=0, sticky="ew", padx=(0, 10), pady=8)
        else:
            self.advanced_frame.grid_remove()

    def _toggle_all_brands(self) -> None:
        if self.all_brands.get():
            self.brand_list.selection_clear(0, "end")
            self.brand_list.configure(state="disabled")
            self.brand_list.pack_forget()
        else:
            self.brand_list.configure(state="normal")
            self.brand_list.pack(fill="x", pady=4)

    def _select_all_brands(self) -> None:
        self.all_brands.set(True)
        self._toggle_all_brands()

    def _clear_all_brands(self) -> None:
        self.all_brands.set(False)
        self._toggle_all_brands()
        self.brand_list.configure(state="normal")
        self.brand_list.selection_clear(0, "end")

    def _brand_selection_changed(self, _event=None) -> None:
        if self.brand_list.curselection():
            self.all_brands.set(False)
            self.brand_list.configure(state="normal")

    def _options(self) -> OptimizationGuiOptions:
        scenario = None
        if not self.real_mode.get():
            try:
                scenario = int(self.scenario_level.get())
            except ValueError as error:
                raise ValueError("Le niveau de scénario doit être un nombre entier.") from error
        try:
            limit = int(self.limit.get())
            max_evaluations = int(self.max_evaluations.get())
        except ValueError as error:
            raise ValueError("Les options numériques doivent contenir des nombres entiers.") from error
        required_labels = tuple(self.required_list.get(index) for index in self.required_list.curselection())
        excluded_labels = tuple(self.excluded_list.get(index) for index in self.excluded_list.curselection())
        required_ids = tuple(self.fixed_club_by_label[item] for item in required_labels)
        if self.all_brands.get():
            allowed_brands: tuple[str, ...] = ()
        else:
            brand_labels = tuple(self.brand_list.get(index) for index in self.brand_list.curselection())
            if not brand_labels:
                raise ValueError("Sélectionnez au moins une marque, ou choisissez Toutes les marques.")
            allowed_brands = tuple(self.brand_id_by_label[item] for item in brand_labels)
        target_bag_id = self.target_bag_by_label.get(self.target_bag_name.get())
        locked_positions: dict[int, str] = {}
        if self.lock_required_positions.get() and target_bag_id:
            bundle = load_user_data(self.user_data_path)
            bag = next(item for item in bundle.bags if item.identifier == target_bag_id)
            locked_positions = {
                position: club_id for position, club_id in enumerate(bag.club_ids, 1)
                if club_id in required_ids
            }
        search_mode = self.search_mode_by_label[self.search_mode_name.get()]
        if search_mode == "replace_club" and not target_bag_id:
            raise ValueError("Choisissez le sac réel dans lequel remplacer un club.")
        club_roles: dict[str, str] = {}
        metric_minimums: dict[str, dict[str, float]] = {}
        primary_step_id = None
        if search_mode in {"interactive_builder", "build_from_scratch"}:
            role_choices = self._role_choices()
            for row in self.chosen_club_rows:
                label = str(row["club_var"].get())
                if not label:
                    raise ValueError("Choisissez un club dans chaque ligne, ou supprimez la ligne facultative vide.")
                club_id = self.fixed_club_by_label[label]
                if club_id in club_roles:
                    raise ValueError(f"Le club {label} a été ajouté plusieurs fois.")
                club_roles[club_id] = role_choices[str(row["role_var"].get())]
                position = str(row["position_var"].get())
                if position != "Libre":
                    numeric = int(position)
                    if numeric in locked_positions:
                        raise ValueError(f"La position {numeric} est verrouillée deux fois.")
                    locked_positions[numeric] = club_id
            strategy = self.presenter.registry.get(self.strategy_by_label[self.strategy_name.get()])
            primary_step_id = next(
                step.identifier for step in strategy.sequence if step.function.identifier != "finish"
            )
            for step_id, values in self.step_minimum_vars.items():
                parsed: dict[str, float] = {}
                for metric, (variable, _box) in values.items():
                    raw = str(variable.get()).strip()
                    if raw and raw.casefold() != "aucun":
                        try:
                            parsed[metric] = float(raw.replace(",", "."))
                        except ValueError as error:
                            raise ValueError(f"Minimum invalide pour {METRIC_LABELS[metric]} : {raw}") from error
                if parsed:
                    metric_minimums[step_id] = parsed
        return OptimizationGuiOptions(
            strategy_id=self.strategy_by_label[self.strategy_name.get()],
            variant_id=self.variant_by_label[self.variant_name.get()],
            real_mode=self.real_mode.get(),
            scenario_level=scenario,
            limit=limit,
            max_evaluations=max_evaluations,
            reference_bag_id=None if search_mode == "build_from_scratch" else self.reference_by_label[self.reference_name.get()],
            search_mode=search_mode,
            target_bag_id=None if search_mode == "build_from_scratch" else target_bag_id,
            fixed_club_id=(
                self.fixed_club_by_label.get(self.fixed_club_name.get())
                if search_mode in {"around_club", "test_new_club"} else None
            ),
            replace_club_id=(
                self.fixed_club_by_label.get(self.fixed_club_name.get())
                if search_mode == "replace_club" else None
            ),
            replacement_depth=(
                2 if "2" in self.replacement_depth.get() else 1
            ),
            required_club_ids=required_ids,
            excluded_club_ids=tuple(self.fixed_club_by_label[item] for item in excluded_labels),
            locked_positions=locked_positions,
            keep_current_putter=self.keep_current_putter.get(),
            fixed_step_id=self.fixed_step_by_label.get(self.fixed_step_name.get()),
            club_roles=club_roles,
            metric_minimums=metric_minimums,
            primary_step_id=primary_step_id,
            allowed_brands=allowed_brands,
            replacement_type_policy=self.replacement_type_by_label[self.replacement_type_name.get()],
        )

    def _start(self) -> None:
        try:
            self._refresh_inventory_choices()
            options = self._options()
        except (ValueError, KeyError) as error:
            self._on_error(str(error), error.__class__.__name__)
            return
        self.controller.start(options)

    def _on_state(self, running: bool, message: str) -> None:
        self.analyze_button.configure(state="disabled" if running else "normal")
        if running:
            self.progress.grid()
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.grid_remove()
        self.status.set(message)

    def _on_success(self, result: StrategyOptimizationResult, _elapsed: float) -> None:
        from .optimizer_cards import render_cards, step_labels_for
        self.result = result
        self.presentation = self.presenter.present(result)
        self._visual_selected_index = None
        self.detail_window.withdraw()
        for step_id, metrics in (result.attainable_ranges or {}).items():
            for metric, values in metrics.items():
                entry = self.step_minimum_vars.get(step_id, {}).get(metric)
                if entry:
                    entry[1].configure(values=("Aucun", *(f"{value:g}" for value in values)))
        strategy = self.presenter.registry.get(result.strategy_id)
        labels = step_labels_for(strategy)
        self.cards = render_cards(self.cards_scroll.body, result, self.presentation, self.assets, labels, self._show_detail, self._save_card)
        self.cards_scroll.canvas.yview_moveto(0)
        self.results_heading.set(f"{len(result.retained_results)} propositions pour votre sac")
        partial = sum(bool(item.unresolved_abilities) for item in result.retained_results)
        limit = "Recherche limitée" if result.search.optimality_status != "maximum_proven" else "Maximum prouvé"
        qualification = "Minimums non satisfaits · " if not result.criteria_satisfied else ""
        self.warning_summary.set(f"{qualification}{limit} · {partial} sac(s) partiel(s) · Portée/réussite non simulées · Voir les limites")
        self.status.set(f"Analyse terminée en {_elapsed:.1f} s · {result.inventory_owned_count} clubs possédés · " + ("niveaux réels" if result.scenario_level is None else f"scénario niveau {result.scenario_level}"))
        for button in (self.export_json_button, self.export_text_button, self.search_info_button):
            button.configure(state="normal")

    def _show_warnings(self) -> None:
        if self.presentation is None:
            return
        window = self.tk.Toplevel(self.root)
        window.title("Limites et avertissements")
        window.geometry("850x550")
        text = self.tk.Text(window, wrap="word", padx=20, pady=20, font=("Segoe UI", 11))
        scroll = self.ttk.Scrollbar(window, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        self._set_text(text, self.presentation.warning_text)

    def _save_card(self, index: int) -> None:
        self._visual_selected_index = index
        self._save_selected_bag()

    def _on_error(self, message: str, technical: str) -> None:
        from tkinter import messagebox

        self.last_technical_error = technical
        messagebox.showerror("Optimisation impossible", message)

    def _show_detail(self, index: int) -> None:
        if self.presentation is None:
            return
        self._visual_selected_index = index
        self.detail_window.deiconify()
        self.detail_window.lift()
        detail = self.presentation.details[index]
        self.detail_title.set(detail.title)
        for tab in self.notebook.tabs():
            self.notebook.nametowidget(tab).destroy()
        self._add_text_tab("Résumé", detail.overview)
        for step in detail.steps:
            self._add_text_tab(step.label, step.content)
        self._add_text_tab("Pourquoi ces clubs ?", detail.synergies)
        self._add_text_tab("Détails techniques", detail.technical_details)
        self.copy_button.configure(state="normal")
        self.save_bag_button.configure(state="normal")
        self.replace_reference_button.configure(
            state="normal" if self.result and self.result.comparison_reference else "disabled"
        )

    def _selected_candidate(self) -> StrategyCandidateResult | None:
        index = self._selected_index()
        if index is None or self.result is None:
            return None
        return self.result.retained_results[index]

    def _save_selected_bag(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        from tkinter import messagebox, simpledialog

        name = simpledialog.askstring("Enregistrer comme sac", "Nom du nouveau sac :", parent=self.root)
        if not name:
            return
        try:
            _, bag_id = PgaDatabase(self.user_data_path).save_bag(name, candidate.composition)
        except Exception as error:
            messagebox.showerror("Enregistrement impossible", str(error), parent=self.root)
            return
        self._refresh_inventory_choices()
        self.status.set(f"Sac {name} enregistré sans modifier les sacs existants ({bag_id}).")

    def _replace_reference(self) -> None:
        candidate = self._selected_candidate()
        reference = self.result.comparison_reference if self.result else None
        if candidate is None or reference is None:
            return
        from tkinter import messagebox

        if not messagebox.askyesno(
            "Confirmer le remplacement",
            f"Remplacer le contenu de « {reference.label} » par la proposition sélectionnée ?\n\nUne sauvegarde sera créée.",
            parent=self.root,
        ):
            return
        try:
            PgaDatabase(self.user_data_path).replace_reference_bag(
                reference.bag_id, candidate.composition, confirmed=True,
            )
        except Exception as error:
            messagebox.showerror("Remplacement impossible", str(error), parent=self.root)
            return
        self._refresh_inventory_choices()
        self.status.set(f"Le sac de référence {reference.label} a été remplacé après confirmation.")

    def _mark_reference(self) -> None:
        bag_id = self.target_bag_by_label.get(self.target_bag_name.get())
        if not bag_id:
            self.status.set("Choisissez d’abord un sac enregistré.")
            return
        from tkinter import messagebox, simpledialog

        bundle = load_user_data(self.user_data_path)
        bag = next(item for item in bundle.bags if item.identifier == bag_id)
        current = bag.reference
        label = simpledialog.askstring(
            "Sac de référence", "Libellé fonctionnel :", initialvalue=current.label if current else bag.name,
            parent=self.root,
        )
        if not label:
            return
        usage = simpledialog.askstring(
            "Sac de référence", "Usage :", initialvalue=current.usage if current else "", parent=self.root,
        )
        note = simpledialog.askstring(
            "Sac de référence", "Note libre (sans effet sur le moteur) :",
            initialvalue=current.note if current else "", parent=self.root,
        )
        role = simpledialog.askstring(
            "Sac de référence", "Rôle (stable ou experimental) :",
            initialvalue=current.role if current else "stable", parent=self.root,
        )
        normalized_role = (role or "stable").casefold().replace("é", "e")
        if normalized_role not in {"stable", "experimental"}:
            messagebox.showerror("Référence impossible", "Le rôle doit être stable ou experimental.", parent=self.root)
            return
        selected_primary = self.fixed_club_by_label.get(self.fixed_club_name.get())
        primary = (
            current.primary_club_id if current and current.primary_club_id
            else selected_primary if selected_primary in bag.club_ids else None
        )
        reference_roles = self._edit_reference_roles_dialog(
            bag,
            dict(current.reference_roles or {}) if current else {},
        )
        if reference_roles is None:
            return
        profile = BagReferenceProfile(
            label=label, usage=usage or "",
            strategy_id=self.strategy_by_label[self.strategy_name.get()],
            primary_club_id=primary,
            role=normalized_role, note=note or "",
            club_notes=(
                dict(current.club_notes or {}) if current
                else {primary: note or ""} if primary and note else {}
            ),
            observed_metrics=dict(current.observed_metrics or {}) if current else {},
            reference_roles=reference_roles,
        )
        try:
            PgaDatabase(self.user_data_path).mark_bag_reference(bag_id, profile)
        except Exception as error:
            messagebox.showerror("Référence impossible", str(error), parent=self.root)
            return
        self._refresh_inventory_choices()
        self.target_bag_name.set(next(
            name for name, value in self.target_bag_by_label.items() if value == bag_id
        ))
        self.status.set(f"{label} est maintenant un sac de référence utilisateur.")

    def _edit_reference_roles_dialog(
        self,
        bag,
        current_roles: Mapping[str, str],
    ) -> dict[str, str] | None:
        strategy = self.presenter.registry.get(self.strategy_by_label[self.strategy_name.get()])
        choices = {
            "Automatique": "automatic",
            **{step.name: step.identifier for step in strategy.sequence},
            "Support": "support",
            "Variable": "variable",
        }
        labels_by_value = {value: label for label, value in choices.items()}
        window = self.tk.Toplevel(self.root)
        window.title("Rôles observés dans ce sac")
        window.transient(self.root)
        window.grab_set()
        self.ttk.Label(
            window,
            text="Ces rôles décrivent votre usage réel. Ils ne modifient ni le catalogue ni le moteur.",
            padding=10,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        variables: dict[str, object] = {}
        for row, club_id in enumerate(bag.club_ids, 1):
            name = next((label for label, value in self.fixed_club_by_label.items() if value == club_id), club_id)
            self.ttk.Label(window, text=name).grid(row=row, column=0, padx=10, pady=3, sticky="w")
            variable = self.tk.StringVar(
                value=labels_by_value.get(current_roles.get(club_id, "automatic"), "Automatique")
            )
            self.ttk.Combobox(
                window, textvariable=variable, values=tuple(choices), state="readonly", width=32,
            ).grid(row=row, column=1, padx=10, pady=3, sticky="ew")
            variables[club_id] = variable
        answer: dict[str, object] = {"value": None}

        def save() -> None:
            answer["value"] = {
                club_id: choices[str(variable.get())]
                for club_id, variable in variables.items()
            }
            window.destroy()

        buttons = self.ttk.Frame(window, padding=10)
        buttons.grid(row=len(bag.club_ids) + 1, column=0, columnspan=2, sticky="e")
        self.ttk.Button(buttons, text="Annuler", command=window.destroy).pack(side="left")
        self.ttk.Button(buttons, text="Enregistrer", command=save).pack(side="left", padx=(8, 0))
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        self.root.wait_window(window)
        return answer["value"]

    def _use_reference_roles(self) -> None:
        bag_id = self.target_bag_by_label.get(self.target_bag_name.get())
        if not bag_id:
            self.status.set("Choisissez d’abord un sac de référence.")
            return
        bag = next(item for item in load_user_data(self.user_data_path).bags if item.identifier == bag_id)
        if bag.reference is None:
            self.status.set("Ce sac ne possède pas encore de rôles utilisateur.")
            return
        if bag.reference.strategy_id and bag.reference.strategy_id != self.strategy_by_label[self.strategy_name.get()]:
            self.status.set("Choisissez d’abord la stratégie associée à cette référence.")
            return
        builder_label = next(
            label for label, mode in self.search_mode_by_label.items() if mode == "interactive_builder"
        )
        self.search_mode_name.set(builder_label)
        self._toggle_search_mode()
        for row in tuple(self.chosen_club_rows):
            self._remove_chosen_club(row)
        roles = dict(bag.reference.reference_roles or {})
        for club_id in bag.club_ids:
            role = roles.get(club_id, "automatic")
            self._add_chosen_club(club_id, "auto" if role in {"automatic", "variable"} else role)
        self.status.set("Rôles de la référence préremplis. Modifiez-les si nécessaire, puis lancez l’analyse.")

    def _add_text_tab(self, label: str, content: str) -> None:
        frame = self.ttk.Frame(self.notebook)
        text = self.tk.Text(frame, wrap="word", font=("Consolas", 10))
        scroll = self.ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.insert("1.0", content)
        text.configure(state="disabled")
        self.notebook.add(frame, text=label)

    def _selected_index(self) -> int | None:
        return self._visual_selected_index

    def _copy_summary(self) -> None:
        index = self._selected_index()
        if index is None or self.presentation is None:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.presentation.details[index].clipboard_summary)
        self.status.set("Résumé du sac copié dans le presse-papiers.")

    def _export_json(self) -> None:
        self._export("json")

    def _export_text(self) -> None:
        self._export("txt")

    def _export(self, extension: str) -> None:
        if self.result is None:
            return
        from tkinter import filedialog, messagebox

        destination = filedialog.asksaveasfilename(
            title="Enregistrer les résultats",
            defaultextension="." + extension,
            initialfile=suggested_export_name(self.result.strategy_id, extension),
            filetypes=(("Fichier JSON", "*.json"),) if extension == "json" else (("Fichier texte", "*.txt"),),
        )
        if not destination:
            return
        try:
            path = export_result_json(self.result, destination) if extension == "json" else export_result_text(self.result, destination)
        except OSError as error:
            messagebox.showerror("Export impossible", "Le fichier n’a pas pu être enregistré.", detail=str(error))
            return
        self.status.set(f"Résultats enregistrés dans {path}.")

    def _show_search_info(self) -> None:
        if self.presentation is None:
            return
        from tkinter import messagebox

        messagebox.showinfo("Informations sur la recherche", self.presentation.search_information)

    def _open_inventory(self) -> None:
        try:
            window = self.tk.Toplevel(self.root)
            service = InventoryEditorService(database_path=self.user_data_path, catalog_path=self.catalog_path)
            app = InventoryEditorApp(service, root=window)
            self.inventory_windows.append(app)
        except Exception as error:
            self._on_error("L’éditeur d’inventaire n’a pas pu être ouvert.", f"{error.__class__.__name__}: {error}")

    @staticmethod
    def _set_text(widget, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def run(self) -> int:
        self.root.mainloop()
        return 0


def run_strategy_optimizer_gui(**kwargs) -> int:
    try:
        return StrategyOptimizerApp(**kwargs).run()
    except Exception as error:
        message = french_optimizer_error(error)
        try:
            from tkinter import messagebox

            messagebox.showerror("PGA Shootout", message)
        except Exception:
            print(message)
        return 1


def _stat_lines(step: ClubStepResult) -> list[str]:
    lines: list[str] = []
    for metric in ("power", "control", "spin"):
        base = step.base_stats[metric]
        final = step.final_stats[metric]
        delta = step.deltas[metric]
        if base is None or final is None or delta is None:
            value = "—"
        else:
            value = f"{base:g} → {final:g}   ({delta:+g})"
        lines.append(f"{_metric_label(metric):<12}{value}")
    return lines


def _metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def _metric_unit(metric: str) -> str:
    if metric.endswith("_percent"):
        return " %"
    if metric.endswith("_degrees"):
        return "°"
    return ""


def _same_values(left: ClubStepResult, right: ClubStepResult) -> bool:
    return (
        left.base_stats == right.base_stats
        and left.final_stats == right.final_stats
        and left.additional_metrics == right.additional_metrics
    )


def _unique_contributions(values) -> tuple[ContributionRecord, ...]:
    result: list[ContributionRecord] = []
    seen: set[tuple[object, ...]] = set()
    for item in values:
        key = (
            item.source_club_id,
            item.target_club_id,
            item.ability_id,
            item.mechanism,
            tuple(item.modification.items()),
            item.scheduled_effect_ids,
        )
        if key not in seen:
            seen.add(key)
            result.append(item)
    return tuple(result)


def _contribution_line(item: ContributionRecord, club_names: Mapping[str, str]) -> str:
    changes = ", ".join(
        f"{_metric_label(metric)} {value:+g}{_metric_unit(metric)}"
        for metric, value in item.modification.items()
    ) or "effet différé planifié"
    scheduled = f" ; effets planifiés : {', '.join(item.scheduled_effect_ids)}" if item.scheduled_effect_ids else ""
    source = club_names.get(item.source_club_id, item.source_club_id)
    target = club_names.get(item.target_club_id, item.target_club_id)
    ability = item.ability_id.split("__", 1)[-1].replace("_", " ").title()
    return f"{source} → {target} — {ability} : {changes}{scheduled}"


if __name__ == "__main__":
    raise SystemExit(run_strategy_optimizer_gui())
