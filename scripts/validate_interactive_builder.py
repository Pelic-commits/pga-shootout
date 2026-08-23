"""Real-inventory acceptance matrix for the interactive bag builder."""

from __future__ import annotations

import json
from pathlib import Path

from pga_shootout.strategy_optimizer import StrategyOptimizationRequest, StrategyOptimizer


ROOT = Path(__file__).resolve().parents[1]


def active_values(candidate):
    result = {}
    for step_id, club_id in candidate.active_assignments.items():
        club = next(item for item in candidate.clubs if item.club_id == club_id)
        step = next(item for item in club.steps if item.step_id == step_id)
        result[step_id] = {
            "club": club.club_name,
            "power": step.final_stats["power"],
            "control": step.final_stats["control"],
            "spin": step.final_stats["spin"],
            "landing": dict(step.additional_metrics),
        }
    return result


def summarize(result):
    return {
        "seconds": result.search.total_seconds,
        "candidates_evaluated": result.search.candidates_evaluated,
        "active_assignments": result.search.active_assignments_considered,
        "criteria_satisfied": result.criteria_satisfied,
        "families": [item.user_name for item in result.result_families],
        "results": [
            {
                "badges": item.optimization_badges,
                "composition": item.composition,
                "active": active_values(item),
                "deltas_from_power_max": item.metric_deltas_from_power_max,
                "unresolved": item.unresolved_abilities,
            }
            for item in result.retained_results
        ],
    }


def main() -> int:
    optimizer = StrategyOptimizer(
        user_data_path=ROOT / "data" / "pga_shootout.sqlite",
        catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        strategy_registry_path=ROOT / "data" / "strategies" / "strategies.json",
    )

    def run(strategy, roles, *, minimums=None, primary=None, budget=1000):
        return optimizer.optimize(StrategyOptimizationRequest(
            strategy,
            search_mode="interactive_builder",
            club_roles=roles,
            metric_minimums=minimums or {},
            primary_step_id=primary or ("drive" if strategy in {"par4_long", "par5"} else "attack"),
            limit=10,
            max_evaluations=budget,
        ))

    cases = {
        "high_flight": run("par3", {"high_flight": "attack"}),
        "high_flight_ember": run("par3", {"high_flight": "attack", "ember": "putt"}),
        "high_flight_ember_maelstrom": run(
            "par3", {"high_flight": "attack", "ember": "putt", "maelstrom": "support"},
        ),
        "divebomb": run("par3", {"divebomb": "attack"}),
        "divebomb_ember": run("par3", {"divebomb": "attack", "ember": "putt"}),
        "high_flight_gearshift": run("par3", {"high_flight": "attack", "gearshift": "auto"}),
        "wave": run("par3", {"wave": "auto"}),
        "three_steps": run(
            "par5", {"high_flight": "drive", "divebomb": "approach", "ember": "putt"},
        ),
        "putt_minimum": run(
            "par3", {"high_flight": "attack", "ember": "putt"},
            minimums={"putt": {"power": 10, "control": 12}},
        ),
        "hybrid_green_attack": run(
            "par3", {"high_flight": "attack", "maelstrom": "support"},
        ),
        "hybrid_progression": run(
            "par5", {"high_flight": "drive", "maelstrom": "support", "ember": "putt"},
        ),
    }
    print(json.dumps({name: summarize(result) for name, result in cases.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
