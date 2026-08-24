import json
import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from pga_shootout.models import EvaluationMode
from pga_shootout.strategy_optimizer import (
    ClubExclusion,
    StrategyOptimizationRequest,
    StrategyOptimizer,
)
from pga_shootout.strategy_optimizer_gui import (
    OptimizationGuiOptions,
    StrategyOptimizerGuiController,
    StrategyOptimizerPresenter,
    export_result_json,
    export_result_text,
    french_optimizer_error,
    suggested_export_name,
)


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


@pytest.fixture(scope="module")
def presenter():
    return StrategyOptimizerPresenter.load(REGISTRY)


@pytest.fixture(scope="module")
def par3_result():
    return StrategyOptimizer(
        user_data_path=DATABASE,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    ).optimize(StrategyOptimizationRequest("par3", limit=5, max_evaluations=20))


@pytest.fixture(scope="module")
def par4_long_result():
    return StrategyOptimizer(
        user_data_path=DATABASE,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    ).optimize(StrategyOptimizationRequest("par4_long", limit=2, max_evaluations=10))


@pytest.fixture(scope="module")
def interactive_result():
    return StrategyOptimizer(
        user_data_path=DATABASE,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    ).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder",
        club_roles={"high_flight": "attack", "ember": "putt"},
        primary_step_id="attack", limit=5, max_evaluations=1000,
    ))


def test_loads_strategy_names_dynamically_without_internal_ids(presenter):
    choices = presenter.strategy_choices()
    assert [item.label for item in choices] == ["Sac Par 3", "Sac Par 4 court", "Sac Par 4 long", "Sac Par 5"]
    assert [item.identifier for item in choices] == ["par3", "par4_short", "par4_long", "par5"]


def test_lists_only_compatible_variants_with_player_labels(presenter):
    assert [(item.identifier, item.label) for item in presenter.variant_choices("par3")] == [(None, "Aucune variante")]
    assert [(item.identifier, item.label) for item in presenter.variant_choices("par4_long")] == [
        (None, "Aucune variante"),
        ("head_crosswind", "Vent contraire / latéral"),
    ]


def test_real_mode_is_default_and_never_supplies_a_common_level():
    options = OptimizationGuiOptions("par3")
    request = options.to_request()
    assert options.real_mode
    assert request.scenario_level is None
    assert request.mode == EvaluationMode.PARTIAL


def test_optional_empirical_reference_is_transmitted_without_numeric_threshold():
    request = OptimizationGuiOptions("par3", reference_bag_id="par3_divebomb").to_request()
    assert request.reference_bag_id == "par3_divebomb"
    assert not hasattr(request, "minimum_power")


def test_local_search_modes_are_transmitted_without_new_business_rules():
    improve = OptimizationGuiOptions(
        "par3", search_mode="improve_bag", target_bag_id="par3_high_flight", replacement_depth=2,
    ).to_request()
    assert (improve.search_mode, improve.target_bag_id, improve.replacement_depth) == (
        "improve_bag", "par3_high_flight", 2,
    )
    around = OptimizationGuiOptions(
        "par3", search_mode="around_club", fixed_club_id="gearshift",
    ).to_request()
    assert (around.search_mode, around.fixed_club_id) == ("around_club", "gearshift")


def test_default_gui_workflow_is_independent_build_from_scratch():
    request = OptimizationGuiOptions(
        "par3", club_roles={"blacksmith": "auto"},
    ).to_request()
    assert request.search_mode == "build_from_scratch"
    assert request.reference_bag_id is None
    assert request.target_bag_id is None


def test_targeted_replacement_type_policy_is_explicit_and_defaults_to_same_type():
    default = OptimizationGuiOptions("par5", search_mode="replace_club").to_request()
    broad = OptimizationGuiOptions(
        "par5", search_mode="replace_club", replacement_type_policy="all_types",
    ).to_request()
    assert default.replacement_type_policy == "same_type"
    assert broad.replacement_type_policy == "all_types"


