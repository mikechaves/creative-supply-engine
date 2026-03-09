from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import PIL
from PIL import Image, ImageDraw, ImageFont

from src.config import AppConfig


@dataclass
class GeneratedImageResult:
    image: Image.Image
    provenance: str
    warning: str | None = None


class ImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, size: tuple[int, int]) -> GeneratedImageResult:
        """Return a generated image or a graceful fallback."""


class OpenAIImageGenerator(ImageGenerator):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, prompt: str, size: tuple[int, int]) -> GeneratedImageResult:
        api_key = os.getenv(self.config.openai_api_key_env)
        if not api_key:
            return GeneratedImageResult(
                image=create_placeholder_image(size, "OpenAI unavailable"),
                provenance="generated_placeholder",
                warning="OpenAI API key not configured; used placeholder image.",
            )

        try:
            image = self._generate_openai_image(api_key, prompt, size)
            return GeneratedImageResult(image=image, provenance="generated_openai")
        except Exception as exc:  # noqa: BLE001 - user-facing fallback path
            return GeneratedImageResult(
                image=create_placeholder_image(size, "OpenAI fallback"),
                provenance="generated_placeholder",
                warning=f"OpenAI image generation failed; used placeholder image. Reason: {exc}",
            )

    def _generate_openai_image(
        self,
        api_key: str,
        prompt: str,
        size: tuple[int, int],
    ) -> Image.Image:
        payload = json.dumps(
            {
                "model": self.config.openai_image_model,
                "prompt": prompt,
                "n": 1,
                "size": f"{size[0]}x{size[1]}",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.config.openai_generate_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        response = self._open_json(request)
        data = response.get("data") or []
        if not data:
            raise RuntimeError("OpenAI response did not include any image data.")

        first_image = data[0]
        b64_image = first_image.get("b64_json")
        if b64_image:
            image_bytes = base64.b64decode(b64_image)
            return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        image_url = first_image.get("url")
        if image_url:
            return self._download_image(str(image_url))

        raise RuntimeError("OpenAI response did not include b64_json or an image URL.")

    def _download_image(self, image_url: str) -> Image.Image:
        request = urllib.request.Request(
            image_url,
            headers={"User-Agent": "creative-supply-engine/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(
            request, timeout=self.config.openai_timeout_seconds
        ) as response:
            image_bytes = response.read()
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    def _open_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.openai_timeout_seconds
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(details)
                details = payload.get("error", {}).get("message", details)
            except json.JSONDecodeError:
                pass
            raise RuntimeError(
                f"HTTP {exc.code} from OpenAI: {details[:240]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error contacting OpenAI: {exc.reason}") from exc


def create_placeholder_image(size: tuple[int, int], label: str) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, "#efe7db")
    draw = ImageDraw.Draw(image, "RGBA")

    for index in range(height):
        blend = index / max(height - 1, 1)
        red = int(239 * (1 - blend) + 212 * blend)
        green = int(231 * (1 - blend) + 189 * blend)
        blue = int(219 * (1 - blend) + 146 * blend)
        draw.line([(0, index), (width, index)], fill=(red, green, blue, 255))

    stripe_color = (255, 255, 255, 70)
    stripe_width = max(60, width // 14)
    for offset in range(-height, width, stripe_width * 2):
        draw.polygon(
            [
                (offset, 0),
                (offset + stripe_width, 0),
                (offset + height + stripe_width, height),
                (offset + height, height),
            ],
            fill=stripe_color,
        )

    margin = int(min(width, height) * 0.08)
    panel_height = int(height * 0.24)
    panel_top = height - panel_height - margin
    draw.rounded_rectangle(
        [(margin, panel_top), (width - margin, height - margin)],
        radius=30,
        fill=(31, 28, 24, 170),
    )

    title_font = _load_font(max(28, width // 22))
    body_font = _load_font(max(18, width // 40))
    title = "Creative Supply Engine"
    subtitle = f"{label}\nCurrent run continues with a placeholder hero."

    title_box = draw.textbbox((0, 0), title, font=title_font)
    subtitle_box = draw.multiline_textbbox((0, 0), subtitle, font=body_font, spacing=10)
    total_height = (title_box[3] - title_box[1]) + 16 + (subtitle_box[3] - subtitle_box[1])
    text_top = panel_top + (panel_height - total_height) / 2

    draw.text(
        (margin + 28, text_top),
        title,
        font=title_font,
        fill=(255, 244, 230, 255),
    )
    draw.multiline_text(
        (margin + 28, text_top + (title_box[3] - title_box[1]) + 16),
        subtitle,
        font=body_font,
        fill=(255, 244, 230, 230),
        spacing=10,
    )
    return image


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
