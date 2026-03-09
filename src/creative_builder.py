from __future__ import annotations

from PIL import Image, ImageOps

try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - Pillow compatibility
    RESAMPLING = Image.LANCZOS


def build_creatives(
    source_image: Image.Image,
    ratio_specs: dict[str, tuple[int, int]],
) -> dict[str, Image.Image]:
    base_image = source_image.convert("RGBA")
    creatives: dict[str, Image.Image] = {}
    for ratio_name, size in ratio_specs.items():
        creatives[ratio_name] = ImageOps.fit(
            base_image,
            size,
            method=RESAMPLING,
            centering=(0.5, 0.5),
        )
    return creatives
