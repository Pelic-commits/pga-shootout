"""Windows-friendly Tkinter presentation for the generic strategy optimizer.

The presenter and controller deliberately have no Tkinter dependency.  This
keeps the UI a replaceable consumer of StrategyOptimizationResult and makes the
threading, French messages and exports testable without opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sqlite3
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Callable, Mapping

from .inventory_editor import InventoryEditorApp, InventoryEditorService
from .models import EvaluationMode
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
    "with_warnings": "Résultat avec avertissements",
    "excluded": "Candidat exclu",
    "neutral": "Neutre",
}
METRIC_LABELS = {
    "power": "Power",
    "control": "Control",
    "spin": "Spin",
    "loft_angle_degrees": "Loft",
    "wind_resistance_percent": "Wind Resistance",
    "bounce_reduction_percent": "Bounce Reduction",
    "groundspin": "Groundspin",
    "groundspin_increase_percent": "Groundspin",
    "swing_speed": "Swing Speed",
    "gravity_reduction_percent": "Gravity Reduction",
    "launch_angle_degrees": "Launch Angle",
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
    search_mode: str = "global"
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
            composition=" · ".join(club.club_name for club in candidate.clubs),
            active_clubs=active,
            category=GROUP_LABELS.get(candidate.comparison_group, "Proposition retenue"),
            unresolved_count=len(candidate.unresolved_abilities),
            has_neutral_club=any(club.role == "neutral" for club in candidate.clubs),
            strengths=self._strengths(candidate, step_labels),
            families=", ".join(family_names.get(item, item) for item in candidate.result_family_ids),
            origin={
                "reference_bag": "Sac enregistré",
                "reference_neighborhood": "Amélioration locale",
                "global_search": "Recherche globale",
                "interactive_builder": "Constructeur interactif",
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
        title = f"Proposition {index} — " + " · ".join(club.club_name for club in candidate.clubs)
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
        lines = [f"Origine : {candidate.origin}", "Exigences"]
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
        if result.inventory_changes.added_club_ids:
            lines.append("• Nouveau(x) club(s) détecté(s) depuis la précédente analyse :")
            lines.extend(f"  - {item.club_name} — niveau {item.level}" for item in result.new_club_diagnostics)
        if not result.criteria_satisfied:
            lines.append("• Aucun sac ne satisfait actuellement ces critères ; les solutions les plus proches sont affichées sans modifier vos minimums.")
        return "\n".join(lines)

    @staticmethod
    def _search_information(result: StrategyOptimizationResult) -> str:
        total = result.search.total_seconds
        return "\n".join((
            "Informations sur la recherche",
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
                self.schedule(lambda: self._finish_error(error))
                return
            self.schedule(lambda: self._finish_success(result, elapsed))

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
    """Single-window, three-zone Tkinter optimizer application."""

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
        self.status = tk.StringVar(value="Choisissez une stratégie puis lancez l’analyse.")
        self.show_advanced = tk.BooleanVar(value=False)
        bundle = load_user_data(self.user_data_path)
        self.reference_by_label = {"Aucun": None, **{bag.name: bag.identifier for bag in bundle.bags}}
        self.reference_name = tk.StringVar(value="Aucun")
        self.search_mode_by_label = {
            "Optimiser autour de mes clubs": "interactive_builder",
            "Chercher de nouveaux sacs": "global",
            "Améliorer un de mes sacs": "improve_bag",
            "Remplacer un club de mon sac": "replace_club",
            "Optimiser autour d’un club": "around_club",
            "Tester un nouveau club dans mes sacs": "test_new_club",
        }
        self.search_mode_name = tk.StringVar(value="Optimiser autour de mes clubs")
        self.target_bag_by_label = {"Aucun": None, **{_bag_label(bag): bag.identifier for bag in bundle.bags}}
        self.target_bag_name = tk.StringVar(value="Aucun")
        owned = tuple(item for item in bundle.inventory.entries if item.unlocked and item.current_level is not None)
        self.fixed_club_by_label = {item.display_name: item.club_id for item in owned}
        self.fixed_club_name = tk.StringVar(value=next(iter(self.fixed_club_by_label), ""))
        self.fixed_step_name = tk.StringVar(value="")
        self.replacement_depth = tk.StringVar(value="1")
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
        tk, ttk = self.tk, self.ttk
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        parameters = ttk.LabelFrame(self.root, text="1 — Paramètres", padding=10)
        parameters.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ttk.Label(parameters, text="Stratégie :").grid(row=0, column=0, sticky="w")
        strategy_box = ttk.Combobox(parameters, textvariable=self.strategy_name, values=tuple(self.strategy_by_label), state="readonly", width=28)
        strategy_box.grid(row=0, column=1, padx=(5, 18))
        strategy_box.bind("<<ComboboxSelected>>", lambda _event: self._strategy_changed())
        ttk.Label(parameters, text="Variante :").grid(row=0, column=2, sticky="w")
        self.variant_box = ttk.Combobox(parameters, textvariable=self.variant_name, state="readonly", width=28)
        self.variant_box.grid(row=0, column=3, padx=(5, 18))
        ttk.Radiobutton(parameters, text="Réel", variable=self.real_mode, value=True, command=self._toggle_mode).grid(row=0, column=4)
        ttk.Radiobutton(parameters, text="Scénario", variable=self.real_mode, value=False, command=self._toggle_mode).grid(row=0, column=5)
        ttk.Label(parameters, text="Niveau :").grid(row=0, column=6, padx=(12, 3))
        self.scenario_entry = ttk.Spinbox(parameters, from_=1, to=12, textvariable=self.scenario_level, width=5)
        self.scenario_entry.grid(row=0, column=7)
        ttk.Label(parameters, text="Résultats :").grid(row=0, column=8, padx=(16, 3))
        ttk.Combobox(parameters, textvariable=self.limit, values=("5", "10", "20"), state="readonly", width=5).grid(row=0, column=9)

        ttk.Label(parameters, text="Sac de référence pour la portée :").grid(row=2, column=0, pady=(8, 0), sticky="w")
        ttk.Combobox(
            parameters, textvariable=self.reference_name,
            values=tuple(self.reference_by_label), state="readonly", width=28,
        ).grid(row=2, column=1, columnspan=2, pady=(8, 0), sticky="w")
        ttk.Label(
            parameters, text="Option empirique : aucun calcul de distance n'est effectué.",
        ).grid(row=2, column=3, columnspan=5, pady=(8, 0), sticky="w")

        ttk.Label(parameters, text="Mode de recherche :").grid(row=3, column=0, pady=(8, 0), sticky="w")
        self.search_mode_box = ttk.Combobox(
            parameters, textvariable=self.search_mode_name,
            values=tuple(self.search_mode_by_label), state="readonly", width=28,
        )
        self.search_mode_box.grid(row=3, column=1, columnspan=2, pady=(8, 0), sticky="w")
        self.search_mode_box.bind("<<ComboboxSelected>>", lambda _event: self._toggle_search_mode())
        ttk.Label(parameters, text="Comparer à / sac de départ :").grid(row=3, column=3, pady=(8, 0), sticky="e")
        self.target_bag_box = ttk.Combobox(
            parameters, textvariable=self.target_bag_name,
            values=tuple(self.target_bag_by_label), state="disabled", width=28,
        )
        self.target_bag_box.grid(row=3, column=4, columnspan=2, pady=(8, 0), sticky="w")
        ttk.Label(parameters, text="Club fixé :").grid(row=3, column=6, pady=(8, 0), sticky="e")
        self.fixed_club_box = ttk.Combobox(
            parameters, textvariable=self.fixed_club_name,
            values=tuple(self.fixed_club_by_label), state="disabled", width=22,
        )
        self.fixed_club_box.grid(row=3, column=7, columnspan=2, pady=(8, 0), sticky="w")
        ttk.Label(parameters, text="Remplacements :").grid(row=3, column=9, pady=(8, 0), sticky="e")
        self.depth_box = ttk.Combobox(
            parameters, textvariable=self.replacement_depth, values=("1", "2"), state="disabled", width=4,
        )
        self.depth_box.grid(row=3, column=10, pady=(8, 0), sticky="w")
        ttk.Button(parameters, text="Définir comme référence", command=self._mark_reference).grid(
            row=3, column=11, pady=(8, 0), padx=(6, 0), sticky="w",
        )

        self.builder_frame = ttk.LabelFrame(parameters, text="Clubs choisis et objectifs", padding=6)
        self.builder_frame.grid(row=4, column=0, columnspan=12, sticky="ew", pady=(8, 0))
        self.builder_frame.columnconfigure(0, weight=2)
        self.builder_frame.columnconfigure(1, weight=3)
        chosen = ttk.LabelFrame(self.builder_frame, text="Clubs à utiliser", padding=5)
        chosen.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.chosen_rows_frame = ttk.Frame(chosen)
        self.chosen_rows_frame.pack(fill="x")
        ttk.Button(chosen, text="+ Ajouter un club", command=self._add_chosen_club).pack(anchor="w", pady=(5, 0))
        self.objectives_frame = ttk.LabelFrame(self.builder_frame, text="Objectifs — Power est maximisée par défaut", padding=5)
        self.objectives_frame.grid(row=0, column=1, sticky="nsew")

        constraints = ttk.LabelFrame(parameters, text="Contraintes facultatives des anciens modes", padding=6)
        constraints.grid(row=5, column=0, columnspan=12, sticky="ew", pady=(8, 0))
        self.legacy_constraints = constraints
        ttk.Label(constraints, text="Clubs à conserver / obligatoires").grid(row=0, column=0, sticky="w")
        self.required_list = tk.Listbox(constraints, selectmode="multiple", exportselection=False, height=4, width=28)
        self.required_list.grid(row=1, column=0, padx=(0, 12), sticky="ew")
        ttk.Label(constraints, text="Clubs exclus").grid(row=0, column=1, sticky="w")
        self.excluded_list = tk.Listbox(constraints, selectmode="multiple", exportselection=False, height=4, width=28)
        self.excluded_list.grid(row=1, column=1, padx=(0, 12), sticky="ew")
        ttk.Checkbutton(
            constraints, text="Conserver mon putter actuel", variable=self.keep_current_putter,
        ).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(
            constraints, text="Verrouiller à leur position actuelle les clubs conservés",
            variable=self.lock_required_positions,
        ).grid(row=1, column=2, sticky="nw")
        ttk.Label(constraints, text="Rôle actif du club testé :").grid(row=0, column=3, padx=(14, 0), sticky="w")
        self.fixed_step_box = ttk.Combobox(
            constraints, textvariable=self.fixed_step_name, state="disabled", width=22,
        )
        self.fixed_step_box.grid(row=1, column=3, padx=(14, 0), sticky="nw")

        self.analyze_button = ttk.Button(parameters, text="Lancer l’analyse", command=self._start)
        self.analyze_button.grid(row=0, column=10, padx=(20, 6))
        ttk.Button(parameters, text="Gérer mon inventaire", command=self._open_inventory).grid(row=0, column=11, padx=6)
        self.test_new_button = ttk.Button(
            parameters, text="Tester le nouveau club", command=self._test_detected_club, state="disabled",
        )
        self.test_new_button.grid(row=1, column=11, padx=6, pady=(10, 0))
        ttk.Checkbutton(parameters, text="Options avancées", variable=self.show_advanced, command=self._toggle_advanced).grid(row=1, column=0, pady=(10, 0), sticky="w")
        self.advanced_frame = ttk.Frame(parameters)
        ttk.Label(self.advanced_frame, text="Limite de sécurité :").pack(side="left")
        ttk.Entry(self.advanced_frame, textvariable=self.max_evaluations, width=8).pack(side="left", padx=5)
        self.progress = ttk.Progressbar(parameters, mode="indeterminate", length=180)
        self.progress.grid(row=1, column=9, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Label(parameters, textvariable=self.status).grid(row=1, column=2, columnspan=7, pady=(10, 0), sticky="w")

        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_zone = ttk.LabelFrame(panes, text="2 — Propositions retenues", padding=8)
        detail_zone = ttk.LabelFrame(panes, text="3 — Détail du sac sélectionné", padding=8)
        panes.add(list_zone, weight=2)
        panes.add(detail_zone, weight=3)

        self.warning = tk.Text(list_zone, height=7, wrap="word", background="#fff4ce", relief="flat")
        self.warning.pack(fill="x", pady=(0, 6))
        self.warning.configure(state="disabled")
        self.reference_summary = tk.StringVar(value="COMPARER À — Aucun sac réel sélectionné")
        ttk.Label(
            list_zone, textvariable=self.reference_summary, background="#eaf3ff",
            padding=6, justify="left", wraplength=760,
        ).pack(fill="x", pady=(0, 6))
        table = ttk.Frame(list_zone)
        table.pack(fill="both", expand=True)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        columns = ("number", "origin", "family", "category", "composition", "active", "unresolved", "neutral", "strengths")
        self.candidate_tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse", height=15)
        labels = {
            "number": "N°", "origin": "Origine", "family": "Famille", "category": "Catégorie", "composition": "Composition ordonnée",
            "active": "Clubs actifs", "unresolved": "Non résolues", "neutral": "Club neutre", "strengths": "Points forts calculables",
        }
        widths = {"number": 40, "origin": 130, "family": 220, "category": 170, "composition": 330, "active": 240, "unresolved": 80, "neutral": 80, "strengths": 290}
        for column in columns:
            self.candidate_tree.heading(column, text=labels[column])
            self.candidate_tree.column(column, width=widths[column], anchor="w")
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.candidate_tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.candidate_tree.xview)
        self.candidate_tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.candidate_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.candidate_tree.bind("<<TreeviewSelect>>", self._select_candidate)

        self.detail_title = tk.StringVar(value="Sélectionnez une proposition.")
        ttk.Label(detail_zone, textvariable=self.detail_title, font=("Segoe UI", 11, "bold"), wraplength=720).pack(fill="x")
        self.notebook = ttk.Notebook(detail_zone)
        self.notebook.pack(fill="both", expand=True, pady=8)
        export_bar = ttk.Frame(detail_zone)
        export_bar.pack(fill="x")
        self.export_json_button = ttk.Button(export_bar, text="Exporter en JSON", command=self._export_json, state="disabled")
        self.export_text_button = ttk.Button(export_bar, text="Exporter en texte", command=self._export_text, state="disabled")
        self.copy_button = ttk.Button(export_bar, text="Copier le résumé du sac", command=self._copy_summary, state="disabled")
        self.save_bag_button = ttk.Button(export_bar, text="Enregistrer comme sac", command=self._save_selected_bag, state="disabled")
        self.replace_reference_button = ttk.Button(
            export_bar, text="Remplacer mon sac de référence", command=self._replace_reference, state="disabled",
        )
        self.export_json_button.pack(side="left")
        self.export_text_button.pack(side="left", padx=6)
        self.copy_button.pack(side="left")
        self.save_bag_button.pack(side="left", padx=6)
        self.replace_reference_button.pack(side="left")
        self.search_info_button = ttk.Button(export_bar, text="Informations sur la recherche", command=self._show_search_info, state="disabled")
        self.search_info_button.pack(side="right")

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
        used = {self.fixed_club_by_label.get(str(row["club_var"].get())) for row in self.chosen_club_rows}
        label = next(
            (name for name, value in self.fixed_club_by_label.items() if value == club_id),
            next((name for name, value in self.fixed_club_by_label.items() if value not in used), ""),
        )
        roles = self._role_choices()
        role_label = next((name for name, value in roles.items() if value == role), "Automatique")
        row_frame = self.ttk.Frame(self.chosen_rows_frame)
        row_frame.pack(fill="x", pady=2)
        club_var = self.tk.StringVar(value=label)
        role_var = self.tk.StringVar(value=role_label)
        position_var = self.tk.StringVar(value="Libre")
        club_box = self.ttk.Combobox(
            row_frame, textvariable=club_var, values=tuple(self.fixed_club_by_label), state="readonly", width=24,
        )
        role_box = self.ttk.Combobox(
            row_frame, textvariable=role_var, values=tuple(roles), state="readonly", width=25,
        )
        position_box = self.ttk.Combobox(
            row_frame, textvariable=position_var, values=("Libre", "1", "2", "3", "4", "5"), state="readonly", width=7,
        )
        club_box.pack(side="left")
        role_box.pack(side="left", padx=4)
        position_box.pack(side="left")
        row: dict[str, object] = {
            "frame": row_frame, "club_var": club_var, "role_var": role_var,
            "position_var": position_var, "club_box": club_box, "role_box": role_box,
        }
        self.ttk.Button(row_frame, text="Supprimer", command=lambda: self._remove_chosen_club(row)).pack(side="left", padx=4)
        self.chosen_club_rows.append(row)

    def _remove_chosen_club(self, row: dict[str, object]) -> None:
        row["frame"].destroy()
        self.chosen_club_rows.remove(row)

    def _refresh_chosen_roles(self) -> None:
        roles = self._role_choices()
        for row in self.chosen_club_rows:
            current = str(row["role_var"].get())
            row["role_box"].configure(values=tuple(roles))
            if current not in roles:
                row["role_var"].set("Automatique")

    def _rebuild_objectives(self) -> None:
        for child in self.objectives_frame.winfo_children():
            child.destroy()
        self.step_minimum_vars = {}
        strategy_id = self.strategy_by_label[self.strategy_name.get()]
        strategy = self.presenter.registry.get(strategy_id)
        for row_index, step in enumerate(strategy.sequence):
            function_label = {
                "advance_toward_target": "PROGRESSER",
                "reach_target_zone": "ATTAQUER LE GREEN",
                "finish": "PUTT",
            }.get(step.function.identifier, step.function.identifier)
            self.ttk.Label(self.objectives_frame, text=f"{step.name} — {function_label}").grid(
                row=row_index, column=0, sticky="w", padx=(0, 8), pady=2,
            )
            metrics = ("power", "control") if step.function.identifier == "finish" else ("control", "spin")
            values: dict[str, object] = {}
            for column, metric in enumerate(metrics, 1):
                variable = self.tk.StringVar(value="Aucun")
                box = self.ttk.Combobox(
                    self.objectives_frame, textvariable=variable, values=("Aucun",), width=12,
                )
                box.grid(row=row_index, column=column, padx=3, pady=2)
                self.ttk.Label(self.objectives_frame, text=f"{METRIC_LABELS[metric]} minimum").grid(
                    row=row_index + len(strategy.sequence), column=column, padx=3, sticky="n",
                ) if row_index == 0 else None
                values[metric] = (variable, box)
            self.step_minimum_vars[step.identifier] = values

    def _toggle_mode(self) -> None:
        self.scenario_entry.configure(state="disabled" if self.real_mode.get() else "normal")

    def _toggle_search_mode(self) -> None:
        mode = self.search_mode_by_label[self.search_mode_name.get()]
        local_mode = mode in {"improve_bag", "replace_club", "around_club", "test_new_club", "interactive_builder"}
        self.target_bag_box.configure(state="readonly" if local_mode else "disabled")
        self.fixed_club_box.configure(state="readonly" if mode in {"replace_club", "around_club", "test_new_club"} else "disabled")
        self.fixed_step_box.configure(state="readonly" if mode == "around_club" else "disabled")
        self.depth_box.configure(state="readonly" if mode != "global" else "disabled")
        if mode == "interactive_builder":
            self.builder_frame.grid()
            self.legacy_constraints.grid_remove()
        else:
            self.builder_frame.grid_remove()
            self.legacy_constraints.grid()
        self.analyze_button.configure(
            text="OPTIMISER MON SAC" if mode == "interactive_builder"
            else "Remplacer ce club" if mode == "replace_club"
            else "Chercher des améliorations" if mode == "improve_bag"
            else "Tester ce club" if mode == "test_new_club" else "Lancer l’analyse"
        )

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
            self.advanced_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="w")
        else:
            self.advanced_frame.grid_remove()

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
        if search_mode == "interactive_builder":
            role_choices = self._role_choices()
            for row in self.chosen_club_rows:
                label = str(row["club_var"].get())
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
            reference_bag_id=self.reference_by_label[self.reference_name.get()],
            search_mode=search_mode,
            target_bag_id=target_bag_id,
            fixed_club_id=self.fixed_club_by_label.get(self.fixed_club_name.get()),
            replace_club_id=(
                self.fixed_club_by_label.get(self.fixed_club_name.get())
                if search_mode == "replace_club" else None
            ),
            replacement_depth=int(self.replacement_depth.get()),
            required_club_ids=required_ids,
            excluded_club_ids=tuple(self.fixed_club_by_label[item] for item in excluded_labels),
            locked_positions=locked_positions,
            keep_current_putter=self.keep_current_putter.get(),
            fixed_step_id=self.fixed_step_by_label.get(self.fixed_step_name.get()),
            club_roles=club_roles,
            metric_minimums=metric_minimums,
            primary_step_id=primary_step_id,
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
            self.progress.start(10)
        else:
            self.progress.stop()
        self.status.set(message)

    def _on_success(self, result: StrategyOptimizationResult, _elapsed: float) -> None:
        self.result = result
        self.presentation = self.presenter.present(result)
        self._set_text(self.warning, self.presentation.warning_text)
        self.reference_summary.set(self.presentation.reference_text)
        self.candidate_tree.delete(*self.candidate_tree.get_children())
        for step_id, metrics in (result.attainable_ranges or {}).items():
            for metric, values in metrics.items():
                entry = self.step_minimum_vars.get(step_id, {}).get(metric)
                if entry:
                    entry[1].configure(values=("Aucun", *(f"{value:g}" for value in values)))
        for index, item in enumerate(self.presentation.candidates):
            self.candidate_tree.insert("", "end", iid=str(index), values=(
                item.display_number, item.origin, item.families, item.category, item.composition, item.active_clubs,
                item.unresolved_count, "Oui" if item.has_neutral_club else "Non", item.strengths,
            ))
        self.status.set(
            f"Analyse terminée — {'maximum prouvé' if result.search.optimality_status == 'maximum_proven' else 'meilleur résultat trouvé'} — "
            f"inventaire utilisé : {result.inventory_owned_count} clubs possédés "
            f"(observation {result.inventory_observed_at or 'inconnue'})."
        )
        for button in (self.export_json_button, self.export_text_button, self.search_info_button):
            button.configure(state="normal")
        if self.presentation.candidates:
            self.candidate_tree.selection_set("0")
            self.candidate_tree.focus("0")
            self._show_detail(0)

    def _on_error(self, message: str, technical: str) -> None:
        from tkinter import messagebox

        self.last_technical_error = technical
        messagebox.showerror("Optimisation impossible", message)

    def _select_candidate(self, _event=None) -> None:
        selected = self.candidate_tree.selection()
        if selected:
            self._show_detail(int(selected[0]))

    def _show_detail(self, index: int) -> None:
        if self.presentation is None:
            return
        detail = self.presentation.details[index]
        self.detail_title.set(detail.title)
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
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
        selected = self.candidate_tree.selection()
        return int(selected[0]) if selected else None

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
