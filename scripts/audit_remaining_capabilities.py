"""Regenerate the official remaining-capability audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pga_shootout.capability_audit import analyze_capability_audit, render_capability_audit_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-dir", default="data/pga_shootout.sqlite")
    parser.add_argument("--normalized-dir", default="data/normalized")
    parser.add_argument("--raw-catalog", default="data/raw/pga_club_stats_extract_v2_2026-07-21.json")
    parser.add_argument("--output", default="docs/CAPABILITY_AUDIT.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = analyze_capability_audit(
        user_dir=args.user_dir,
        normalized_dir=args.normalized_dir,
        raw_catalog_path=args.raw_catalog,
    )
    if args.json:
        # Escaped JSON also works in legacy Windows consoles using CP-1252.
        print(json.dumps(report.as_dict(), ensure_ascii=True, indent=2))
    else:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_capability_audit_markdown(report), encoding="utf-8")
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