def test_user_constraints_are_transmitted_as_structural_options():
    request = OptimizationGuiOptions(
        "par3", search_mode="improve_bag", target_bag_id="par3_high_flight",
        required_club_ids=("ember", "gearshift"), excluded_club_ids=("sunstorm",),
        locked_positions={3: "ember"}, keep_current_putter=True, fixed_step_id="putt",
    ).to_request()
    assert request.required_club_ids == ("ember", "gearshift")
    assert request.excluded_club_ids == ("sunstorm",)
    assert request.locked_positions == {3: "ember"}
    assert request.keep_current_putter and request.fixed_step_id == "putt"


def test_interactive_builder_options_transmit_roles_and_factual_minimums():
    request = OptimizationGuiOptions(
        "par3", search_mode="interactive_builder",
        club_roles={"high_flight": "attack", "ember": "putt", "maelstrom": "support"},
        metric_minimums={"attack": {"control": 11, "spin": 10}, "putt": {"power": 12, "control": 12}},
        primary_step_id="attack", locked_positions={3: "maelstrom"},
    ).to_request()
    assert request.club_roles == {"high_flight": "attack", "ember": "putt", "maelstrom": "support"}
    assert request.metric_minimums["putt"] == {"power": 12, "control": 12}
    assert request.primary_step_id == "attack"
    assert request.locked_positions == {3: "maelstrom"}


def test_scenario_mode_requires_and_transmits_explicit_level():
    with pytest.raises(ValueError, match="niveau"):
        OptimizationGuiOptions("par3", real_mode=False).to_request()
    request = OptimizationGuiOptions("par3", real_mode=False, scenario_level=12).to_request()
    assert request.scenario_level == 12
    with pytest.raises(ValueError, match="compris entre 1 et 12"):
        OptimizationGuiOptions("par3", real_mode=False, scenario_level=13).to_request()


def test_controller_runs_off_ui_path_disables_reentry_and_marshals_result(par3_result):
    state_changes = []
    success = []
    errors = []
    scheduled = []

    class FakeOptimizer:
        def optimize(self, _request):
            return par3_result

    class DeferredThread:
        def __init__(self, *, target, daemon):
            assert daemon
            self.target = target
            scheduled.append(self)

        def start(self):
            pass

    controller = StrategyOptimizerGuiController(
        FakeOptimizer(),
        schedule=lambda callback: callback(),
        on_state=lambda running, text: state_changes.append((running, text)),
        on_success=lambda result, elapsed: success.append((result, elapsed)),
        on_error=lambda message, technical: errors.append((message, technical)),
        thread_factory=DeferredThread,
    )
    assert controller.start(OptimizationGuiOptions("par3"))
    assert controller.running
    assert not controller.start(OptimizationGuiOptions("par3"))
    assert state_changes == [(True, "Analyse en cours…")]
    scheduled[0].target()
    assert not controller.running
    assert success[0][0] is par3_result
    assert state_changes[-1][0] is False
    assert not errors


def test_controller_converts_calculation_error_to_french_without_traceback():
    errors = []

    class FailingOptimizer:
        def optimize(self, _request):
            raise RuntimeError("secret technical detail")

    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target

        def start(self):
            self.target()

    controller = StrategyOptimizerGuiController(
        FailingOptimizer(),
        schedule=lambda callback: callback(),
        on_state=lambda *_args: None,
        on_success=lambda *_args: pytest.fail("unexpected success"),
        on_error=lambda message, technical: errors.append((message, technical)),
        thread_factory=ImmediateThread,
    )
    assert controller.start(OptimizationGuiOptions("par3"))
    assert "erreur de calcul" in errors[0][0]
    assert "Traceback" not in errors[0][0]
    assert "secret technical detail" not in errors[0][0]
    assert "secret technical detail" in errors[0][1]


