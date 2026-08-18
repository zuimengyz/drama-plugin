from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REFERENCE_MARKS = {
    "B60RE2E_REF_GESHUIHAN.png": "REF_GESHUIHAN",
    "B60RE2E_REF_YANGGUOZHONG_REVISED.png": "REF_YANGGUOZHONG",
    "B60RE2E_REF_XUANZONG.png": "REF_XUANZONG",
    "B60RE2E_REF_CUIQIANYOU.png": "REF_CUIQIANYOU",
    "B60RE2E_REF_HUOBAGUIREN.png": "REF_HUOBAGUIREN",
    "B60RE2E_REF_TONGPASS.png": "REF_TONGPASS",
    "B60RE2E_REF_LINGBAO.png": "REF_LINGBAO",
    "B60RE2E_REF_CHANGAN.png": "REF_CHANGAN",
}


def apply_mark(source: Path, destination: Path, label: str, font_path: Path) -> None:
    with Image.open(source) as image:
        canvas = image.convert("RGBA")
        font_size = max(22, round(min(canvas.size) * 0.024))
        font = ImageFont.truetype(str(font_path), font_size)
        draw = ImageDraw.Draw(canvas, "RGBA")
        padding_x = round(font_size * 0.65)
        padding_y = round(font_size * 0.4)
        bbox = draw.textbbox((0, 0), label, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        right = canvas.width - round(font_size * 0.7)
        bottom = canvas.height - round(font_size * 0.7)
        left = right - width - (padding_x * 2)
        top = bottom - height - (padding_y * 2)
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=round(font_size * 0.3),
            fill=(0, 0, 0, 176),
            outline=(255, 255, 255, 150),
            width=max(1, round(font_size * 0.05)),
        )
        draw.text(
            (left + padding_x, top + padding_y - bbox[1]),
            label,
            font=font,
            fill=(255, 255, 255, 245),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(destination, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--font",
        type=Path,
        default=Path(r"C:\Windows\Fonts\arial.ttf"),
    )
    args = parser.parse_args()

    for filename, label in REFERENCE_MARKS.items():
        source = args.reference_dir / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        apply_mark(source, args.output_dir / filename, label, args.font)


if __name__ == "__main__":
    main()
