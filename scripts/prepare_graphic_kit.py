"""Prepare small offline UI assets from the supplied kit (Pillow, development only)."""

import argparse
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

# Asset-only spelling reconciliation; never changes catalogue data or rules.
ASSET_NAMES = {"endeavour.png": "endeavor.png"}


def prepare(archive: Path, destination: Path) -> None:
    icons = destination / "club_icons"
    icons.mkdir(parents=True, exist_ok=True)
    prefix = "PGA_Shootout_Graphic_Kit/"
    with ZipFile(archive) as kit:
        colors = json.loads(kit.read(prefix + "brand_colors.json"))
        (destination / "brand_colors.json").write_text(
            json.dumps(colors, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
        count = 0
        for entry in kit.infolist():
            if not entry.filename.startswith(prefix + "assets/clubs/") or not entry.filename.endswith(".png"):
                continue
            with Image.open(BytesIO(kit.read(entry))) as source:
                picture = source.convert("RGBA")
                bounds = picture.getbbox()
                if bounds:
                    picture = picture.crop(bounds)
                picture.thumbnail((112, 100), Image.Resampling.LANCZOS)
                tile = Image.new("RGBA", (120, 108))
                tile.alpha_composite(picture, ((120 - picture.width) // 2, (108 - picture.height) // 2))
                name = Path(entry.filename).name
                tile.save(icons / ASSET_NAMES.get(name, name), optimize=True)
                count += 1
    print(f"Prepared {count} club icons and {len(colors)} brand palettes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path, default=Path("src/pga_shootout/assets"))
    args = parser.parse_args()
    prepare(args.archive, args.destination)
