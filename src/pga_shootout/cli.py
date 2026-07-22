"""Small command-line entrypoint for raw-data inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .bag_evaluation import evaluate_saved_bag, render_bag_evaluation
from .coverage import generate_coverage_report
from .data_validation import validate_official_data
from .loader import load_raw_json, summarize_raw_json
from .models import EvaluationMode
from .normalization import normalize_catalog
from .user_data import ClubCatalogIndex, load_user_data, validate_user_data


def _add_user_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-dir", default="data/user")
    parser.add_argument("--catalog", default="data/normalized/clubs_official.json")


def _level_value(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pga-shootout")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="inspect raw JSON without schema assumptions")
    inspect_parser.add_argument("path")
    validate_parser = subparsers.add_parser("validate-data", help="validate official data provenance and structure")
    validate_parser.add_argument("raw_path")
    validate_parser.add_argument("normalized_path")
    for command, help_text in (
        ("user-validate", "validate all user data files"),
        ("user-account", "display the user account summary"),
        ("user-inventory", "list known inventory entries"),
        ("user-upgrades", "list currently available upgrades"),
        ("user-bags", "display saved user bags"),
    ):
        _add_user_paths(subparsers.add_parser(command, help=help_text))
    evaluate_parser = subparsers.add_parser("evaluate-bag", help="evaluate a saved user bag through the rule engine")
    evaluate_parser.add_argument("bag_id")
    evaluate_parser.add_argument("--level", required=True, type=_level_value, help="explicit scenario level for all bag clubs")
    evaluate_parser.add_argument("--current-club", help="stable club identifier; defaults to the first bag position")
    _add_user_paths(evaluate_parser)
    mode_group = evaluate_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--strict", action="store_true")
    mode_group.add_argument("--partial", action="store_true")
    normalize_parser = subparsers.add_parser("normalize", help="regenerate structural ability artifacts without interpretation")
    normalize_parser.add_argument("--source", default="data/normalized/clubs_official.json")
    normalize_parser.add_argument("--output-dir", default="data/normalized")
    coverage_parser = subparsers.add_parser("coverage", help="regenerate mechanic coverage report")
    coverage_parser.add_argument("--normalized-dir", default="data/normalized")
    coverage_parser.add_argument("--output", default="docs/MECHANIC_COVERAGE.md")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        print(json.dumps(summarize_raw_json(load_raw_json(args.path)), indent=2, ensure_ascii=False))
    elif args.command == "validate-data":
        report = validate_official_data(args.raw_path, args.normalized_path)
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    elif args.command == "coverage":
        report = generate_coverage_report(args.normalized_dir, args.output)
        print(json.dumps({
            "total_groups": report.total_groups,
            "implemented_groups": report.implemented_groups,
            "occurrence_coverage_percent": report.occurrence_coverage_percent,
            "club_coverage_percent": report.club_coverage_percent,
            "report": args.output,
        }, indent=2, ensure_ascii=False))
    elif args.command == "normalize":
        summary = normalize_catalog(args.source, args.output_dir)
        print(json.dumps(summary.__dict__, indent=2, ensure_ascii=False))
    elif args.command == "evaluate-bag":
        mode = EvaluationMode.STRICT if args.strict else EvaluationMode.PARTIAL
        evaluation = evaluate_saved_bag(
            args.bag_id,
            level=args.level,
            mode=mode,
            user_dir=args.user_dir,
            catalog_path=args.catalog,
            current_club_id=args.current_club,
        )
        print(render_bag_evaluation(evaluation))
        return 1 if evaluation.strict_failed else 0
    elif args.command.startswith("user-"):
        bundle = load_user_data(args.user_dir)
        report = validate_user_data(bundle, ClubCatalogIndex.load(args.catalog))
        if args.command == "user-validate":
            output = report.as_dict()
        elif args.command == "user-account":
            output = {
                "player_name": bundle.account.player_name,
                "player_level": bundle.account.player_level,
                "fedex_reward_target_level": bundle.account.fedex_reward_target_level,
                "priority_club_id": bundle.account.priority_club_id,
                "free_to_play": bundle.account.free_to_play,
            }
        elif args.command == "user-inventory":
            output = [
                {
                    "club_id": entry.club_id,
                    "display_name": entry.display_name,
                    "current_level": entry.current_level,
                    "cards_owned": entry.cards_owned,
                    "cards_required_for_next_upgrade": entry.cards_required_for_next_upgrade,
                }
                for entry in bundle.inventory.entries
            ]
        elif args.command == "user-upgrades":
            output = [
                {"club_id": entry.club_id, "display_name": entry.display_name}
                for entry in bundle.inventory.entries
                if entry.upgrade_available
            ]
        else:
            output = [
                {"id": bag.identifier, "name": bag.name, "status": bag.status, "club_ids": bag.club_ids}
                for bag in bundle.bags
            ]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        if not report.valid:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
