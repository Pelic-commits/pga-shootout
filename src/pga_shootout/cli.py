"""Small command-line entrypoint for raw-data inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .data_validation import validate_official_data
from .loader import load_raw_json, summarize_raw_json
from .user_data import ClubCatalogIndex, load_user_data, validate_user_data


def _add_user_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-dir", default="data/user")
    parser.add_argument("--catalog", default="data/normalized/clubs_official.json")


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        print(json.dumps(summarize_raw_json(load_raw_json(args.path)), indent=2, ensure_ascii=False))
    elif args.command == "validate-data":
        report = validate_official_data(args.raw_path, args.normalized_path)
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
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
