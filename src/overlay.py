from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import PIL
from PIL import Image, ImageDraw, ImageFont

from src.brief_loader import BrandBrief


@dataclass(frozen=True)
class OverlayStyle:
    gradient_rgb: tuple[int, int, int]
    panel_fill: tuple[int, int, int, int]
    panel_outline: tuple[int, int, int, int]
    accent_fill: tuple[int, int, int, int]
    text_fill: tuple[int, int, int, int]
    support_fill: tuple[int, int, int, int]
    cta_fill: tuple[int, int, int, int]
    cta_text_fill: tuple[int, int, int, int]
    safe_margin_x_ratio: float = 0.055
    safe_margin_y_ratio: float = 0.05


def overlay_style_from_brand(brand: BrandBrief) -> OverlayStyle:
    primary = _hex_to_rgb(brand.colors.primary)
    secondary = _hex_to_rgb(brand.colors.secondary)
    accent = _hex_to_rgb(brand.colors.accent)
    text_light = _hex_to_rgb(brand.colors.text_light)
    return OverlayStyle(
        gradient_rgb=primary,
        panel_fill=secondary + (168,),
        panel_outline=text_light + (28,),
        accent_fill=accent + (235,),
        text_fill=text_light + (255,),
        support_fill=text_light + (224,),
        cta_fill=accent + (245,),
        cta_text_fill=primary + (255,),
    )


def apply_campaign_message(
    image: Image.Image,
    campaign_message: str,
    style: OverlayStyle,
    cta: str | None = None,
) -> Image.Image:
    canvas = image.convert("RGBA").copy()
    width, height = canvas.size
    message = " ".join(campaign_message.split())
    if not message:
        return canvas

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    _draw_bottom_gradient(overlay, width, height, style.gradient_rgb)
    draw = ImageDraw.Draw(overlay, "RGBA")

    headline, support = _split_message(message)
    margin_x = max(32, int(width * style.safe_margin_x_ratio))
    margin_y = max(32, int(height * style.safe_margin_y_ratio))
    panel_width = _panel_width(width, height)
    panel_padding_x = max(26, width // 34)
    panel_padding_y = max(22, height // 38)
    text_width = panel_width - panel_padding_x * 2

    headline_font = _load_font(max(36, min(width, height) // 15), bold=True)
    support_font = _load_font(max(22, min(width, height) // 28))
    cta_font = _load_font(max(18, min(width, height) // 34), bold=True)

    headline_lines = _wrap_text(draw, headline, headline_font, text_width)
    support_lines = _wrap_text(draw, support, support_font, text_width) if support else []
    headline_line_height = _line_height(draw, headline_font)
    support_line_height = _line_height(draw, support_font)
    headline_spacing = max(8, headline_line_height // 5)
    support_spacing = max(6, support_line_height // 4)

    cta_text = " ".join((cta or "").split())
    cta_height = 0
    if cta_text:
        cta_box = draw.textbbox((0, 0), cta_text.upper(), font=cta_font)
        cta_height = (cta_box[3] - cta_box[1]) + max(18, height // 56)

    headline_height = len(headline_lines) * headline_line_height + max(
        0, len(headline_lines) - 1
    ) * headline_spacing
    support_height = len(support_lines) * support_line_height + max(
        0, len(support_lines) - 1
    ) * support_spacing
    accent_height = max(5, width // 220)
    gap_after_accent = max(16, height // 60)
    gap_between_blocks = max(10, height // 72) if support_lines else 0
    gap_after_cta = max(14, height // 68) if cta_height else 0
    panel_height = (
        panel_padding_y * 2
        + cta_height
        + gap_after_cta
        + accent_height
        + gap_after_accent
        + headline_height
        + gap_between_blocks
        + support_height
    )
    panel_left = margin_x
    panel_top = height - margin_y - panel_height
    panel_right = min(width - margin_x, panel_left + panel_width)

    draw.rounded_rectangle(
        [(panel_left, panel_top), (panel_right, panel_top + panel_height)],
        radius=max(22, width // 40),
        fill=style.panel_fill,
        outline=style.panel_outline,
        width=1,
    )

    text_x = panel_left + panel_padding_x
    cursor_y = panel_top + panel_padding_y

    if cta_text:
        pill_width = min(
            panel_width - panel_padding_x * 2,
            _text_width(draw, cta_text.upper(), cta_font) + max(32, width // 32),
        )
        pill_height = cta_height
        draw.rounded_rectangle(
            [(text_x, cursor_y), (text_x + pill_width, cursor_y + pill_height)],
            radius=max(12, pill_height // 2),
            fill=style.cta_fill,
        )
        pill_text_y = cursor_y + (pill_height - _line_height(draw, cta_font)) / 2 - 1
        draw.text(
            (text_x + max(16, width // 72), pill_text_y),
            cta_text.upper(),
            font=cta_font,
            fill=style.cta_text_fill,
        )
        cursor_y += pill_height + gap_after_cta

    draw.rounded_rectangle(
        [(text_x, cursor_y), (text_x + max(48, width // 18), cursor_y + accent_height)],
        radius=max(2, accent_height // 2),
        fill=style.accent_fill,
    )
    cursor_y += accent_height + gap_after_accent

    for line in headline_lines:
        _draw_text_with_shadow(
            draw,
            (text_x, cursor_y),
            line,
            headline_font,
            fill=style.text_fill,
        )
        cursor_y += headline_line_height + headline_spacing

    if support_lines:
        cursor_y += gap_between_blocks - headline_spacing
        for line in support_lines:
            _draw_text_with_shadow(
                draw,
                (text_x, cursor_y),
                line,
                support_font,
                fill=style.support_fill,
                shadow_alpha=96,
            )
            cursor_y += support_line_height + support_spacing

    return Image.alpha_composite(canvas, overlay)


def _draw_bottom_gradient(
    overlay: Image.Image,
    width: int,
    height: int,
    gradient_rgb: tuple[int, int, int],
) -> None:
    gradient_top = int(height * 0.48)
    gradient_height = max(1, height - gradient_top)
    for index in range(gradient_height):
        progress = index / gradient_height
        alpha = int(208 * (progress**1.8))
        overlay.paste(gradient_rgb + (alpha,), (0, gradient_top + index, width, gradient_top + index + 1))


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
        return int(width * 0.48)
    if width == height:
        return int(width * 0.72)
    return int(width * 0.82)


def _draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    shadow_alpha: int = 124,
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


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = value.lstrip("#")
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
