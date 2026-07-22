"""Small command-line entrypoint for raw-data inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .loader import load_raw_json, summarize_raw_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pga-shootout")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="inspect raw JSON without schema assumptions")
    inspect_parser.add_argument("path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        print(json.dumps(summarize_raw_json(load_raw_json(args.path)), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
