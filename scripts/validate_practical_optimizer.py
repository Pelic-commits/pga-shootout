"""Real-inventory acceptance report for practical optimizer workflows."""

from __future__ import annotations

import json
from pathlib import Path

from pga_shootout.strategy_optimizer import StrategyOptimizationRequest, StrategyOptimizer
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


def _optimizer() -> StrategyOptimizer:
    return StrategyOptimizer(
        user_data_path=DATABASE,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    )


def _candidate(value):
    candidates = tuple(item for item in value.retained_results if item.origin != "reference_bag")
    if not candidates:
        return None
    item = candidates[0]
    clubs = {club.club_id: club for club in item.clubs}
    steps = {}
    for step_id, club_id in item.active_assignments.items():
        step = next(value for value in clubs[club_id].steps if value.step_id == step_id)
        steps[step_id] = {
            "club": clubs[club_id].club_name,
            "stats": step.final_stats,
            "additional_metrics": step.additional_metrics,
        }
    return {
        "composition": item.composition,
        "active_assignments": item.active_assignments,
        "steps": steps,
        "category": item.comparison_group,
        "removed": item.removed_club_ids,
        "added": item.added_club_ids,
        "before_after": item.metric_values_from_reference,
        "gained_abilities": item.gained_contribution_ids,
        "lost_abilities": item.lost_contribution_ids,
        "unresolved": item.unresolved_abilities,
    }


def _around(club_id: str, required=(), target="par3_high_flight", strategy="par3", step="attack"):
    result = _optimizer().optimize(StrategyOptimizationRequest(
        strategy, limit=5, max_evaluations=240,
        search_mode="around_club", target_bag_id=target,
        fixed_club_id=club_id, fixed_step_id=step,
        required_club_ids=tuple(required),
    ))
    return {"search_seconds": result.search.total_seconds, "best": _candidate(result)}


def _replacement(required, excluded, target="par3_high_flight", strategy="par3"):
    result = _optimizer().optimize(StrategyOptimizationRequest(
        strategy, limit=5, max_evaluations=2000,
        search_mode="improve_bag", target_bag_id=target,
        required_club_ids=tuple(required), excluded_club_ids=tuple(excluded),
    ))
    return {"search_seconds": result.search.total_seconds, "best": _candidate(result)}


def _wave_in_bag(target: str, strategy: str):
    result = _optimizer().optimize(StrategyOptimizationRequest(
        strategy, limit=5, max_evaluations=2000,
        search_mode="test_new_club", target_bag_id=target, fixed_club_id="wave",
    ))
    return {"search_seconds": result.search.total_seconds, "best": _candidate(result)}


def main() -> int:
    bundle = load_user_data(DATABASE)
    entries = {item.club_id: item for item in bundle.inventory.entries}
    wave = entries["wave"]
    gearshift = entries["gearshift"]
    report = {
        "inventory": {
            "owned": sum(item.unlocked for item in bundle.inventory.entries),
            "observed_at": bundle.inventory.observed_at,
            "unknown_owned_levels": [item.club_id for item in bundle.inventory.entries if item.unlocked and item.current_level is None],
            "gearshift": {"owned": gearshift.unlocked, "level": gearshift.current_level},
            "wave": {"owned": wave.unlocked, "level": wave.current_level},
        },
        "high_flight": {
            "free": _around("high_flight"),
            "ember": _around("high_flight", ("ember",)),
            "maelstrom": _around("high_flight", ("maelstrom",)),
            "ember_maelstrom": _around("high_flight", ("ember", "maelstrom")),
            "gearshift": _around("high_flight", ("gearshift",)),
            "wave": _around("high_flight", ("wave",)),
        },
        "maelstrom_to_steadfast": _replacement(("steadfast",), ("maelstrom",)),
        "divebomb": {
            "free": _around("divebomb", target="par3_divebomb"),
            "ember": _around("divebomb", ("ember",), target="par3_divebomb"),
            "gearshift": _around("divebomb", ("gearshift",), target="par3_divebomb"),
            "wave": _around("divebomb", ("wave",), target="par3_divebomb"),
        },
        "wave_replacements": {
            strategy: {
                bag: _wave_in_bag(bag, strategy)
                for bag in ("par3_divebomb", "par3_high_flight")
            }
            for strategy in ("par3", "par4_short", "par4_long", "par5")
        },
        "three_step": _around(
            "high_flight", ("wave",), target="par3_high_flight",
            strategy="par4_long", step="drive",
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
