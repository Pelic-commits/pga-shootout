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
}
METRIC_LABELS = {
    "power": "Power",
    "control": "Control",
    "spin": "Spin",
    "loft_angle_degrees": "Loft",
    "wind_resistance_percent": "Wind Resistance",
    "bounce_reduction_percent": "Bounce Reduction",
    "groundspin": "Groundspin",
    "swing_speed": "Swing Speed",
    "gravity_reduction_percent": "Gravity Reduction",
    "launch_angle_degrees": "Launch Angle",
}


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


@dataclass(frozen=True)
class StepPresentation:
    step_id: str
    label: str
    content: str


@dataclass(frozen=True)
class CandidateDetailPresentation:
    title: str
    steps: tuple[StepPresentation, ...]
    synergies: str
    technical_details: str
    clipboard_summary: str


@dataclass(frozen=True)
class OptimizationPresentation:
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
        candidates = tuple(self._candidate_list(index, item, step_labels) for index, item in enumerate(result.retained_results, 1))
        details = tuple(self._candidate_detail(index, item, step_labels) for index, item in enumerate(result.retained_results, 1))
        return OptimizationPresentation(
            warning_text=self._warnings(result),
            search_information=self._search_information(result),
            candidates=candidates,
            details=details,
        )

    def _candidate_list(
        self,
        index: int,
        candidate: StrategyCandidateResult,
        step_labels: Mapping[str, str],
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
        )

    def _strengths(self, candidate: StrategyCandidateResult, step_labels: Mapping[str, str]) -> str:
        facts: list[str] = []
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
            steps=steps,
            synergies=self._synergies(candidate, step_labels),
            technical_details=self._technical(candidate, step_labels),
            clipboard_summary=clipboard,
        )

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
                    lines.append("Métriques additionnelles :")
                    lines.extend(
                        f"  {_metric_label(metric)} : {value:g}{_metric_unit(metric)}"
                        for metric, value in sorted(step.additional_metrics.items())
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
        lines = ["Exigences"]
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
        return "\n".join(lines)

    @staticmethod
    def _search_information(result: StrategyOptimizationResult) -> str:
        total = result.search.generation_seconds + result.search.evaluation_seconds
        return "\n".join((
            "Informations sur la recherche",
            f"Candidats générés : {result.search.reduced_candidates_generated}",
            f"Candidats évalués : {result.search.candidates_evaluated}",
            f"Doublons éliminés : {result.search.candidate_result_duplicates_removed}",
            f"Durée mesurée : {total:.2f} s",
            f"Limite de sécurité atteinte : {'oui' if result.search.safety_limit_reached else 'non'}",
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
        self._callback_queue: Queue[Callable[[], None]] = Queue()
        self.controller = StrategyOptimizerGuiController(
            self.optimizer,
            schedule=self._callback_queue.put,
            on_state=self._on_state,
            on_success=self._on_success,
            on_error=self._on_error,
        )
        self._build()
        self.root.after(25, self._poll_callbacks)
        self._refresh_variants()
        self._toggle_mode()

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        parameters = ttk.LabelFrame(self.root, text="1 — Paramètres", padding=10)
        parameters.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ttk.Label(parameters, text="Stratégie :").grid(row=0, column=0, sticky="w")
        strategy_box = ttk.Combobox(parameters, textvariable=self.strategy_name, values=tuple(self.strategy_by_label), state="readonly", width=28)
        strategy_box.grid(row=0, column=1, padx=(5, 18))
        strategy_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_variants())
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

        self.analyze_button = ttk.Button(parameters, text="Lancer l’analyse", command=self._start)
        self.analyze_button.grid(row=0, column=10, padx=(20, 6))
        ttk.Button(parameters, text="Gérer mon inventaire", command=self._open_inventory).grid(row=0, column=11, padx=6)
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
        table = ttk.Frame(list_zone)
        table.pack(fill="both", expand=True)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        columns = ("number", "category", "composition", "active", "unresolved", "neutral", "strengths")
        self.candidate_tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse", height=15)
        labels = {
            "number": "N°", "category": "Catégorie", "composition": "Composition ordonnée",
            "active": "Clubs actifs", "unresolved": "Non résolues", "neutral": "Club neutre", "strengths": "Points forts calculables",
        }
        widths = {"number": 40, "category": 170, "composition": 330, "active": 240, "unresolved": 80, "neutral": 80, "strengths": 290}
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
        self.export_json_button.pack(side="left")
        self.export_text_button.pack(side="left", padx=6)
        self.copy_button.pack(side="left")
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

    def _toggle_mode(self) -> None:
        self.scenario_entry.configure(state="disabled" if self.real_mode.get() else "normal")

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
        return OptimizationGuiOptions(
            strategy_id=self.strategy_by_label[self.strategy_name.get()],
            variant_id=self.variant_by_label[self.variant_name.get()],
            real_mode=self.real_mode.get(),
            scenario_level=scenario,
            limit=limit,
            max_evaluations=max_evaluations,
        )

    def _start(self) -> None:
        try:
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
        self.candidate_tree.delete(*self.candidate_tree.get_children())
        for index, item in enumerate(self.presentation.candidates):
            self.candidate_tree.insert("", "end", iid=str(index), values=(
                item.display_number, item.category, item.composition, item.active_clubs,
                item.unresolved_count, "Oui" if item.has_neutral_club else "Non", item.strengths,
            ))
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
        for step in detail.steps:
            self._add_text_tab(step.label, step.content)
        self._add_text_tab("Pourquoi ces clubs ?", detail.synergies)
        self._add_text_tab("Détails techniques", detail.technical_details)
        self.copy_button.configure(state="normal")

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