def test_presenter_builds_continuous_user_list_without_technical_ranking_terms(presenter, par3_result):
    presentation = presenter.present(par3_result)
    assert len(presentation.candidates) == len(par3_result.retained_results)
    first = presentation.candidates[0]
    assert first.display_number == 1
    assert first.composition.count(" · ") == 4
    assert first.category == "Compromis partiellement évalué"
    combined = "\n".join(vars(item).__str__() for item in presentation.candidates)
    assert "candidate_id" not in combined
    assert "comparison_layer" not in combined
    assert "Pareto" not in combined
    assert any(item.families for item in presentation.candidates)
    assert {item.user_name for item in par3_result.result_families} == {
        "Iron le plus puissant", "Irons : puissance et contrôle",
        "Iron le plus stable", "Meilleur concurrent tous types",
    }


def test_detail_contains_five_clubs_base_final_and_missing_stat(presenter, par3_result):
    detail = presenter.present(par3_result).details[0]
    first_step = detail.steps[0].content
    assert sum(first_step.count(club.club_name) for club in par3_result.retained_results[0].clubs) >= 5
    assert "Power" in first_step and "→" in first_step
    assert "Spin        —" in first_step


def test_additional_metrics_are_rendered_dynamically(presenter, par3_result):
    content = "\n".join(step.content for step in presenter.present(par3_result).details[0].steps)
    produced = {
        metric
        for club in par3_result.retained_results[0].clubs
        for step in club.steps
        for metric in step.additional_metrics
    }
    assert produced
    for metric in produced:
        expected = metric.replace("_", " ").title()
        assert expected in content or metric in {
            "loft_angle_degrees", "wind_resistance_percent", "bounce_reduction_percent",
        }
    assert "seulement descriptives" in content


def test_all_four_role_labels_and_neutral_explanation_are_supported(presenter, par3_result):
    candidate = par3_result.retained_results[0]
    roles = ("active", "support", "hybrid", "neutral", "neutral")
    clubs = tuple(replace(club, role=role) for club, role in zip(candidate.clubs, roles, strict=True))
    custom = replace(par3_result, retained_results=(replace(candidate, clubs=clubs),))
    detail = presenter.present(custom).details[0]
    text = "\n".join((*[step.content for step in detail.steps], detail.synergies))
    for label in ("actif", "support", "hybride", "neutre"):
        assert f"rôle {label}" in text or f"— {label}" in text
    assert "Aucun effet différenciant observé dans ce sac." in detail.synergies


def test_contributions_received_sent_and_counterfactuals_are_visible(presenter, par3_result):
    synergies = presenter.present(par3_result).details[0].synergies
    assert "Contributions envoyées" in synergies
    assert "Contributions reçues" in synergies
    assert "Perte observée sans ce club" in synergies
    assert " → " in synergies


def test_warning_and_search_information_are_explicit(presenter, par3_result):
    presentation = presenter.present(par3_result)
    assert "portée réelle" in presentation.warning_text
    assert "réussite du putt" in presentation.warning_text
    assert "optimum absolu n’est pas garanti" in presentation.warning_text
    assert f"Candidats générés : {par3_result.search.reduced_candidates_generated}" in presentation.search_information
    assert "Limite de sécurité atteinte" in presentation.search_information


def test_unknown_level_exclusion_is_explained_to_user(presenter, par3_result):
    result = replace(
        par3_result,
        excluded_clubs=(ClubExclusion("club_x", "Club X", "niveau utilisateur inconnu"),),
    )
    warning = presenter.present(result).warning_text
    assert "Club X" in warning
    assert "niveau utilisateur inconnu" in warning


def test_json_and_text_exports_use_the_domain_result(tmp_path, par3_result):
    json_path = export_result_json(par3_result, tmp_path / "result.json")
    text_path = export_result_text(par3_result, tmp_path / "result.txt")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["strategy_id"] == "par3"
    assert payload["aggregate_score"] is None
    assert payload["result_families"]
    assert payload["type_comparison"]
    assert "Optimisation de stratégie : par3" in text_path.read_text(encoding="utf-8")
    assert suggested_export_name("par3", "json", datetime(2026, 8, 5, 1, 30)) == "resultats_par3_2026-08-05_0130.json"


