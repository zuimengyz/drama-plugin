from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FONT_PATH = Path("/System/Library/Fonts/STHeiti Light.ttc")
FONT_SIZE = 34
MARGIN = 24
PADDING_X = 12
PADDING_Y = 10
BACKGROUND = (0, 0, 0, 176)
FOREGROUND = (248, 248, 248, 255)

ITEMS = (
    {
        "source": "character-master-liling-provider.png",
        "output": "character-master-liling-reference.png",
        "expected_sha256": "41ec29c7d6ae18c3503e50041c1784dc5ec74fd3770c5407e8cd22517a3135df",
        "label": "人物：李陵",
    },
    {
        "source": "scene-master-qionglu-provider.png",
        "output": "scene-master-qionglu-reference.png",
        "expected_sha256": "e20301d471c46fb2e51f17c73727803c22ed5517658b47f3e2675a4844d35e90",
        "label": "场景：苏武穹庐",
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def annotate(item: dict[str, str], font: ImageFont.FreeTypeFont) -> dict[str, object]:
    source_path = ROOT / item["source"]
    output_path = ROOT / item["output"]
    source_hash = sha256(source_path)
    if source_hash != item["expected_sha256"]:
        raise RuntimeError(f"Provider integrity mismatch: {source_path.name}")

    with Image.open(source_path) as source_image:
        source_image.load()
        original_mode = source_image.mode
        base = source_image.convert("RGBA")

    if base.size != (1024, 1024):
        raise RuntimeError(f"Unexpected dimensions: {source_path.name} {base.size}")

    label = item["label"]
    measure = ImageDraw.Draw(base)
    left, top, right, bottom = measure.textbbox((0, 0), label, font=font)
    text_width = right - left
    text_height = bottom - top
    panel = (
        MARGIN,
        MARGIN,
        MARGIN + PADDING_X * 2 + text_width,
        MARGIN + PADDING_Y * 2 + text_height,
    )

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(panel, fill=BACKGROUND)
    text_position = (MARGIN + PADDING_X - left, MARGIN + PADDING_Y - top)
    draw.text(text_position, label, font=font, fill=FOREGROUND)
    annotated = Image.alpha_composite(base, overlay)

    difference = ImageChops.difference(base, annotated)
    outside_mask = Image.new("L", base.size, 255)
    ImageDraw.Draw(outside_mask).rectangle(panel, fill=0)
    outside_difference = Image.new("RGBA", base.size, (0, 0, 0, 0))
    outside_difference.paste(difference, mask=outside_mask)
    if outside_difference.getbbox() is not None:
        raise RuntimeError(f"Pixels changed outside annotation panel: {source_path.name}")

    if output_path.exists() and output_path.stat().st_size > 0:
        raise RuntimeError(f"Refusing to overwrite non-empty output: {output_path.name}")

    if original_mode == "RGB":
        rendered = annotated.convert("RGB")
    else:
        rendered = annotated
    rendered.save(output_path, format="PNG", optimize=False, compress_level=6)

    with Image.open(output_path) as check:
        check.load()
        decoded_size = check.size
        decoded_mode = check.mode

    return {
        "source": source_path.name,
        "source_sha256": source_hash,
        "output": output_path.name,
        "output_sha256": sha256(output_path),
        "output_size": output_path.stat().st_size,
        "dimensions": decoded_size,
        "mode": decoded_mode,
        "label": label,
        "panel": panel,
        "font_family": font.getname(),
        "font_path": str(FONT_PATH),
        "font_size": FONT_SIZE,
        "margin": MARGIN,
        "padding": (PADDING_X, PADDING_Y),
        "outside_panel_pixels_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--label")
    args = parser.parse_args()

    if not FONT_PATH.is_file():
        raise RuntimeError(f"Required system font is missing: {FONT_PATH}")
    font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    supplied = (args.input, args.output, args.label)
    if any(supplied) and not all(supplied):
        parser.error("--input, --output, and --label must be supplied together")
    if all(supplied):
        input_path = Path(args.input).resolve()
        items = ({
            "source": str(input_path),
            "output": str(Path(args.output).resolve()),
            "expected_sha256": sha256(input_path),
            "label": args.label,
        },)
    else:
        items = ITEMS
    results = [annotate(item, font) for item in items]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
