"""Read-only real-inventory audit and reproducible bounded optimizer runs."""

import argparse
import json
from pathlib import Path
import time

from pga_shootout.capability_audit import _official_texts
from pga_shootout.strategy_optimizer import (
    BuildFromScratchRequest, StrategyOptimizer, CandidateSpec, _RuntimeEvaluator, _attach_power_tier_deltas,
)
from pga_shootout.strategy import StrategyRegistry
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import load_user_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="logs/context-variants/after.json")
    parser.add_argument("--budget", type=int, default=400)
    args = parser.parse_args()
    catalog = json.loads(Path("data/normalized/clubs_official.json").read_text(encoding="utf-8"))
    semantics = json.loads(Path("data/normalized/semantic_map.json").read_text(encoding="utf-8"))
    raw = json.loads(Path("data/raw/pga_club_stats_extract_v2_2026-07-21.json").read_text(encoding="utf-8"))
    inventory = {item.club_id: item for item in load_user_data("data/pga_shootout.sqlite").inventory.entries}
    audit = {}
    for identifier in ("meteor", "flashpoint"):
        club = catalog["clubs"][identifier]
        entry = inventory.get(identifier)
        audit[identifier] = {
            "identity": {key: club[key] for key in ("id", "name", "brand", "rarity", "club_type")},
            "inventory": {"owned": entry.unlocked if entry else False, "level": entry.current_level if entry else None},
            "levels": {key: value for key, value in club["levels"].items() if value["available"]},
            "texts": _official_texts(next(item for item in raw["clubs"] if item["name"] == club["name"])),
            "abilities": [{"id": ability["occurrence_id"],
                           "values": {key: value["official_notation"]["raw"] for key, value in ability["values_by_level"].items() if value},
                           "qualification": semantics["entries"]["label:" + ability["label_id"]]}
                          for ability in club["abilities"]],
        }
    runs = []
    for strategy, primary, variants in (
        ("par3", "blacksmith", ()), ("par3", "high_flight", ()),
        ("par4_long", "high_flight", ("head_crosswind",)),
        ("par3", "meteor", ()), ("par3", "flashpoint", ()),
    ):
        if primary not in inventory or not inventory[primary].unlocked or inventory[primary].current_level is None:
            runs.append({"primary": primary, "skipped": "owned club with known level required"})
            continue
        started = time.perf_counter()
        result = StrategyOptimizer().build_from_scratch(BuildFromScratchRequest(
            strategy, primary, variant_ids=variants, limit=5, max_evaluations=args.budget,
        ))
        run = {"strategy": strategy, "primary": primary, "variants": variants,
               "seconds": round(time.perf_counter() - started, 3), "evaluated": result.search.candidates_evaluated,
               "status": result.search.optimality_status, "results": []}
        for candidate in result.retained_results:
            run["results"].append({"composition": candidate.composition, "families": candidate.result_family_ids,
                                   "unresolved": candidate.unresolved_abilities,
                                   "deltas": candidate.metric_deltas_from_power_max,
                                   "active": {step_id: {"club": club_id, "stats": dict(step.final_stats), "modifiers": dict(step.additional_metrics)}
                                              for step_id, club_id in candidate.active_assignments.items()
                                              for club in candidate.clubs if club.club_id == club_id
                                              for step in club.steps if step.step_id == step_id}})
        runs.append(run)
        print(f"{strategy}/{primary}/{variants}: {run['seconds']}s, {len(run['results'])} results", flush=True)
    # Controlled real-data comparison, not an extra optimization or a claimed optimum.
    service = StrategyOptimizer()
    strategy = StrategyRegistry.load().resolve("par3")
    runtime = _RuntimeEvaluator("data/normalized/clubs_official.json", tuple(inventory.values()), None)
    controlled = []
    required = {"high_flight", "jumpstart", "cyclotron", "steadfast", "gearshift", "commonlaw"}
    if required <= runtime.clubs.keys():
        for support in ("jumpstart", "cyclotron"):
            spec = CandidateSpec(support, ("high_flight", support, "steadfast", "gearshift", "commonlaw"),
                                 {"attack": "high_flight", "putt": "gearshift"}, "build_from_scratch")
            quick = service._evaluate_quick(spec, strategy, runtime, EvaluationMode.PARTIAL)
            controlled.append(service._detail(quick, strategy, runtime, EvaluationMode.PARTIAL,
                                              ("power_max",) if not controlled else ("landing_profile",)))
        controlled = [
            {"composition": item.composition, "unresolved": item.unresolved_abilities,
             "attack": dict(item.clubs[0].steps[0].final_stats),
             "modifiers": dict(item.clubs[0].steps[0].additional_metrics),
             "deltas_from_first_bag": item.metric_deltas_from_power_max}
            for item in _attach_power_tier_deltas(tuple(controlled), strategy, "attack")
        ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"source": catalog["source"], "audit": audit, "runs": runs,
                                 "controlled_real_bag_comparison": controlled}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
