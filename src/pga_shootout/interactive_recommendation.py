"""Guided terminal experience over the existing placement recommendation flow."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from .explain import render_explain_entries
from .models import EvaluationMode
from .placement_recommendation import (
    PlacementCandidateResult,
    PlacementRecommendationFormatter,
    PlacementRecommendationRequest,
    PlacementRecommendationResult,
    PlacementRecommendationService,
)
from .recommendation import (
    CandidateEvaluator,
    CandidateValidator,
    RecommendationRequest,
    RecommendationStatus,
)
from .optimizer_api import RuleEngineBagEvaluator
from .user_data import SavedBag, load_user_data


InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


STATUS_LABELS = {
    RecommendationStatus.PARETO: "amélioration sans contrepartie",
    RecommendationStatus.TRADEOFF: "compromis",
    RecommendationStatus.NEUTRAL: "neutre",
    RecommendationStatus.EXCLUDED: "exclu",
}


class InteractiveRecommendationFormatter:
    """Compact French presentation of an existing structured result."""

    def __init__(self, structured_formatter: type[PlacementRecommendationFormatter] = PlacementRecommendationFormatter):
        self.structured_formatter = structured_formatter

    def render(self, result: PlacementRecommendationResult) -> tuple[str, ...]:
        # Ensure the interactive view and non-interactive JSON share the same serializable source.
        self.structured_formatter.render_json(result)
        lines = [
            "",
            "Résultats",
            f"Sac : {result.request.bag_id}",
            f"Club testé : {result.incoming_club_name}",
            f"Mode de niveau : {'réel' if result.request.level_mode == 'actual' else 'scénario'}",
        ]
        if result.request.level is not None:
            lines.append(f"Niveau de scénario : {result.request.level}")
        lines.append("")
        for candidate in result.candidates:
            replacement = candidate.replacement
            position = replacement.position if replacement is not None else "?"
            outgoing = replacement.outgoing_club_name if replacement is not None else "inconnu"
            incoming = replacement.incoming_club_name if replacement is not None else result.incoming_club_name
            lines.extend(
                [
                    f"Placement {position} — {outgoing} → {incoming}",
                    f"Catégorie : {STATUS_LABELS[candidate.status]}",
                    "Gains :",
                    *self._matrix_lines(candidate.gains),
                    "Pertes :",
                    *self._matrix_lines(candidate.losses),
                ]
            )
            if candidate.new_unresolved_ability_ids:
                lines.append("Nouvelles capacités non résolues : " + ", ".join(candidate.new_unresolved_ability_ids))
            if candidate.exclusion_reasons:
                lines.append(
                    "Exclusion : "
                    + " ".join(self._exclusion_label(item) for item in candidate.exclusion_reasons)
                )
            if candidate.warnings:
                lines.append("Avertissements :")
                lines.extend(f"  - {self._warning_label(item)}" for item in candidate.warnings)
            lines.append("")
        lines.extend(
            [
                "Aucun score global n'a été calculé.",
                "Plusieurs placements peuvent rester des compromis différents.",
            ]
        )
        return tuple(lines)

    @staticmethod
    def _matrix_lines(items) -> list[str]:
        if not items:
            return ["  - aucune"]
        return [
            f"  - position évaluée {position} ({club}) : {metric.label} "
            f"{metric.delta:+g} {metric.unit}"
            for position, club, metric in items
        ]

    @staticmethod
    def _warning_label(value: str) -> str:
        if value.startswith("Explicit level scenario"):
            level = value.split("Explicit level scenario ", 1)[1].split(" ", 1)[0]
            return f"Le niveau {level} est hypothétique et ne provient pas de l'inventaire."
        if value.startswith("The user inventory is incomplete"):
            return "L'inventaire utilisateur est incomplet ; la recommandation n'est pas exhaustive."
        if value.startswith("The candidate retains unresolved abilities already present in the baseline:"):
            abilities = value.split(":", 1)[1].strip()
            return f"Capacités non résolues déjà présentes dans le sac de référence : {abilities}."
        if value.startswith("Delayed effects are reported"):
            return "Les effets différés sont signalés par position mais aucune séquence de coups n'est simulée."
        return value

    @staticmethod
    def _exclusion_label(value: str) -> str:
        if value.startswith("No recorded user level is available for club"):
            club = value.split("club ", 1)[1].split(" in actual mode", 1)[0]
            return f"Niveau utilisateur manquant pour {club}."
        if "not confirmed in the user inventory" in value:
            return "Le club entrant n'est pas confirmé dans l'inventaire utilisateur."
        if "already present in the bag" in value or "duplicate clubs" in value:
            return "Ce placement créerait un doublon dans le sac."
        return value


class PlacementExplainProvider:
    """Render the existing Explain journal for one already-selected placement."""

    def __init__(
        self,
        *,
        user_dir: str | Path,
        catalog_path: str | Path,
    ) -> None:
        self.validator = CandidateValidator(user_dir=user_dir, catalog_path=catalog_path)
        self.evaluator = CandidateEvaluator(RuleEngineBagEvaluator(catalog_path))

    def render(
        self,
        request: PlacementRecommendationRequest,
        candidate: PlacementCandidateResult,
    ) -> tuple[str, ...]:
        replacement = candidate.replacement
        if replacement is None or not candidate.positions:
            return ("Ce placement est exclu ; aucun Explain complet n'est disponible.",)
        validation = self.validator.validate(
            self._single_request(request, replacement.outgoing_club_id, replacement.incoming_club_id)
        )
        if not validation.valid:
            return ("Explain indisponible : " + " ".join(validation.errors),)

        lines = [
            "",
            f"Explain détaillé — placement {replacement.position} : "
            f"{replacement.outgoing_club_name} → {replacement.incoming_club_name}",
        ]
        for position in range(1, 6):
            positioned = replace(validation, evaluated_position=position)
            evaluation = self.evaluator.evaluate(positioned)
            club = evaluation.candidate.evaluation.state.current_entry.club
            lines.extend(
                [
                    "",
                    "-" * 72,
                    f"Position évaluée {position} — {club.name}",
                    render_explain_entries(evaluation.candidate.evaluation.result.explain),
                ]
            )
        return tuple(lines)

    @staticmethod
    def _single_request(request, outgoing_club_id: str, incoming_club_id: str):
        return RecommendationRequest(
            bag_id=request.bag_id,
            outgoing_club_id=outgoing_club_id,
            incoming_club_id=incoming_club_id,
            level=request.level,
            mode=request.mode,
        )


class InteractiveRecommendationApp:
    def __init__(
        self,
        *,
        user_dir: str | Path = "data/user",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        input_fn: InputFunction | None = None,
        output_fn: OutputFunction = print,
        service: PlacementRecommendationService | None = None,
    ) -> None:
        self.user_dir = Path(user_dir)
        self.catalog_path = Path(catalog_path)
        self.input = input_fn or input
        self.output = output_fn
        self.service = service or PlacementRecommendationService(
            user_dir=self.user_dir,
            catalog_path=self.catalog_path,
        )
        self.formatter = InteractiveRecommendationFormatter()
        self.explain = PlacementExplainProvider(
            user_dir=self.user_dir,
            catalog_path=self.catalog_path,
        )

    def run(self) -> int:
        bundle = load_user_data(self.user_dir)
        self.output("Assistant de placement PGA Shootout")
        self.output("=" * 40)
        bag = self._choose_bag(bundle.bags)
        eligible = tuple(
            item
            for item in bundle.inventory.entries
            if item.unlocked and item.club_id not in bag.club_ids
        )
        if not eligible:
            self.output("Aucun club débloqué éligible n'est enregistré pour ce sac.")
            return 1
        incoming = self._choose(
            "Choisissez un club à tester :",
            eligible,
            lambda item: item.display_name,
        )
        mode_choice = self._choose(
            "Choisissez le mode :",
            ("actual", "scenario"),
            lambda item: "Réel" if item == "actual" else "Scénario",
        )
        level = None
        if mode_choice == "scenario":
            level = self._ask_level()

        request = PlacementRecommendationRequest(
            bag_id=bag.identifier,
            incoming_club_id=incoming.club_id,
            level=level,
            mode=EvaluationMode.PARTIAL,
        )
        self.output("")
        self.output("Analyse...")
        result = self.service.analyze(request)
        for line in self.formatter.render(result):
            self.output(line)

        if self._ask_yes_no("Afficher les explications détaillées d'un placement ?"):
            candidate = self._choose(
                "Choisissez un numéro de placement :",
                result.candidates,
                self._candidate_label,
            )
            for line in self.explain.render(request, candidate):
                self.output(line)
        return 1 if all(item.status is RecommendationStatus.EXCLUDED for item in result.candidates) else 0

    def _choose_bag(self, bags: Sequence[SavedBag]) -> SavedBag:
        return self._choose("Choisissez un sac :", bags, lambda item: item.name)

    def _choose(self, title: str, options: Sequence, label: Callable[[object], str]):
        while True:
            self.output("")
            self.output(title)
            for index, option in enumerate(options, start=1):
                self.output(f"{index} - {label(option)}")
            value = self.input("> ").strip()
            if value.isdigit() and 1 <= int(value) <= len(options):
                return options[int(value) - 1]
            self.output("Choix invalide. Saisissez le numéro d'une option proposée.")

    def _ask_level(self) -> int | str:
        while True:
            self.output("")
            self.output("Niveau de scénario :")
            value = self.input("> ").strip()
            if value.isdigit():
                return int(value)
            if value.casefold() == "elite":
                return "Elite"
            self.output("Niveau invalide. Saisissez un niveau numérique ou Elite.")

    def _ask_yes_no(self, title: str) -> bool:
        while True:
            self.output("")
            self.output(title)
            self.output("1 - Oui")
            self.output("2 - Non")
            value = self.input("> ").strip().casefold()
            if value in {"1", "o", "oui"}:
                return True
            if value in {"2", "n", "non"}:
                return False
            self.output("Choix invalide. Répondez 1 pour Oui ou 2 pour Non.")

    @staticmethod
    def _candidate_label(candidate: PlacementCandidateResult) -> str:
        replacement = candidate.replacement
        if replacement is None:
            return "Placement indisponible"
        return (
            f"position {replacement.position} — {replacement.outgoing_club_name} → "
            f"{replacement.incoming_club_name} ({STATUS_LABELS[candidate.status]})"
        )
