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
    for primary in ("blacksmith", "high_flight", "divebomb", "meteor"):
        started = time.perf_counter()
        result = StrategyOptimizer().build_from_scratch(BuildFromScratchRequest(
            "par3", primary, max_evaluations=args.budget, limit=5,
        ))
        run = {"primary": primary, "seconds": round(time.perf_counter() - started, 3),
               "evaluated": result.search.candidates_evaluated,
               "amplifier_frequency": sum("meteor" in item.composition for item in result.retained_results),
               "results": [{"composition": item.composition, "families": item.result_family_ids,
                            "unknowns": item.unresolved_abilities,
                            "actives": {step: {"club": club.club_id, "stats": row.final_stats}
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
