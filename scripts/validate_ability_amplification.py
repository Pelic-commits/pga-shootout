"""Read-only bounded before/after benchmark on the current real inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from pga_shootout.capability_audit import analyze_capability_audit, render_capability_audit_markdown
from pga_shootout.strategy_optimizer import BuildFromScratchRequest, StrategyOptimizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--modifier-payloads", action="store_true", help="Include explicit wind context and modifier/provenance results")
    parser.add_argument("--audit-only", action="store_true", help="Regenerate the requested capability documentation without running searches")
    args = parser.parse_args()
    database = Path("data/pga_shootout.sqlite")
    fingerprint = hashlib.sha256(database.read_bytes()).hexdigest()
    audit_report = analyze_capability_audit()
    audit = audit_report.as_dict()
    if args.audit_only:
        Path("docs/CAPABILITY_AUDIT.md").write_text(render_capability_audit_markdown(audit_report), encoding="utf-8")
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return
    runs = []
    cases = [("par3", primary, ()) for primary in ("blacksmith", "high_flight", "divebomb", "meteor")]
    if args.modifier_payloads:
        cases.append(("par4_long", "high_flight", ("head_crosswind",)))
    for strategy, primary, variants in cases:
        started = time.perf_counter()
        result = StrategyOptimizer().build_from_scratch(BuildFromScratchRequest(
            strategy, primary, variant_ids=variants, max_evaluations=args.budget, limit=5,
        ))
        run = {"strategy": strategy, "primary": primary, "variants": variants, "seconds": round(time.perf_counter() - started, 3),
               "evaluated": result.search.candidates_evaluated,
               "amplifier_frequency": sum("meteor" in item.composition for item in result.retained_results),
               "results": [{"composition": item.composition, "families": item.result_family_ids,
                            "unknowns": item.unresolved_abilities,
                            "deltas": item.metric_deltas_from_power_max,
                            "amplifications": [fact for club in item.clubs for row in club.steps for fact in row.amplifications],
                            "actives": {step: {"club": club.club_id, "stats": row.final_stats, "modifiers": row.additional_metrics}
                                        for step, club_id in item.active_assignments.items()
                                        for club in item.clubs if club.club_id == club_id
                                        for row in club.steps if row.step_id == step}}
                           for item in result.retained_results]}
        runs.append(run)
        print(f"{primary}: {run['seconds']}s; amplifier in {run['amplifier_frequency']}/{len(run['results'])}", flush=True)
    assert fingerprint == hashlib.sha256(database.read_bytes()).hexdigest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"database_sha256": fingerprint, "budget": args.budget,
                                 "coverage": {k: v for k, v in audit.items() if isinstance(v, int)},
                                 "runs": runs}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
