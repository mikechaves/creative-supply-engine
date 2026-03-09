from __future__ import annotations

from pathlib import Path

import PIL
from PIL import Image, ImageDraw, ImageFont


def apply_campaign_message(image: Image.Image, campaign_message: str) -> Image.Image:
    canvas = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    width, height = canvas.size

    font_size = max(28, width // 22)
    font = _load_font(font_size)
    padding_x = max(40, width // 20)
    padding_y = max(28, height // 28)
    max_text_width = width - (padding_x * 2)
    lines = _wrap_text(draw, campaign_message, font, max_text_width)
    line_height = _line_height(draw, font)
    line_spacing = max(8, line_height // 4)
    text_height = len(lines) * line_height + max(0, len(lines) - 1) * line_spacing
    banner_height = max(int(height * 0.2), text_height + padding_y * 2)
    banner_top = height - banner_height

    draw.rectangle([(0, banner_top), (width, height)], fill=(19, 19, 19, 180))

    text_y = banner_top + (banner_height - text_height) / 2
    for line in lines:
        draw.text((padding_x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_height + line_spacing

    return canvas


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    message: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = message.split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line: list[str] = []
    for word in words:
        tentative = " ".join(current_line + [word])
        if _text_width(draw, tentative, font) <= max_width or not current_line:
            current_line.append(word)
            continue
        lines.append(" ".join(current_line))
        current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def _text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _line_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), "Ag", font=font)
    return box[3] - box[1]


def _load_font(size: int) -> ImageFont.ImageFont:
    font_candidates = (
        "DejaVuSans.ttf",
        str(Path(PIL.__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"),
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    )
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()