def test_clipboard_summary_is_self_contained(presenter, par3_result):
    summary = presenter.present(par3_result).details[0].clipboard_summary
    assert "Proposition 1" in summary
    assert all(club.club_name in summary for club in par3_result.retained_results[0].clubs)
    assert "Pourquoi ce club est présent" in summary


def test_par3_uses_player_step_labels_and_never_claims_reach(presenter, par3_result):
    detail = presenter.present(par3_result).details[0]
    expected = [step.name for step in presenter.registry.get("par3").sequence]
    assert [item.label for item in detail.steps] == expected
    assert "reach_green" not in "\n".join(step.content for step in detail.steps)
    assert "indeterminate" in detail.technical_details


def test_three_step_strategy_can_be_presented_without_special_case(presenter, par4_long_result):
    presentation = presenter.present(par4_long_result)
    assert presentation.candidates
    expected = [step.name for step in presenter.registry.get("par4_long").sequence]
    assert [item.label for item in presentation.details[0].steps] == expected
    assert all(len(candidate.clubs) == 5 for candidate in par4_long_result.retained_results)


def test_interactive_presentation_shows_badge_and_deltas_without_opening_technical_details(
    presenter, interactive_result,
):
    presentation = presenter.present(interactive_result)
    assert presentation.candidates[0].strengths.startswith("MEILLEURE PUISSANCE TROUVÉE")
    assert "MEILLEURE PUISSANCE TROUVÉE" in presentation.details[0].overview
    alternative = next(
        detail for candidate, detail in zip(interactive_result.retained_results, presentation.details, strict=True)
        if any("POUR -" in badge for badge in candidate.optimization_badges)
    )
    assert "ÉCART AVEC LA MEILLEURE PUISSANCE TROUVÉE" in alternative.overview


def test_local_presentation_separates_attack_landing_and_exact_before_after(presenter):
    result = StrategyOptimizer(
        user_data_path=DATABASE, catalog_path=CATALOG, strategy_registry_path=REGISTRY,
    ).optimize(StrategyOptimizationRequest(
        "par3", limit=2, max_evaluations=20, search_mode="improve_bag",
        target_bag_id="par3_high_flight", required_club_ids=("steadfast",),
    ))
    candidate = next(item for item in result.retained_results if item.origin != "reference_bag")
    overview = presenter.present(replace(result, retained_results=(candidate,))).details[0].overview
    for expected in (
        "COMPARAISON AVANT / APRÈS", "CLUBS RETIRÉS", "CLUBS AJOUTÉS",
        "CHANGEMENTS DE POSITION", "PROFIL D’ATTAQUE", "GAINS", "PERTES", "INCHANGÉ",
    ):
        assert expected in overview
    assert "→" in overview


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (FileNotFoundError("missing"), "introuvables"),
        (sqlite3.OperationalError("locked"), "base de données"),
        (RuntimeError("boom"), "Vos données n’ont pas été modifiées"),
    ),
)
def test_user_errors_are_french_and_never_include_traceback(error, expected):
    message = french_optimizer_error(error)
    assert expected in message
    assert "Traceback" not in message


def test_windows_launcher_is_self_contained_and_hides_python_tracebacks():
    launcher = (ROOT / "OPTIMISER_MES_SACS.bat").read_text(encoding="utf-8")
    for expected in ('cd /d "%~dp0"', "PYTHONUTF8=1", "%~dp0scripts\\windows_gui_launcher.ps1", "%*"):
        assert expected in launcher
    assert "Traceback" not in launcher

    powershell = (ROOT / "scripts" / "windows_gui_launcher.ps1").read_text(encoding="utf-8")
    for expected in (
        "windows_python_probe.py", "--require-compatible", "Remove-Item Env:TCL_LIBRARY",
        "Remove-Item Env:TK_LIBRARY", "pga_shootout.gui_preflight", "Start-Process",
        "pga_shootout.strategy_optimizer_gui", "pyvenv.cfg",
    ):
        assert expected in powershell
    assert "C:\\Users\\Pelic" not in powershell
    assert "data\\pga_shootout.sqlite" not in powershell
