from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    if output.exists() and output.stat().st_size:
        raise RuntimeError(f"refusing to overwrite {output}")

    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if not font_path.is_file():
        raise RuntimeError(f"missing font: {font_path}")
    font = ImageFont.truetype(str(font_path), 34)

    with Image.open(source) as image:
        image.load()
        base = image.convert("RGBA")
        original_mode = image.mode

    margin, padding_x, padding_y = 24, 12, 10
    measure = ImageDraw.Draw(base)
    left, top, right, bottom = measure.textbbox((0, 0), args.label, font=font)
    panel = (
        margin,
        margin,
        margin + padding_x * 2 + right - left,
        margin + padding_y * 2 + bottom - top,
    )
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(panel, fill=(0, 0, 0, 176))
    draw.text((margin + padding_x - left, margin + padding_y - top), args.label, font=font, fill=(248, 248, 248, 255))
    annotated = Image.alpha_composite(base, overlay)

    difference = ImageChops.difference(base, annotated)
    outside_mask = Image.new("L", base.size, 255)
    ImageDraw.Draw(outside_mask).rectangle(panel, fill=0)
    outside_difference = Image.new("RGBA", base.size, (0, 0, 0, 0))
    outside_difference.paste(difference, mask=outside_mask)
    if outside_difference.getbbox() is not None:
        raise RuntimeError("pixels changed outside annotation panel")

    (annotated.convert("RGB") if original_mode == "RGB" else annotated).save(output, format="PNG", compress_level=6)
    print(json.dumps({
        "source": str(source),
        "sourceSha256": digest(source),
        "output": str(output),
        "outputSha256": digest(output),
        "dimensions": base.size,
        "label": args.label,
        "panel": panel,
        "font": str(font_path),
        "outsidePanelPixelsUnchanged": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
