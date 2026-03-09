from __future__ import annotations

from pathlib import Path
import re

import PIL
from PIL import Image, ImageDraw, ImageFont


def apply_campaign_message(image: Image.Image, campaign_message: str) -> Image.Image:
    canvas = image.convert("RGBA").copy()
    width, height = canvas.size
    message = " ".join(campaign_message.split())
    if not message:
        return canvas

    headline, support = _split_message(message)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    _draw_bottom_gradient(overlay, width, height)
    draw = ImageDraw.Draw(overlay, "RGBA")

    panel_margin_x = max(36, width // 18)
    panel_margin_y = max(36, height // 24)
    panel_width = _panel_width(width, height)
    headline_font = _load_font(max(36, min(width, height) // 15), bold=True)
    support_font = _load_font(max(22, min(width, height) // 28))
    accent_width = max(42, width // 20)
    panel_padding_x = max(28, width // 32)
    panel_padding_y = max(24, height // 36)
    text_width = panel_width - (panel_padding_x * 2)

    headline_lines = _wrap_text(draw, headline, headline_font, text_width)
    support_lines = (
        _wrap_text(draw, support, support_font, text_width) if support else []
    )
    headline_line_height = _line_height(draw, headline_font)
    support_line_height = _line_height(draw, support_font)
    headline_spacing = max(8, headline_line_height // 5)
    support_spacing = max(6, support_line_height // 4)
    headline_height = len(headline_lines) * headline_line_height + max(
        0, len(headline_lines) - 1
    ) * headline_spacing
    support_height = len(support_lines) * support_line_height + max(
        0, len(support_lines) - 1
    ) * support_spacing
    gap_after_accent = max(20, height // 54)
    gap_between_blocks = max(12, height // 70) if support_lines else 0
    panel_height = (
        panel_padding_y * 2
        + accent_width // 8
        + gap_after_accent
        + headline_height
        + gap_between_blocks
        + support_height
    )
    panel_x = panel_margin_x
    panel_y = height - panel_margin_y - panel_height
    panel_right = min(width - panel_margin_x, panel_x + panel_width)

    draw.rounded_rectangle(
        [(panel_x, panel_y), (panel_right, panel_y + panel_height)],
        radius=max(22, width // 38),
        fill=(7, 10, 16, 150),
        outline=(255, 255, 255, 24),
        width=1,
    )

    accent_y = panel_y + panel_padding_y
    draw.rounded_rectangle(
        [
            (panel_x + panel_padding_x, accent_y),
            (panel_x + panel_padding_x + accent_width, accent_y + max(5, accent_width // 8)),
        ],
        radius=3,
        fill=(242, 210, 92, 235),
    )

    text_x = panel_x + panel_padding_x
    text_y = accent_y + max(5, accent_width // 8) + gap_after_accent
    for line in headline_lines:
        _draw_text_with_shadow(
            draw,
            (text_x, text_y),
            line,
            headline_font,
            fill=(250, 248, 242, 255),
        )
        text_y += headline_line_height + headline_spacing

    if support_lines:
        text_y += gap_between_blocks - headline_spacing
        for line in support_lines:
            _draw_text_with_shadow(
                draw,
                (text_x, text_y),
                line,
                support_font,
                fill=(232, 229, 221, 240),
                shadow_alpha=100,
            )
            text_y += support_line_height + support_spacing

    return Image.alpha_composite(canvas, overlay)


def _draw_bottom_gradient(overlay: Image.Image, width: int, height: int) -> None:
    gradient_top = int(height * 0.52)
    gradient_height = max(1, height - gradient_top)
    for index in range(gradient_height):
        progress = index / gradient_height
        alpha = int(210 * (progress**1.8))
        band = Image.new("RGBA", (width, 1), (6, 8, 12, alpha))
        overlay.paste(band, (0, gradient_top + index))


def _split_message(message: str) -> tuple[str, str]:
    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", message)
        if part.strip()
    ]
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])

    words = message.split()
    if len(words) <= 4:
        return message, ""

    split_index = max(2, len(words) // 2)
    return " ".join(words[:split_index]), " ".join(words[split_index:])


def _panel_width(width: int, height: int) -> int:
    if width > height:
        return int(width * 0.46)
    if width == height:
        return int(width * 0.74)
    return int(width * 0.8)


def _draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    shadow_alpha: int = 130,
) -> None:
    x, y = position
    draw.text((x, y + 2), text, font=font, fill=(0, 0, 0, shadow_alpha))
    draw.text((x, y), text, font=font, fill=fill)


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


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    base_candidates = ("DejaVuSans", "Arial")
    suffixes = ("-Bold.ttf", ".ttf") if bold else (".ttf", "-Bold.ttf")
    font_candidates = (
        *[
            f"{base}{suffix}"
            for base in base_candidates
            for suffix in suffixes
        ],
        *[
            str(Path(PIL.__file__).resolve().parent / "fonts" / f"{base}{suffix}")
            for base in ("DejaVuSans",)
            for suffix in suffixes
        ],
        *[
            str(Path("/System/Library/Fonts/Supplemental") / f"{base}{suffix}")
            for base in base_candidates
            for suffix in suffixes
        ],
    )
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()
